from __future__ import annotations

import argparse
import collections
import http.client
import json
import locale
import mimetypes
import os
import re
import signal
import socket
import stat
import subprocess
import sys
import threading
import time
import urllib.parse
import uuid
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover - fallback when psutil is unavailable
    psutil = None  # type: ignore[assignment]

from win32_ui import ProcessJob, SingleInstanceMutex, TrayManager, open_folder_foreground, select_folder_native


BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_FILE = BASE_DIR / "templates" / "index.html"
STATIC_DIR = BASE_DIR / "static"
STATIC_ROOT = STATIC_DIR.resolve()
HOST = "127.0.0.1"
APP_PORT = 8888
MIN_PROJECT_PORT = 3000
MAX_PROJECT_PORT = 8999
VALID_PROJECT_TYPES = {"npm", "python", "static"}


class LauncherError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


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


def validate_inspect_payload(data: Any) -> str:
    if not isinstance(data, dict) or not isinstance(data.get("path"), str):
        raise LauncherError(422, "请求参数无效：缺少 path")
    return data["path"]


def validate_project_payload(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise LauncherError(422, "请求体必须是 JSON 对象")

    path = data.get("path")
    name = data.get("name")
    project_type = data.get("type")
    command = data.get("command")
    port = data.get("port")

    if not isinstance(path, str):
        raise LauncherError(422, "项目路径无效")
    if not isinstance(name, str):
        raise LauncherError(422, "项目名称不能为空")
    if project_type not in VALID_PROJECT_TYPES:
        raise LauncherError(422, "项目类型无效")
    if not isinstance(command, str):
        raise LauncherError(422, "启动命令不能为空")
    if isinstance(port, bool) or not isinstance(port, int):
        raise LauncherError(422, "端口必须是整数")

    return {
        "path": path,
        "name": name,
        "type": project_type,
        "command": command,
        "port": port,
    }


def validate_reorder_payload(data: Any) -> list[str]:
    if not isinstance(data, dict) or not isinstance(data.get("ids"), list):
        raise LauncherError(422, "请求参数无效：缺少 ids 列表")
    ids = data["ids"]
    if not all(isinstance(item, str) and item for item in ids):
        raise LauncherError(422, "项目 ID 列表无效")
    return ids


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

    def reorder(self, ids: list[str]) -> list[dict]:
        with self._lock:
            if len(ids) != len(self._projects) or len(set(ids)) != len(ids):
                raise LauncherError(422, "项目排序列表与当前项目不匹配")
            by_id = {item["id"]: item for item in self._projects}
            if any(project_id not in by_id for project_id in ids):
                raise LauncherError(422, "项目排序列表包含未知项目")
            self._projects = [by_id[project_id] for project_id in ids]
            self._save()
            return [dict(item) for item in self._projects]

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.file.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(self._projects, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, self.file)


class RuntimeProcess:
    def __init__(
        self,
        process: subprocess.Popen,
        job: ProcessJob | None = None,
    ) -> None:
        self.process = process
        self.job = job
        self.started_at = time.monotonic()
        self.cpu_processes: dict[int, Any] = {}
        self.lock = threading.Lock()


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
            if runtime.job is not None:
                runtime.job.close()
            return False

    def running_count(self) -> int:
        with self._lock:
            dead = [
                pid for pid, rt in self._runtimes.items() if rt.process.poll() is not None
            ]
            for pid in dead:
                rt = self._runtimes.pop(pid, None)
                if rt is not None and rt.job is not None:
                    rt.job.close()
            return len(self._runtimes)

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
                    stderr=subprocess.PIPE,
                    creationflags=creation_flags,
                )
            except OSError as exc:
                raise LauncherError(500, f"启动失败：{exc}") from exc

            stderr_lines: collections.deque[bytes] = collections.deque(maxlen=6)
            capturing = threading.Event()
            capturing.set()
            drainer = None
            stderr_stream = getattr(process, "stderr", None)
            if stderr_stream is not None:
                drainer = threading.Thread(
                    target=self._drain_stderr,
                    args=(stderr_stream, stderr_lines, capturing),
                    daemon=True,
                )
                drainer.start()

            job = ProcessJob()
            job.assign(process)
            runtime = RuntimeProcess(process, job=job)
            self._runtimes[project_id] = runtime

        try:
            process.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            capturing.clear()
            return
        with self._lock:
            self._runtimes.pop(project_id, None)
        job.close()
        if drainer is not None:
            drainer.join(timeout=0.2)
        detail = self._format_stderr(stderr_lines)
        message = f"启动命令已退出，退出码：{process.returncode}"
        if detail:
            message = f"{message} — {detail}"
        raise LauncherError(500, message)

    @staticmethod
    def _drain_stderr(
        stream: Any,
        lines: collections.deque[bytes],
        capturing: threading.Event,
    ) -> None:
        try:
            while capturing.is_set():
                line = stream.readline(1024)
                if not line:
                    return
                if line.strip():
                    lines.append(line)
            lines.clear()
            while stream.read(4096):
                pass
        except OSError:
            pass
        finally:
            try:
                stream.close()
            except OSError:
                pass

    @staticmethod
    def _format_stderr(lines: collections.deque[bytes]) -> str:
        if not lines:
            return ""
        raw = b"".join(lines)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode(locale.getpreferredencoding(False) or "utf-8", errors="replace")
        compact = " | ".join(part.strip() for part in text.splitlines() if part.strip())
        return compact[:300]

    def stop(self, project_id: str) -> None:
        with self._lock:
            runtime = self._runtimes.pop(project_id, None)
        if runtime is not None:
            self._terminate(runtime)

    def close(self) -> None:
        self.stop_all()

    def stop_all(self) -> None:
        with self._lock:
            runtimes = list(self._runtimes.values())
            self._runtimes.clear()
        if not runtimes:
            return
        self._terminate_many(runtimes)

    @staticmethod
    def _stopped_metrics() -> dict:
        return {
            "status": "stopped",
            "pid": None,
            "cpu_percent": 0.0,
            "memory_uss_bytes": 0,
            "memory_vms_bytes": 0,
            "uptime_seconds": 0,
        }

    @staticmethod
    def _build_children_map() -> dict[int, list[Any]]:
        children_map: dict[int, list[Any]] = {}
        for proc in psutil.process_iter(["ppid"]):
            try:
                ppid = proc.info.get("ppid")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if ppid is not None:
                children_map.setdefault(ppid, []).append(proc)
        return children_map

    @classmethod
    def _collect_tree(
        cls,
        root: Any,
        children_map: dict[int, list[Any]] | None,
    ) -> list[Any]:
        if children_map is None:
            return [root, *root.children(recursive=True)]
        processes = [root]
        visited = {root.pid}
        stack = [root.pid]
        while stack:
            parent_pid = stack.pop()
            for child in children_map.get(parent_pid, ()):
                if child.pid not in visited:
                    visited.add(child.pid)
                    processes.append(child)
                    stack.append(child.pid)
        return processes

    @classmethod
    def _sample_runtime(
        cls,
        runtime: RuntimeProcess,
        children_map: dict[int, list[Any]] | None = None,
    ) -> dict:
        if psutil is None:
            return {
                "status": "running",
                "pid": runtime.process.pid,
                "cpu_percent": 0.0,
                "memory_uss_bytes": 0,
                "memory_vms_bytes": 0,
                "uptime_seconds": int(time.monotonic() - runtime.started_at),
            }

        try:
            root = psutil.Process(runtime.process.pid)
            processes = cls._collect_tree(root, children_map)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return cls._stopped_metrics()

        cpu_percent = 0.0
        memory_uss_bytes = 0
        memory_vms_bytes = 0
        live_pids: set[int] = set()
        with runtime.lock:
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

    def metrics(self, project_id: str) -> dict:
        with self._lock:
            runtime = self._runtimes.get(project_id)
            if runtime is None:
                return self._stopped_metrics()
            if runtime.process.poll() is not None:
                self._runtimes.pop(project_id, None)
                if runtime.job is not None:
                    runtime.job.close()
                return self._stopped_metrics()
        return self._sample_runtime(runtime)

    def metrics_all(self, project_ids: list[str]) -> dict[str, dict]:
        active: list[tuple[str, RuntimeProcess]] = []
        results: dict[str, dict] = {}
        with self._lock:
            for project_id in project_ids:
                runtime = self._runtimes.get(project_id)
                if runtime is None:
                    results[project_id] = self._stopped_metrics()
                elif runtime.process.poll() is not None:
                    self._runtimes.pop(project_id, None)
                    if runtime.job is not None:
                        runtime.job.close()
                    results[project_id] = self._stopped_metrics()
                else:
                    active.append((project_id, runtime))
        if not active:
            return results
        children_map = self._build_children_map() if psutil is not None else None
        for project_id, runtime in active:
            results[project_id] = self._sample_runtime(runtime, children_map)
        return results

    @classmethod
    def _terminate(cls, runtime: RuntimeProcess) -> None:
        cls._terminate_many([runtime])

    @classmethod
    def _terminate_many(cls, runtimes: list[RuntimeProcess]) -> None:
        if psutil is None:
            for runtime in runtimes:
                if runtime.job is not None:
                    runtime.job.terminate()
                    runtime.job.close()
                try:
                    runtime.process.terminate()
                except OSError:
                    pass
            deadline = time.monotonic() + 2.0
            alive_runtimes: list[RuntimeProcess] = []
            for runtime in runtimes:
                remaining = max(0.0, deadline - time.monotonic())
                try:
                    runtime.process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    alive_runtimes.append(runtime)
                except OSError:
                    pass
            for runtime in alive_runtimes:
                try:
                    runtime.process.kill()
                    runtime.process.wait(timeout=2)
                except (subprocess.TimeoutExpired, OSError):
                    pass
            return

        children_map = cls._build_children_map() if len(runtimes) > 1 else None
        processes: list[Any] = []
        seen: set[int] = set()
        for runtime in runtimes:
            try:
                root = psutil.Process(runtime.process.pid)
                tree = cls._collect_tree(root, children_map)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            for proc in reversed(tree):
                if proc.pid not in seen:
                    seen.add(proc.pid)
                    processes.append(proc)

        for runtime in runtimes:
            if runtime.job is not None:
                runtime.job.terminate()
                runtime.job.close()
        if not processes:
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

    @staticmethod
    def _build_project(project_id: str, path: Path, payload: dict[str, Any]) -> dict:
        return {
            "id": project_id,
            "path": str(path),
            "name": payload["name"].strip(),
            "type": payload["type"],
            "command": payload["command"].strip(),
            "port": payload["port"],
        }

    def create(self, payload: dict[str, Any]) -> dict:
        with self._lock:
            path = canonical_path(payload["path"])
            projects = self.store.all()
            self._validate(payload, path, projects)
            project = self._build_project(uuid.uuid4().hex, path, payload)
            self.store.add(project)
        return self.view(project)

    def delete(self, project_id: str) -> None:
        self.require_project(project_id)
        if self.processes.is_running(project_id):
            raise LauncherError(409, "请先停止项目再删除")
        self.store.delete(project_id)

    def update(self, project_id: str, payload: dict[str, Any]) -> dict:
        with self._lock:
            self.require_project(project_id)
            if self.processes.is_running(project_id):
                raise LauncherError(409, "请先停止项目再编辑")
            path = canonical_path(payload["path"])
            other_projects = [
                project
                for project in self.store.all()
                if project["id"] != project_id
            ]
            self._validate(payload, path, other_projects)
            project = self._build_project(project_id, path, payload)
            self.store.update(project)
        return self.view(project)

    def reorder(self, ids: list[str]) -> dict:
        with self._lock:
            self.store.reorder(ids)
        return self.list_view()

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
        raw_projects = self.store.all()
        metrics_map = self.processes.metrics_all([item["id"] for item in raw_projects])
        projects = [
            {
                **project,
                "url": f"http://{HOST}:{project['port']}/",
                "icon_url": project_icon_url(project),
                **metrics_map[project["id"]],
            }
            for project in raw_projects
        ]
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
            "icon_url": project_icon_url(project),
            **self.processes.metrics(project["id"]),
        }

    @staticmethod
    def _validate(payload: dict[str, Any], path: Path, projects: list[dict]) -> None:
        if not path.is_dir():
            raise LauncherError(422, "项目目录无效")
        if not payload["name"].strip():
            raise LauncherError(422, "项目名称不能为空")
        if not payload["command"].strip():
            raise LauncherError(422, "启动命令不能为空")
        if not MIN_PROJECT_PORT <= payload["port"] <= MAX_PROJECT_PORT:
            raise LauncherError(
                422, f"端口必须在 {MIN_PROJECT_PORT}–{MAX_PROJECT_PORT} 之间"
            )
        if payload["port"] == APP_PORT:
            raise LauncherError(422, "不能使用启动器管理端口")
        normalized = comparable_path(path)
        if any(comparable_path(item["path"]) == normalized for item in projects):
            raise LauncherError(409, "该目录已添加")
        if any(item["port"] == payload["port"] for item in projects):
            raise LauncherError(409, "该端口已被其他项目配置使用")
        if not port_is_available(payload["port"]):
            raise LauncherError(409, f"端口 {payload['port']} 已被占用")


