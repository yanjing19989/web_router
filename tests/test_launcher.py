import http.client
import json
import os
import threading
from pathlib import Path

import pytest

import app as launcher


class LiveResponse:
    def __init__(self, status: int, body: bytes, headers: dict[str, str] | None = None) -> None:
        self.status_code = status
        self._body = body
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}

    def json(self):
        return json.loads(self._body.decode("utf-8"))


class LiveClient:
    def __init__(self, data_dir: Path) -> None:
        self.server = launcher.create_server(data_dir=data_dir, port=0)
        self.port = self.server.server_address[1]
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> "LiveClient":
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.server.service.processes.stop_all()
        self._thread.join(timeout=2)

    def request(self, method: str, path: str, json_body=None, extra_headers=None) -> LiveResponse:
        conn = http.client.HTTPConnection(launcher.HOST, self.port, timeout=5)
        try:
            headers = dict(extra_headers or {})
            body = None
            if json_body is not None:
                body = json.dumps(json_body).encode("utf-8")
                headers["Content-Type"] = "application/json"
            conn.request(method, path, body=body, headers=headers)
            resp = conn.getresponse()
            return LiveResponse(resp.status, resp.read(), dict(resp.getheaders()))
        finally:
            conn.close()

    def get(self, path: str) -> LiveResponse:
        return self.request("GET", path)

    def post(self, path: str, json=None) -> LiveResponse:
        return self.request("POST", path, json_body=json)

    def put(self, path: str, json=None) -> LiveResponse:
        return self.request("PUT", path, json_body=json)

    def delete(self, path: str) -> LiveResponse:
        return self.request("DELETE", path)


@pytest.mark.parametrize(
    ("script", "dependencies", "expected_detector", "command_part"),
    [
        ("vite", {"vite": "latest"}, "Vite", "--host 127.0.0.1 --port {port}"),
        ("next dev", {"next": "latest"}, "Next.js", "-H 127.0.0.1 -p {port}"),
        ("react-scripts start", {"react-scripts": "latest"}, "react-scripts", "npm run dev"),
        ("node server.js", {}, "npm · dev", "npm run dev"),
    ],
)
def test_detect_npm_variants(
    tmp_path: Path,
    script: str,
    dependencies: dict,
    expected_detector: str,
    command_part: str,
) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"serve": "serve", "start": "start", "dev": script}, "devDependencies": dependencies}),
        encoding="utf-8",
    )

    result = launcher.detect_project(tmp_path)

    assert result is not None
    assert result["type"] == "npm"
    assert result["detector"] == expected_detector
    assert command_part in result["command"]


@pytest.mark.parametrize(
    ("files", "detector", "command_part"),
    [
        ({"manage.py": ""}, "Django", "manage.py runserver 127.0.0.1:{port}"),
        ({"main.py": "from fastapi import FastAPI\napp = FastAPI()"}, "FastAPI", "uvicorn main:app"),
        ({"app.py": "from flask import Flask\napp = Flask(__name__)"}, "Flask", "flask --app app:app"),
        ({"main.py": "print('hello')"}, "Python · main.py", "main.py"),
        ({"index.html": "<!doctype html>"}, "静态站点", "http.server {port}"),
    ],
)
def test_detect_python_and_static_projects(
    tmp_path: Path, files: dict[str, str], detector: str, command_part: str
) -> None:
    for name, content in files.items():
        (tmp_path / name).write_text(content, encoding="utf-8")

    result = launcher.detect_project(tmp_path)

    assert result is not None
    assert result["detector"] == detector
    assert command_part in result["command"]


def test_detect_uses_virtualenv_and_higher_priority_entry(tmp_path: Path) -> None:
    interpreter = tmp_path / ".venv" / "Scripts" / "python.exe"
    interpreter.parent.mkdir(parents=True)
    interpreter.touch()
    (tmp_path / "main.py").write_text("print('python')", encoding="utf-8")
    (tmp_path / "index.html").write_text("static", encoding="utf-8")

    result = launcher.detect_project(tmp_path)

    assert result is not None
    assert result["type"] == "python"
    assert str(interpreter) in result["command"]


def test_unknown_directory_is_not_detected(tmp_path: Path) -> None:
    assert launcher.detect_project(tmp_path) is None


