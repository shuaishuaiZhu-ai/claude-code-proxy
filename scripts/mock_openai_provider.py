from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
import argparse
import json


class MockOpenAIHandler(BaseHTTPRequestHandler):
    server_version = "ccproxy-mock-openai/0.1"

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json({"ok": True})
            return
        self._send_json({"error": {"message": "not found"}}, status=404)

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self._send_json({"error": {"message": "not found"}}, status=404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        if payload.get("stream"):
            self._send_stream()
            return
        self._send_json(
            {
                "id": "chatcmpl_mock",
                "object": "chat.completion",
                "model": payload.get("model", "mock-model"),
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "ccproxy-ok"},
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        )

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_stream(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        for chunk in (
            {"choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]},
            {"choices": [{"index": 0, "delta": {"content": "ccproxy-ok"}, "finish_reason": None}]},
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
        ):
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode("utf-8"))
        self.wfile.write(b"data: [DONE]\n\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Local mock OpenAI-compatible provider for ccproxy.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), MockOpenAIHandler)
    print(f"mock OpenAI-compatible provider on http://{args.host}:{args.port}/v1")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
