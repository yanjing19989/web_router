import http.client
import json
import os
import threading
from pathlib import Path

import pytest

import app as launcher


class LiveResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status_code = status
        self._body = body

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

    def request(self, method: str, path: str, json_body=None) -> LiveResponse:
        conn = http.client.HTTPConnection(launcher.HOST, self.port, timeout=5)
        try:
            headers = {}
            body = None
            if json_body is not None:
                body = json.dumps(json_body).encode("utf-8")
                headers["Content-Type"] = "application/json"
            conn.request(method, path, body=body, headers=headers)
            resp = conn.getresponse()
            return LiveResponse(resp.status, resp.read())
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