ICON_MIME_TYPES = {
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".webp": "image/webp",
}

_ICON_NAME_RE = re.compile(
    r"^(?:favicon|icon)(?:[_-][A-Za-z0-9_-]+)?\.(?:ico|png|svg|webp)$",
    re.IGNORECASE,
)
_ICON_PRIORITY_DIRS = ("public", "static", "assets", "dist", "build")
_ICON_SKIP_DIRS = {
    "node_modules",
    "venv",
    "env",
    "__pycache__",
    "site-packages",
    "target",
    "vendor",
}
_ICON_MAX_DEPTH = 3
_ICON_NEGATIVE_CACHE_TTL = 30.0
_ICON_CACHE: dict[str, tuple[float, Path | None, int]] = {}
_ICON_CACHE_LOCK = threading.Lock()


def _scan_dir_for_icon(directory: Path) -> tuple[Path | None, int, list[Path]]:
    matches: list[os.DirEntry[str]] = []
    subdirs: list[Path] = []
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                name = entry.name
                try:
                    if _ICON_NAME_RE.fullmatch(name) and entry.is_file():
                        matches.append(entry)
                    elif (
                        not name.startswith(".")
                        and name.casefold() not in _ICON_SKIP_DIRS
                        and entry.is_dir(follow_symlinks=False)
                    ):
                        subdirs.append(Path(entry.path))
                except OSError:
                    continue
    except OSError:
        return None, 0, []

    if matches:
        matches.sort(key=lambda item: item.name.casefold())
        for match in matches:
            try:
                return Path(match.path), match.stat().st_mtime_ns, []
            except OSError:
                continue
    subdirs.sort(key=lambda item: item.name.casefold())
    return None, 0, subdirs