def test_allocate_port_skips_configured_and_occupied(tmp_path: Path, monkeypatch) -> None:
    service = launcher.LauncherService(tmp_path / "data")
    service.store.add(
        {
            "id": "existing",
            "path": str(tmp_path / "one"),
            "name": "one",
            "type": "static",
            "command": "command",
            "port": 3001,
        }
    )
    monkeypatch.setattr(launcher, "port_is_available", lambda port: port not in {3000, 3002})

    assert service.allocate_port() == 3003


def test_project_api_create_list_conflicts_and_delete(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "site"
    project_dir.mkdir()
    (project_dir / "index.html").write_text("site", encoding="utf-8")
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    monkeypatch.setattr(launcher, "port_is_available", lambda _: True)

    with LiveClient(tmp_path / "data") as client:
        inspected = client.post("/api/projects/inspect", json={"path": str(project_dir)})
        assert inspected.status_code == 200
        payload = {
            key: inspected.json()[key]
            for key in ("path", "name", "type", "command", "port")
        }
        created = client.post("/api/projects", json=payload)
        assert created.status_code == 201
        project_id = created.json()["id"]

        listing = client.get("/api/projects").json()
        assert listing["summary"] == {
            "total": 1,
            "running": 0,
            "total_memory_uss_bytes": 0,
            "total_memory_vms_bytes": 0,
        }
        assert listing["projects"][0]["status"] == "stopped"

        updated_payload = {**payload, "name": "updated", "command": "new command"}
        updated = client.put(f"/api/projects/{project_id}", json=updated_payload)
        assert updated.status_code == 200
        assert updated.json()["name"] == "updated"
        assert updated.json()["command"] == "new command"
        assert client.get("/api/projects").json()["projects"][0]["name"] == "updated"

        duplicate_path = client.post("/api/projects", json=payload)
        assert duplicate_path.status_code == 409
        assert duplicate_path.json()["detail"] == "该目录已添加"

        duplicate_port_payload = {**payload, "path": str(other_dir), "name": "other"}
        duplicate_port = client.post("/api/projects", json=duplicate_port_payload)
        assert duplicate_port.status_code == 409

        service = client.server.service
        monkeypatch.setattr(service.processes, "is_running", lambda _: True)
        blocked_update = client.put(f"/api/projects/{project_id}", json=payload)
        assert blocked_update.status_code == 409
        assert blocked_update.json()["detail"] == "请先停止项目再编辑"
        blocked_delete = client.delete(f"/api/projects/{project_id}")
        assert blocked_delete.status_code == 409

        monkeypatch.setattr(service.processes, "is_running", lambda _: False)
        assert client.delete(f"/api/projects/{project_id}").status_code == 204
        assert client.get("/api/projects").json()["summary"]["total"] == 0


def test_project_validation_errors(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    base = {
        "path": str(project_dir),
        "name": "project",
        "type": "python",
        "command": "python main.py",
        "port": 3000,
    }

    with LiveClient(tmp_path / "data") as client:
        invalid_directory = client.post(
            "/api/projects", json={**base, "path": str(tmp_path / "missing")}
        )
        assert invalid_directory.status_code == 422

        invalid_port = client.post("/api/projects", json={**base, "port": 2999})
        assert invalid_port.status_code == 422

        monkeypatch.setattr(launcher, "port_is_available", lambda _: False)
        occupied_port = client.post("/api/projects", json=base)
        assert occupied_port.status_code == 409
        assert "已被占用" in occupied_port.json()["detail"]

        unknown = client.post("/api/projects/inspect", json={"path": str(project_dir)})
        assert unknown.status_code == 422


@pytest.mark.skipif(os.name != "nt", reason="Windows process management")
def test_static_project_start_stop_and_delete(tmp_path: Path) -> None:
    project_dir = tmp_path / "running-site"
    project_dir.mkdir()
    (project_dir / "index.html").write_text("running", encoding="utf-8")

    with LiveClient(tmp_path / "data") as client:
        inspected = client.post(
            "/api/projects/inspect", json={"path": str(project_dir)}
        ).json()
        payload = {
            key: inspected[key]
            for key in ("path", "name", "type", "command", "port")
        }
        project = client.post("/api/projects", json=payload).json()
        project_id = project["id"]

        started = client.post(f"/api/projects/{project_id}/start")
        assert started.status_code == 200
        assert started.json()["status"] == "running"
        assert started.json()["pid"] is not None
        assert (
            client.put(f"/api/projects/{project_id}", json=payload).status_code
            == 409
        )
        assert client.delete(f"/api/projects/{project_id}").status_code == 409

        stopped = client.post(f"/api/projects/{project_id}/stop")
        assert stopped.status_code == 200
        assert stopped.json()["status"] == "stopped"
        assert client.delete(f"/api/projects/{project_id}").status_code == 204


@pytest.mark.skipif(os.name != "nt", reason="Windows paths are case-insensitive")
def test_duplicate_paths_are_case_insensitive(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "CaseProject"
    project_dir.mkdir()
    monkeypatch.setattr(launcher, "port_is_available", lambda _: True)
    payload = {
        "path": str(project_dir),
        "name": "first",
        "type": "python",
        "command": "python main.py",
        "port": 3000,
    }

    with LiveClient(tmp_path / "data") as client:
        assert client.post("/api/projects", json=payload).status_code == 201
        duplicate = client.post(
            "/api/projects",
            json={**payload, "path": str(project_dir).swapcase(), "port": 3001},
        )
        assert duplicate.status_code == 409


def test_metrics_all_uses_single_process_snapshot(monkeypatch) -> None:
    class FakeMem:
        def __init__(self, uss: int, vms: int) -> None:
            self.uss = uss
            self.vms = vms

    class FakeProc:
        def __init__(self, pid: int, ppid: int, cpu: float, uss: int, vms: int) -> None:
            self.pid = pid
            self.info = {"ppid": ppid}
            self._cpu = cpu
            self._mem = FakeMem(uss, vms)

        def cpu_percent(self, interval=None) -> float:
            return self._cpu

        def memory_full_info(self) -> FakeMem:
            return self._mem

    class FakePopen:
        def __init__(self, pid: int) -> None:
            self.pid = pid

        def poll(self):
            return None

    procs = {
        100: FakeProc(100, 1, 1.5, 1000, 4000),
        101: FakeProc(101, 100, 2.5, 2000, 6000),
        200: FakeProc(200, 1, 3.0, 5000, 9000),
    }
    snapshot_calls = 0

    class FakePsutil:
        NoSuchProcess = LookupError
        AccessDenied = PermissionError

        @staticmethod
        def Process(pid: int) -> FakeProc:
            return procs[pid]

        @staticmethod
        def process_iter(attrs=None):
            nonlocal snapshot_calls
            snapshot_calls += 1
            return list(procs.values())

    monkeypatch.setattr(launcher, "psutil", FakePsutil)
    manager = launcher.ProcessManager()
    manager._runtimes["p1"] = launcher.RuntimeProcess(FakePopen(100))
    manager._runtimes["p2"] = launcher.RuntimeProcess(FakePopen(200))

    result = manager.metrics_all(["p1", "p2", "p3"])

    assert snapshot_calls == 1
    assert result["p1"]["cpu_percent"] == 4.0
    assert result["p1"]["memory_uss_bytes"] == 3000
    assert result["p1"]["memory_vms_bytes"] == 10000
    assert result["p2"]["memory_uss_bytes"] == 5000
    assert result["p3"]["status"] == "stopped"


def test_stop_all_terminates_all_trees_in_one_batch(monkeypatch) -> None:
    terminated: list[int] = []
    waited_batches: list[list[int]] = []

    class FakeProc:
        def __init__(self, pid: int, ppid: int) -> None:
            self.pid = pid
            self.info = {"ppid": ppid}

        def terminate(self) -> None:
            terminated.append(self.pid)

        def kill(self) -> None:
            pass

    class FakePopen:
        def __init__(self, pid: int) -> None:
            self.pid = pid

    procs = {
        10: FakeProc(10, 1),
        11: FakeProc(11, 10),
        20: FakeProc(20, 1),
    }

    class FakePsutil:
        NoSuchProcess = LookupError
        AccessDenied = PermissionError

        @staticmethod
        def Process(pid: int) -> FakeProc:
            return procs[pid]

        @staticmethod
        def process_iter(attrs=None):
            return list(procs.values())

        @staticmethod
        def wait_procs(targets, timeout=None):
            waited_batches.append([p.pid for p in targets])
            return targets, []

    monkeypatch.setattr(launcher, "psutil", FakePsutil)
    manager = launcher.ProcessManager()
    manager._runtimes["a"] = launcher.RuntimeProcess(FakePopen(10))
    manager._runtimes["b"] = launcher.RuntimeProcess(FakePopen(20))

    manager.stop_all()

    assert len(waited_batches) == 1
    assert set(terminated) == {10, 11, 20}
    assert terminated.index(11) < terminated.index(10)


def test_static_asset_etag_and_304(tmp_path: Path) -> None:
    with LiveClient(tmp_path / "data") as client:
        first = client.get("/static/app.js")
        assert first.status_code == 200
        etag = first.headers.get("etag")
        assert etag

        second = client.request("GET", "/static/app.js", extra_headers={"If-None-Match": etag})
        assert second.status_code == 304
        assert second._body == b""


def test_process_manager_assigns_and_terminates_project_job(tmp_path: Path, monkeypatch) -> None:
    events: list[tuple[str, int | None]] = []

    class FakeJob:
        def assign(self, proc) -> bool:
            events.append(("assign", proc.pid))
            return True

        def terminate(self, exit_code: int = 1) -> bool:
            events.append(("terminate", exit_code))
            return True

        def close(self) -> None:
            events.append(("close", None))

    class FakePopen:
        pid = 4321

        def wait(self, timeout=None):
            raise launcher.subprocess.TimeoutExpired("cmd", timeout or 0)

        def terminate(self) -> None:
            pass

        def kill(self) -> None:
            pass

    manager = launcher.ProcessManager()
    monkeypatch.setattr(launcher, "ProcessJob", FakeJob)
    monkeypatch.setattr(launcher, "psutil", None)
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *args, **kwargs: FakePopen())

    manager.start({"id": "p1", "path": str(tmp_path), "command": "echo hi", "port": 3000})
    manager.stop("p1")

    assert events == [("assign", 4321), ("terminate", 1), ("close", None)]


def test_start_captures_stderr_on_immediate_crash(tmp_path: Path) -> None:
    manager = launcher.ProcessManager()
    cmd = f"{launcher.shell_quote(launcher.sys.executable)} -c \"import sys; sys.stderr.write('boom-failure\\n'); sys.exit(2)\""
    with pytest.raises(launcher.LauncherError) as exc_info:
        manager.start({"id": "crash", "path": str(tmp_path), "command": cmd, "port": 3000})
    assert "退出码：2" in exc_info.value.detail
    assert "boom-failure" in exc_info.value.detail


def test_main_opens_existing_instance_when_port_in_use(tmp_path: Path, monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(launcher.webbrowser, "open", lambda url: opened.append(url) or True)

    with LiveClient(tmp_path / "data") as client:
        code = launcher.main(["--port", str(client.port), "--no-tray"])
        assert code == 0
        assert opened == [f"http://{launcher.HOST}:{client.port}/"]


def test_project_icon_discovery_and_endpoint(tmp_path: Path, monkeypatch) -> None:
    site_with_icon = tmp_path / "with-icon"
    (site_with_icon / "public").mkdir(parents=True)
    (site_with_icon / "index.html").write_text("hi", encoding="utf-8")
    svg_bytes = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"></svg>'
    (site_with_icon / "public" / "favicon.svg").write_bytes(svg_bytes)

    site_without_icon = tmp_path / "no-icon"
    site_without_icon.mkdir()
    (site_without_icon / "index.html").write_text("hi", encoding="utf-8")
    monkeypatch.setattr(launcher, "port_is_available", lambda _: True)

    with LiveClient(tmp_path / "data") as client:
        p1 = client.post("/api/projects", json={
            "path": str(site_with_icon), "name": "alpha", "type": "static",
            "command": "python -m http.server {port}", "port": 3010,
        }).json()
        p2 = client.post("/api/projects", json={
            "path": str(site_without_icon), "name": "beta", "type": "static",
            "command": "python -m http.server {port}", "port": 3011,
        }).json()

        assert p1["icon_url"] and p1["icon_url"].startswith(f"/api/projects/{p1['id']}/icon?v=")
        assert p2["icon_url"] is None

        icon_resp = client.get(p1["icon_url"])
        assert icon_resp.status_code == 200
        assert icon_resp._body == svg_bytes
        assert "image/svg+xml" in icon_resp.headers.get("content-type", "")
        assert client.get(f"/api/projects/{p2['id']}/icon").status_code == 404


def test_tray_menu_text_escaping_and_truncation() -> None:
    import win32_ui

    assert win32_ui._escape_menu_text("R&D App") == "R&&D App"
    long_name = "a" * 50
    escaped = win32_ui._escape_menu_text(long_name, max_len=20)
    assert len(escaped) == 20
    assert escaped.endswith("…")


def test_tray_dark_mode_detection_and_fallback(monkeypatch) -> None:
    import win32_ui

    values = {"SystemUsesLightTheme": False, "AppsUseLightTheme": True}
    monkeypatch.setattr(win32_ui, "_read_light_theme_flag", lambda key: values.get(key))

    assert win32_ui.is_system_dark_mode() is True
    assert win32_ui.is_apps_dark_mode() is False

    values = {"AppsUseLightTheme": False}
    assert win32_ui.is_system_dark_mode() is True

    values = {"SystemUsesLightTheme": True, "AppsUseLightTheme": True}
    assert win32_ui.is_system_dark_mode() is False


def test_apply_menu_theme_switches_and_flushes(monkeypatch) -> None:
    import win32_ui

    calls: list[tuple] = []
    monkeypatch.setattr(win32_ui.os, "name", "nt")
    monkeypatch.setattr(win32_ui, "_ensure_uxtheme_loaded", lambda: None)
    monkeypatch.setattr(win32_ui, "_is_high_contrast_enabled", lambda: False)
    monkeypatch.setattr(win32_ui, "_APPLIED_APP_MODE", None)
    monkeypatch.setattr(win32_ui, "PREFERRED_APP_MODE_DEFAULT", 0, raising=False)
    monkeypatch.setattr(win32_ui, "PREFERRED_APP_MODE_ALLOW_DARK", 1, raising=False)
    monkeypatch.setattr(win32_ui, "PREFERRED_APP_MODE_FORCE_DARK", 2, raising=False)
    monkeypatch.setattr(win32_ui, "PREFERRED_APP_MODE_FORCE_LIGHT", 3, raising=False)
    monkeypatch.setattr(win32_ui, "_UXTHEME_SET_PREFERRED_APP_MODE", lambda mode: calls.append(("mode", mode)))
    monkeypatch.setattr(win32_ui, "_UXTHEME_ALLOW_DARK_WINDOW", lambda hwnd, allow: calls.append(("win", hwnd, allow)))
    monkeypatch.setattr(win32_ui, "_UXTHEME_FLUSH_MENU_THEMES", lambda: calls.append(("flush",)))

    monkeypatch.setattr(win32_ui, "is_system_dark_mode", lambda: True)
    assert win32_ui._apply_menu_theme(123) is True
    assert calls == [("mode", 2), ("win", 123, True), ("flush",)]

    # Unchanged theme skips redundant flush
    calls.clear()
    assert win32_ui._apply_menu_theme(123) is True
    assert calls == []

    # Switching to light mode triggers ForceLight + flush
    monkeypatch.setattr(win32_ui, "is_system_dark_mode", lambda: False)
    assert win32_ui._apply_menu_theme(123) is False
    assert calls == [("mode", 3), ("win", 123, False), ("flush",)]

    # High contrast reverts to Default
    calls.clear()
    monkeypatch.setattr(win32_ui, "_is_high_contrast_enabled", lambda: True)
    assert win32_ui._apply_menu_theme(123) is False
    assert calls == [("mode", 0), ("win", 123, False), ("flush",)]


def test_python_executable_prefers_console_python_over_pythonw(tmp_path: Path, monkeypatch) -> None:
    py_dir = tmp_path / "py"
    py_dir.mkdir()
    pythonw = py_dir / "pythonw.exe"
    python_exe = py_dir / "python.exe"
    pythonw.touch()
    python_exe.touch()

    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    monkeypatch.setattr(launcher.sys, "executable", str(pythonw))
    assert launcher.python_executable(project_dir) == python_exe

    python_exe.unlink()
    assert launcher.python_executable(project_dir) == pythonw


def test_main_exits_early_when_single_instance_mutex_held(monkeypatch) -> None:
    opened: list[str] = []

    class HeldMutex:
        def __init__(self, name: str) -> None:
            self.name = name
            self.already_running = True

        def release(self) -> None:
            pass

    monkeypatch.setattr(launcher, "SingleInstanceMutex", HeldMutex)
    monkeypatch.setattr(launcher.webbrowser, "open", lambda url: opened.append(url) or True)
    monkeypatch.setattr(launcher, "create_server", lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not bind")))

    assert launcher.main(["--port", "8888", "--no-tray"]) == 0
    assert opened == [f"http://{launcher.HOST}:8888/"]

    opened.clear()
    assert launcher.main(["--port", "8888", "--no-browser", "--no-tray"]) == 0
    assert opened == []


def test_project_reorder_api_and_validation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(launcher, "port_is_available", lambda _: True)
    dirs = []
    for name in ("alpha", "beta", "gamma"):
        d = tmp_path / name
        d.mkdir()
        (d / "index.html").write_text(name, encoding="utf-8")
        dirs.append((name, d))

    with LiveClient(tmp_path / "data") as client:
        ids = []
        for idx, (name, d) in enumerate(dirs):
            resp = client.post(
                "/api/projects",
                json={
                    "path": str(d),
                    "name": name,
                    "type": "static",
                    "command": "python -m http.server {port}",
                    "port": 3100 + idx,
                },
            )
            assert resp.status_code == 201
            ids.append(resp.json()["id"])

        reordered = [ids[2], ids[0], ids[1]]
        resp = client.put("/api/projects/reorder", json={"ids": reordered})
        assert resp.status_code == 200
        assert [item["id"] for item in resp.json()["projects"]] == reordered
        assert [item["id"] for item in client.get("/api/projects").json()["projects"]] == reordered

        # Persistence check across reload
        reloaded = launcher.ProjectStore(tmp_path / "data")
        assert [item["id"] for item in reloaded.all()] == reordered

        # Validation failures
        assert client.put("/api/projects/reorder", json={"ids": [ids[0]]}).status_code == 422
        assert client.put("/api/projects/reorder", json={"ids": [ids[0], ids[0], ids[1]]}).status_code == 422
        assert client.put("/api/projects/reorder", json={"ids": [ids[0], ids[1], "unknown"]}).status_code == 422
        assert client.put("/api/projects/reorder", json={"bad": []}).status_code == 422


def test_find_project_icon_skips_heavy_dirs_and_uses_cache(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "npm-app"
    (project_dir / "node_modules" / "pkg").mkdir(parents=True)
    (project_dir / "node_modules" / "pkg" / "favicon.ico").write_bytes(b"dep-icon")
    (project_dir / ".venv" / "lib").mkdir(parents=True)
    (project_dir / ".venv" / "lib" / "icon.png").write_bytes(b"venv-icon")
    (project_dir / "dist" / "assets").mkdir(parents=True)
    built_icon = project_dir / "dist" / "assets" / "favicon-abc123.svg"
    built_icon.write_bytes(b"<svg></svg>")

    launcher._ICON_CACHE.clear()
    found, mtime_ns = launcher.find_project_icon(project_dir)
    assert found == built_icon
    assert mtime_ns > 0

    # Cached positive hit should only stat the icon file without rescanning
    scan_calls = 0
    real_search = launcher._search_project_icon

    def counting_search(root: Path):
        nonlocal scan_calls
        scan_calls += 1
        return real_search(root)

    monkeypatch.setattr(launcher, "_search_project_icon", counting_search)
    found_again, _ = launcher.find_project_icon(project_dir)
    assert found_again == built_icon
    assert scan_calls == 0

    # Deleting the cached icon triggers a rescan and returns None (ignoring node_modules/.venv)
    built_icon.unlink()
    found_after_delete, mtime_after_delete = launcher.find_project_icon(project_dir)
    assert found_after_delete is None
    assert mtime_after_delete == 0
    assert scan_calls == 1

    # Negative cache prevents repeated rescans within TTL
    assert launcher.find_project_icon(project_dir) == (None, 0)
    assert scan_calls == 1