from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse
import json

from .client import JsonResult, StreamResult, UpstreamClient
from .config import ProviderProfile, ServerConfig


def build_stdlib_server(server: ServerConfig, profile: ProviderProfile) -> ThreadingHTTPServer:
    client = UpstreamClient(profile)

    class Handler(BaseHTTPRequestHandler):
        server_version = "ccproxy/0.1"

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/health":
                self._send_json(200, {"ok": True, "profile": profile.name, "provider_type": profile.type})
                return
            self._send_json(404, {"error": {"message": "not found"}})

        def do_POST(self) -> None:
            path = urlparse(self.path).path.rstrip("/")
            if path != "/v1/messages":
                self._send_json(404, {"error": {"message": "not found"}})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8")
                body = json.loads(raw) if raw else {}
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json(400, {"error": {"message": str(exc), "type": "invalid_request"}})
                return

            result = client.messages(body)
            if isinstance(result, JsonResult):
                self._send_json(result.status, result.payload)
                return
            self.send_response(result.status)
            self.send_header("Content-Type", result.media_type)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            for chunk in result.chunks:
                self.wfile.write(chunk)
                self.wfile.flush()

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer((server.host, server.port), Handler)


def create_fastapi_app(profile: ProviderProfile) -> Any:
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse, StreamingResponse
    except ImportError as exc:
        raise RuntimeError("FastAPI is not installed; use the stdlib server or install project dependencies.") from exc

    app = FastAPI(title="cc-provider-proxy", version="0.1.0")
    client = UpstreamClient(profile)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "profile": profile.name, "provider_type": profile.type}

    @app.post("/v1/messages")
    async def messages(request: Request) -> Any:
        body = await request.json()
        result = client.messages(body)
        if isinstance(result, JsonResult):
            return JSONResponse(result.payload, status_code=result.status)
        return StreamingResponse(result.chunks, media_type=result.media_type, status_code=result.status)

    return app


def serve_stdlib(server: ServerConfig, profile: ProviderProfile) -> None:
    httpd = build_stdlib_server(server, profile)
    print(f"ccproxy serving {profile.name} on http://{server.host}:{server.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