def _search_project_icon(root: Path) -> tuple[Path | None, int]:
    if not root.is_dir():
        return None, 0

    found, mtime_ns, root_subdirs = _scan_dir_for_icon(root)
    if found is not None:
        return found, mtime_ns

    priority_rank = {name: index for index, name in enumerate(_ICON_PRIORITY_DIRS)}
    root_subdirs.sort(
        key=lambda item: (
            priority_rank.get(item.name.casefold(), len(priority_rank)),
            item.name.casefold(),
        )
    )

    queue: collections.deque[tuple[Path, int]] = collections.deque(
        (subdir, 1) for subdir in root_subdirs
    )
    while queue:
        current, depth = queue.popleft()
        found, mtime_ns, subdirs = _scan_dir_for_icon(current)
        if found is not None:
            return found, mtime_ns
        if depth < _ICON_MAX_DEPTH:
            for subdir in subdirs:
                queue.append((subdir, depth + 1))
    return None, 0


def find_project_icon(path: str | Path, use_cache: bool = True) -> tuple[Path | None, int]:
    key = str(path)
    now = time.monotonic()
    if use_cache:
        with _ICON_CACHE_LOCK:
            cached = _ICON_CACHE.get(key)
        if cached is not None:
            cached_at, cached_path, _ = cached
            if cached_path is not None:
                try:
                    info = cached_path.stat()
                    if stat.S_ISREG(info.st_mode):
                        with _ICON_CACHE_LOCK:
                            _ICON_CACHE[key] = (now, cached_path, info.st_mtime_ns)
                        return cached_path, info.st_mtime_ns
                except OSError:
                    pass
            elif (now - cached_at) < _ICON_NEGATIVE_CACHE_TTL:
                return None, 0

    found, mtime_ns = _search_project_icon(Path(path))
    with _ICON_CACHE_LOCK:
        _ICON_CACHE[key] = (now, found, mtime_ns)
    return found, mtime_ns


