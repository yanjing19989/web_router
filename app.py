from __future__ import annotations

import asyncio
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import psutil
import uvicorn
from fastapi import FastAPI, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_FILE = BASE_DIR / "templates" / "index.html"
STATIC_DIR = BASE_DIR / "static"
HOST = "127.0.0.1"
APP_PORT = 8765
MIN_PROJECT_PORT = 3000
MAX_PROJECT_PORT = 8999


class LauncherError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class InspectRequest(BaseModel):
    path: str


class ProjectCreate(BaseModel):
    path: str
    name: str
    type: Literal["npm", "python", "static"]
    command: str
    port: int


def canonical_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def comparable_path(value: str | Path) -> str:
    return os.path.normcase(str(canonical_path(value))).casefold()


def shell_quote(value: str | Path) -> str:
    return subprocess.list2cmdline([str(value)])


def port_is_available(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind((HOST, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


class ProjectStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.file = data_dir / "projects.json"
        self._lock = threading.RLock()
        self._projects = self._load()

    def _load(self) -> list[dict]:
        if not self.file.exists():
            return []
        try:
            data = json.loads(self.file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"无法读取项目配置：{exc}") from exc
        if not isinstance(data, list):
            raise RuntimeError("项目配置格式无效")
        return data

    def all(self) -> list[dict]:
        with self._lock:
            return [dict(item) for item in self._projects]

    def get(self, project_id: str) -> dict | None:
        with self._lock:
            for project in self._projects:
                if project["id"] == project_id:
                    return dict(project)
        return None

    def add(self, project: dict) -> None:
        with self._lock:
            self._projects.append(dict(project))
            self._save()

    def update(self, project: dict) -> bool:
        with self._lock:
            for index, current in enumerate(self._projects):
                if current["id"] == project["id"]:
                    self._projects[index] = dict(project)
                    self._save()
                    return True
        return False

    def delete(self, project_id: str) -> bool:
        with self._lock:
            original_size = len(self._projects)
            self._projects = [item for item in self._projects if item["id"] != project_id]
            if len(self._projects) == original_size:
                return False
            self._save()
            return True

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.file.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(self._projects, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, self.file)


class RuntimeProcess:
    def __init__(self, process: subprocess.Popen) -> None:
        self.process = process
        self.started_at = time.monotonic()
        self.cpu_processes: dict[int, psutil.Process] = {}


class ProcessManager:
    def __init__(self) -> None:
        self._runtimes: dict[str, RuntimeProcess] = {}
        self._lock = threading.RLock()

    def is_running(self, project_id: str) -> bool:
        with self._lock:
            runtime = self._runtimes.get(project_id)
            if runtime is None:
                return False
            if runtime.process.poll() is None:
                return True
            self._runtimes.pop(project_id, None)
            return False

    def start(self, project: dict) -> None:
        project_id = project["id"]
        with self._lock:
            if self.is_running(project_id):
                return

            command = project["command"].replace("{port}", str(project["port"]))
            environment = os.environ.copy()
            environment.update({"HOST": HOST, "PORT": str(project["port"])})
            if os.name == "nt":
                args = ["cmd.exe", "/d", "/s", "/c", command]
                creation_flags = (
                    subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
                )
            else:
                args = ["/bin/sh", "-c", command]
                creation_flags = 0

            try:
                process = subprocess.Popen(
                    args,
                    cwd=project["path"],
                    env=environment,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creation_flags,
                )
            except OSError as exc:
                raise LauncherError(500, f"启动失败：{exc}") from exc

            runtime = RuntimeProcess(process)
            self._runtimes[project_id] = runtime

        time.sleep(0.2)
        if process.poll() is not None:
            with self._lock:
                self._runtimes.pop(project_id, None)
            raise LauncherError(500, f"启动命令已退出，退出码：{process.returncode}")

    def stop(self, project_id: str) -> None:
        with self._lock:
            runtime = self._runtimes.pop(project_id, None)
        if runtime is not None:
            self._terminate(runtime)

    def stop_all(self) -> None:
        with self._lock:
            runtimes = list(self._runtimes.values())
            self._runtimes.clear()
        for runtime in runtimes:
            self._terminate(runtime)

    def metrics(self, project_id: str) -> dict:
        stopped = {
            "status": "stopped",
            "pid": None,
            "cpu_percent": 0.0,
            "memory_uss_bytes": 0,
            "memory_vms_bytes": 0,
            "uptime_seconds": 0,
        }
        with self._lock:
            runtime = self._runtimes.get(project_id)
            if runtime is None:
                return stopped
            if runtime.process.poll() is not None:
                self._runtimes.pop(project_id, None)
                return stopped

            try:
                root = psutil.Process(runtime.process.pid)
                processes = [root, *root.children(recursive=True)]
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return stopped

            cpu_percent = 0.0
            memory_uss_bytes = 0
            memory_vms_bytes = 0
            live_pids: set[int] = set()
            for process in processes:
                try:
                    live_pids.add(process.pid)
                    sampled = runtime.cpu_processes.setdefault(process.pid, process)
                    cpu_percent += sampled.cpu_percent(interval=None)
                    memory = sampled.memory_full_info()
                    memory_uss_bytes += getattr(memory, "uss", 0)
                    memory_vms_bytes += memory.vms
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            runtime.cpu_processes = {
                pid: process
                for pid, process in runtime.cpu_processes.items()
                if pid in live_pids
            }
            return {
                "status": "running",
                "pid": runtime.process.pid,
                "cpu_percent": round(cpu_percent, 1),
                "memory_uss_bytes": memory_uss_bytes,
                "memory_vms_bytes": memory_vms_bytes,
                "uptime_seconds": int(time.monotonic() - runtime.started_at),
            }

    @staticmethod
    def _terminate(runtime: RuntimeProcess) -> None:
        try:
            root = psutil.Process(runtime.process.pid)
            processes = [*reversed(root.children(recursive=True)), root]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return

        for process in processes:
            try:
                process.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        _, alive = psutil.wait_procs(processes, timeout=2)
        for process in alive:
            try:
                process.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if alive:
            psutil.wait_procs(alive, timeout=2)


class LauncherService:
    def __init__(self, data_dir: Path) -> None:
        self.store = ProjectStore(data_dir)
        self.processes = ProcessManager()
        self._lock = threading.RLock()

    def allocate_port(self) -> int:
        configured = {item["port"] for item in self.store.all()}
        configured.add(APP_PORT)
        for port in range(MIN_PROJECT_PORT, MAX_PROJECT_PORT + 1):
            if port not in configured and port_is_available(port):
                return port
        raise LauncherError(409, "没有可用的项目端口")

    def inspect(self, path_value: str) -> dict:
        path = canonical_path(path_value)
        if not path.is_dir():
            raise LauncherError(422, "请选择有效的项目目录")

        detection = detect_project(path)
        if detection is None:
            raise LauncherError(422, "未识别到可运行的 npm、Python 或静态项目")
        return {
            "path": str(path),
            "name": path.name,
            "port": self.allocate_port(),
            **detection,
        }

    def create(self, payload: ProjectCreate) -> dict:
        with self._lock:
            path = canonical_path(payload.path)
            projects = self.store.all()
            self._validate(payload, path, projects)
            project = {
                "id": uuid.uuid4().hex,
                "path": str(path),
                "name": payload.name.strip(),
                "type": payload.type,
                "command": payload.command.strip(),
                "port": payload.port,
            }
            self.store.add(project)
        return self.view(project)

    def delete(self, project_id: str) -> None:
        self.require_project(project_id)
        if self.processes.is_running(project_id):
            raise LauncherError(409, "请先停止项目再删除")
        self.store.delete(project_id)

    def update(self, project_id: str, payload: ProjectCreate) -> dict:
        with self._lock:
            self.require_project(project_id)
            if self.processes.is_running(project_id):
                raise LauncherError(409, "请先停止项目再编辑")
            path = canonical_path(payload.path)
            other_projects = [
                project
                for project in self.store.all()
                if project["id"] != project_id
            ]
            self._validate(payload, path, other_projects)
            project = {
                "id": project_id,
                "path": str(path),
                "name": payload.name.strip(),
                "type": payload.type,
                "command": payload.command.strip(),
                "port": payload.port,
            }
            self.store.update(project)
        return self.view(project)

    def start(self, project_id: str) -> dict:
        project = self.require_project(project_id)
        if self.processes.is_running(project_id):
            return self.view(project)
        if not port_is_available(project["port"]):
            raise LauncherError(409, f"端口 {project['port']} 已被占用")
        self.processes.start(project)
        return self.view(project)

    def stop(self, project_id: str) -> dict:
        project = self.require_project(project_id)
        self.processes.stop(project_id)
        return self.view(project)

    def require_project(self, project_id: str) -> dict:
        project = self.store.get(project_id)
        if project is None:
            raise LauncherError(404, "项目不存在")
        return project

    def list_view(self) -> dict:
        projects = [self.view(project) for project in self.store.all()]
        return {
            "summary": {
                "total": len(projects),
                "running": sum(item["status"] == "running" for item in projects),
                "total_memory_uss_bytes": sum(
                    item["memory_uss_bytes"] for item in projects
                ),
                "total_memory_vms_bytes": sum(
                    item["memory_vms_bytes"] for item in projects
                ),
            },
            "projects": projects,
        }

    def view(self, project: dict) -> dict:
        return {
            **project,
            "url": f"http://{HOST}:{project['port']}/",
            **self.processes.metrics(project["id"]),
        }

    @staticmethod
    def _validate(payload: ProjectCreate, path: Path, projects: list[dict]) -> None:
        if not path.is_dir():
            raise LauncherError(422, "项目目录无效")
        if not payload.name.strip():
            raise LauncherError(422, "项目名称不能为空")
        if not payload.command.strip():
            raise LauncherError(422, "启动命令不能为空")
        if not MIN_PROJECT_PORT <= payload.port <= MAX_PROJECT_PORT:
            raise LauncherError(
                422, f"端口必须在 {MIN_PROJECT_PORT}–{MAX_PROJECT_PORT} 之间"
            )
        if payload.port == APP_PORT:
            raise LauncherError(422, "不能使用启动器管理端口")
        normalized = comparable_path(path)
        if any(comparable_path(item["path"]) == normalized for item in projects):
            raise LauncherError(409, "该目录已添加")
        if any(item["port"] == payload.port for item in projects):
            raise LauncherError(409, "该端口已被其他项目配置使用")
        if not port_is_available(payload.port):
            raise LauncherError(409, f"端口 {payload.port} 已被占用")


def read_source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:1_000_000]
    except OSError:
        return ""


def python_executable(path: Path) -> Path:
    for environment in (".venv", "venv"):
        candidate = path / environment / "Scripts" / "python.exe"
        if candidate.is_file():
            return candidate
    return Path(sys.executable)


def python_module_entries(path: Path) -> list[tuple[str, Path]]:
    """Return importable top-level packages exposing a ``__main__.py`` entry."""
    entries: list[tuple[str, Path]] = []
    try:
        children = sorted(path.iterdir(), key=lambda item: item.name.casefold())
    except OSError:
        return entries
    for package in children:
        if (
            not package.is_dir()
            or package.name.startswith(".")
            or not package.name.isidentifier()
        ):
            continue
        main_file = package / "__main__.py"
        if main_file.is_file():
            entries.append((package.name, main_file))
    return entries


def detect_project(path: Path) -> dict | None:
    package_file = path / "package.json"
    if package_file.is_file():
        try:
            package = json.loads(package_file.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            package = {}
        scripts = package.get("scripts") if isinstance(package, dict) else None
        if isinstance(scripts, dict):
            script = next(
                (name for name in ("dev", "start", "serve") if scripts.get(name)),
                None,
            )
            if script:
                regular_dependencies = package.get("dependencies") or {}
                development_dependencies = package.get("devDependencies") or {}
                dependencies = {
                    **(regular_dependencies if isinstance(regular_dependencies, dict) else {}),
                    **(
                        development_dependencies
                        if isinstance(development_dependencies, dict)
                        else {}
                    ),
                }
                script_body = str(scripts[script]).lower()
                dependency_names = {str(name).lower() for name in dependencies}
                if "vite" in dependency_names or re.search(r"(^|\s)vite(\s|$)", script_body):
                    command = (
                        f"npm run {script} -- --host {HOST} --port {{port}}"
                    )
                    detector = "Vite"
                elif "next" in dependency_names or re.search(
                    r"(^|\s)next(\s|$)", script_body
                ):
                    command = f"npm run {script} -- -H {HOST} -p {{port}}"
                    detector = "Next.js"
                elif "react-scripts" in dependency_names or "react-scripts" in script_body:
                    command = f"npm run {script}"
                    detector = "react-scripts"
                else:
                    command = f"npm run {script}"
                    detector = f"npm · {script}"
                return {"type": "npm", "command": command, "detector": detector}

    interpreter = shell_quote(python_executable(path))
    if (path / "manage.py").is_file():
        return {
            "type": "python",
            "command": f"{interpreter} manage.py runserver {HOST}:{{port}}",
            "detector": "Django",
        }

    module_entries = python_module_entries(path)
    if module_entries:
        module, main_file = module_entries[0]
        source = read_source(main_file)
        detector = (
            "FastAPI"
            if re.search(r"\b(?:FastAPI|uvicorn)\b", source, re.IGNORECASE)
            else f"Python · {module}"
        )
        return {
            "type": "python",
            "command": f"{interpreter} -m {module} --host {HOST} --port {{port}}",
            "detector": detector,
        }

    candidates = [
        candidate
        for candidate in (path / "main.py", path / "app.py")
        if candidate.is_file()
    ]
    for candidate in candidates:
        source = read_source(candidate)
        module = candidate.stem
        if re.search(r"\bFastAPI\s*\(", source):
            return {
                "type": "python",
                "command": (
                    f"{interpreter} -m uvicorn {module}:app --host {HOST} --port {{port}}"
                ),
                "detector": "FastAPI",
            }
        if re.search(r"\bFlask\s*\(", source):
            return {
                "type": "python",
                "command": (
                    f"{interpreter} -m flask --app {module}:app run "
                    f"--host {HOST} --port {{port}}"
                ),
                "detector": "Flask",
            }
    if candidates:
        candidate = candidates[0]
        return {
            "type": "python",
            "command": (
                f"{interpreter} {candidate.name} --host {HOST} --port {{port}}"
            ),
            "detector": f"Python · {candidate.name}",
        }

    if (path / "index.html").is_file():
        return {
            "type": "static",
            "command": f"{interpreter} -m http.server {{port}} --bind {HOST}",
            "detector": "静态站点",
        }
    return None


def select_folder() -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as exc:
        raise LauncherError(500, "当前 Python 环境不支持 Windows 文件夹选择器") from exc
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    root = tk.Tk()
    try:
        root.withdraw()
        root.attributes("-topmost", True)
        root.update()
        selected = filedialog.askdirectory(parent=root, mustexist=True, title="选择项目文件夹")
        return selected or None
    finally:
        root.destroy()


def open_project_directory(path: str | Path) -> None:
    directory = canonical_path(path)
    if not directory.is_dir():
        raise LauncherError(422, "项目目录无效")
    try:
        if os.name == "nt":
            os.startfile(str(directory))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(directory)])
        else:
            subprocess.Popen(["xdg-open", str(directory)])
    except OSError as exc:
        raise LauncherError(500, f"无法打开项目目录：{exc}") from exc


def create_app(data_dir: Path | None = None) -> FastAPI:
    service = LauncherService(data_dir or BASE_DIR / ".local_data")

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        yield
        service.processes.stop_all()

    application = FastAPI(title="本地项目启动器", lifespan=lifespan)
    application.state.launcher = service

    @application.exception_handler(LauncherError)
    async def launcher_error_handler(_, exc: LauncherError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @application.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(
            TEMPLATE_FILE,
            media_type="text/html; charset=utf-8",
            headers={"Cache-Control": "no-cache"},
        )

    @application.get("/static/{asset_path:path}", include_in_schema=False)
    def static_asset(asset_path: str) -> FileResponse:
        asset = (STATIC_DIR / asset_path).resolve()
        if STATIC_DIR not in asset.parents or not asset.is_file():
            raise LauncherError(404, "资源不存在")
        return FileResponse(asset)

    @application.get("/api/projects")
    def list_projects() -> dict:
        return service.list_view()

    @application.post("/api/picker")
    async def picker() -> dict:
        return {"path": await asyncio.to_thread(select_folder)}

    @application.post("/api/projects/inspect")
    def inspect_project(payload: InspectRequest) -> dict:
        return service.inspect(payload.path)

    @application.post("/api/projects", status_code=201)
    def create_project(payload: ProjectCreate) -> dict:
        return service.create(payload)

    @application.put("/api/projects/{project_id}")
    def update_project(project_id: str, payload: ProjectCreate) -> dict:
        return service.update(project_id, payload)

    @application.post("/api/projects/{project_id}/start")
    def start_project(project_id: str) -> dict:
        return service.start(project_id)

    @application.post("/api/projects/{project_id}/stop")
    def stop_project(project_id: str) -> dict:
        return service.stop(project_id)

    @application.post("/api/projects/{project_id}/open-folder", status_code=204)
    def open_project_folder(project_id: str) -> Response:
        project = service.require_project(project_id)
        open_project_directory(project["path"])
        return Response(status_code=204)

    @application.delete("/api/projects/{project_id}", status_code=204)
    def delete_project(project_id: str) -> Response:
        service.delete(project_id)
        return Response(status_code=204)

    return application


app = create_app()


if __name__ == "__main__":
    import threading
    import webbrowser

    def open_browser() -> None:
        time.sleep(1.2)
        webbrowser.open(f"http://{HOST}:{APP_PORT}/")

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host=HOST, port=APP_PORT, reload=False)