def project_icon_url(project: dict) -> str | None:
    icon_path, mtime_ns = find_project_icon(project["path"])
    if icon_path is None:
        return None
    return f"/api/projects/{project['id']}/icon?v={mtime_ns}"


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
    current = Path(sys.executable)
    if current.name.casefold() == "pythonw.exe":
        console_python = current.with_name("python.exe")
        if console_python.is_file():
            return console_python
    return current


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
        for candidate in (path / "main.py", path / "app.py", path / "web_gui.py")
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
        return select_folder_native("选择项目文件夹")
    except RuntimeError as exc:
        raise LauncherError(500, str(exc)) from exc


def open_project_directory(path: str | Path) -> None:
    directory = canonical_path(path)
    if not directory.is_dir():
        raise LauncherError(422, "项目目录无效")
    try:
        if os.name == "nt":
            open_folder_foreground(str(directory))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(directory)])
        else:
            subprocess.Popen(["xdg-open", str(directory)])
    except OSError as exc:
        raise LauncherError(500, f"无法打开项目目录：{exc}") from exc


class LauncherRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    @property
    def service(self) -> LauncherService:
        return self.server.service  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress stderr logging so pythonw.exe (where sys.stderr is None) never fails.
        return

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        content_type: str,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _send_json(self, status: int, payload: Any) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(status, encoded, "application/json; charset=utf-8")

    def _send_empty(self, status: int) -> None:
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_file(self, path: Path, content_type: str, cache_control: str | None = None) -> None:
        try:
            stat = path.stat()
        except OSError:
            raise LauncherError(404, "资源不存在")
        etag = f'"{stat.st_mtime_ns:x}-{stat.st_size:x}"'
        headers = {"ETag": etag}
        if cache_control:
            headers["Cache-Control"] = cache_control
        if self.headers.get("If-None-Match") == etag:
            self.send_response(HTTPStatus.NOT_MODIFIED)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        try:
            content = path.read_bytes()
        except OSError:
            raise LauncherError(404, "资源不存在")
        self._send_bytes(HTTPStatus.OK, content, content_type, headers)

    def _read_json(self) -> Any:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise LauncherError(422, "无效的 Content-Length")
        raw = self.rfile.read(length) if length > 0 else b""
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise LauncherError(422, "请求体不是有效的 JSON")

    def _handle(self, method: str) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path

        try:
            if method == "GET":
                if path == "/":
                    self._send_file(TEMPLATE_FILE, "text/html; charset=utf-8", "no-cache")
                    return
                if path.startswith("/static/"):
                    rel = urllib.parse.unquote(path[len("/static/"):])
                    asset = (STATIC_DIR / rel).resolve()
                    if STATIC_ROOT not in asset.parents or not asset.is_file():
                        raise LauncherError(404, "资源不存在")
                    ctype, _ = mimetypes.guess_type(str(asset))
                    if ctype and (ctype.startswith("text/") or ctype == "application/javascript"):
                        ctype = f"{ctype}; charset=utf-8"
                    self._send_file(asset, ctype or "application/octet-stream", "no-cache")
                    return
                if path == "/api/projects":
                    self._send_json(HTTPStatus.OK, self.service.list_view())
                    return
                if path == "/api/health":
                    self._send_json(HTTPStatus.OK, {"status": "ok"})
                    return
                icon_match = re.fullmatch(r"/api/projects/([^/]+)/icon", path)
                if icon_match:
                    project = self.service.require_project(icon_match.group(1))
                    icon_path, _ = find_project_icon(project["path"])
                    if icon_path is None:
                        raise LauncherError(404, "项目图标不存在")
                    ctype = ICON_MIME_TYPES.get(
                        icon_path.suffix.lower(),
                        mimetypes.guess_type(str(icon_path))[0] or "application/octet-stream",
                    )
                    has_version = bool(urllib.parse.parse_qs(parsed.query).get("v"))
                    cache_control = "private, max-age=3600" if has_version else "no-cache"
                    self._send_file(icon_path, ctype, cache_control)
                    return

            elif method == "POST":
                if path == "/api/picker":
                    self._send_json(HTTPStatus.OK, {"path": select_folder()})
                    return
                if path == "/api/projects/inspect":
                    target = validate_inspect_payload(self._read_json())
                    self._send_json(HTTPStatus.OK, self.service.inspect(target))
                    return
                if path == "/api/projects":
                    payload = validate_project_payload(self._read_json())
                    self._send_json(HTTPStatus.CREATED, self.service.create(payload))
                    return
                match = re.fullmatch(r"/api/projects/([^/]+)/(start|stop|open-folder)", path)
                if match:
                    project_id, action = match.groups()
                    if action == "start":
                        self._send_json(HTTPStatus.OK, self.service.start(project_id))
                    elif action == "stop":
                        self._send_json(HTTPStatus.OK, self.service.stop(project_id))
                    else:
                        project = self.service.require_project(project_id)
                        open_project_directory(project["path"])
                        self._send_empty(HTTPStatus.NO_CONTENT)
                    return

            elif method == "PUT":
                if path == "/api/projects/reorder":
                    ids = validate_reorder_payload(self._read_json())
                    self._send_json(HTTPStatus.OK, self.service.reorder(ids))
                    return
                match = re.fullmatch(r"/api/projects/([^/]+)", path)
                if match:
                    payload = validate_project_payload(self._read_json())
                    self._send_json(HTTPStatus.OK, self.service.update(match.group(1), payload))
                    return

            elif method == "DELETE":
                match = re.fullmatch(r"/api/projects/([^/]+)", path)
                if match:
                    self.service.delete(match.group(1))
                    self._send_empty(HTTPStatus.NO_CONTENT)
                    return

            self._send_json(HTTPStatus.NOT_FOUND, {"detail": "接口不存在"})
        except LauncherError as exc:
            self._send_json(exc.status_code, {"detail": exc.detail})
        except Exception as exc:  # pragma: no cover - defensive guard
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"detail": str(exc)})

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_PUT(self) -> None:
        self._handle("PUT")

    def do_DELETE(self) -> None:
        self._handle("DELETE")


class LauncherHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    # On Windows, SO_REUSEADDR allows multiple processes to bind the same port simultaneously.
    allow_reuse_address = os.name != "nt"

    def __init__(
        self,
        server_address: tuple[str, int],
        service: LauncherService,
    ) -> None:
        self.service = service
        super().__init__(server_address, LauncherRequestHandler)

    def server_bind(self) -> None:
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def create_server(
    data_dir: Path | None = None,
    host: str = HOST,
    port: int = APP_PORT,
) -> LauncherHTTPServer:
    service = LauncherService(data_dir or BASE_DIR / ".local_data")
    return LauncherHTTPServer((host, port), service)


def is_launcher_running(host: str, port: int, timeout: float = 0.5) -> bool:
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        conn.request("GET", "/api/health")
        resp = conn.getresponse()
        if resp.status != HTTPStatus.OK:
            return False
        data = json.loads(resp.read().decode("utf-8"))
        return isinstance(data, dict) and data.get("status") == "ok"
    except (OSError, http.client.HTTPException, ValueError):
        return False
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="本地项目启动器")
    parser.add_argument("--port", type=int, default=APP_PORT, help="管理控制台端口")
    parser.add_argument("--no-browser", action="store_true", help="启动时不自动打开浏览器")
    parser.add_argument("--no-tray", action="store_true", help="不显示系统托盘图标")
    args = parser.parse_args(argv)

    instance_lock = SingleInstanceMutex(f"Local\\WebRouterLauncher_{args.port}") if args.port else None
    if instance_lock is not None and instance_lock.already_running:
        if not args.no_browser:
            webbrowser.open(f"http://{HOST}:{args.port}/")
        return 0

    try:
        server = create_server(port=args.port)
    except OSError:
        if instance_lock is not None:
            instance_lock.release()
        if args.port and is_launcher_running(HOST, args.port):
            if not args.no_browser:
                webbrowser.open(f"http://{HOST}:{args.port}/")
            return 0
        raise
    actual_port = server.server_address[1]
    dashboard_url = f"http://{HOST}:{actual_port}/"

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    if not args.no_browser:
        threading.Thread(
            target=lambda: webbrowser.open(dashboard_url),
            daemon=True,
        ).start()

    shutdown_done = threading.Event()

    def shutdown_all() -> None:
        if shutdown_done.is_set():
            return
        shutdown_done.set()
        server.shutdown()
        server.server_close()
        server.service.processes.stop_all()
        server.service.processes.close()
        if instance_lock is not None:
            instance_lock.release()

    if os.name == "nt" and not args.no_tray:
        def get_running_projects() -> list[dict[str, object]]:
            running_items: list[dict[str, object]] = []
            for project in server.service.store.all():
                if server.service.processes.is_running(project["id"]):
                    running_items.append(
                        {
                            "id": project["id"],
                            "name": project["name"],
                            "port": project["port"],
                            "url": f"http://{HOST}:{project['port']}/",
                        }
                    )
            return running_items

        tray = TrayManager(
            tooltip=f"本地项目启动器 ({actual_port})",
            on_open=lambda: webbrowser.open(dashboard_url),
            on_stop_all=server.service.processes.stop_all,
            on_exit=shutdown_all,
            get_running_count=server.service.processes.running_count,
            get_running_projects=get_running_projects,
            on_open_project=lambda url: webbrowser.open(url),
        )

        def handle_sigint(_signum, _frame) -> None:
            tray.stop()
            shutdown_all()

        signal.signal(signal.SIGINT, handle_sigint)
        try:
            tray.run()
        finally:
            shutdown_all()
        return 0

    try:
        while server_thread.is_alive():
            server_thread.join(timeout=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        shutdown_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())