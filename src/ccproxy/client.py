from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json

from .config import ProviderProfile
from .secrets import get_api_key
from .translator import anthropic_to_openai, openai_stream_to_anthropic_sse, openai_to_anthropic, select_model


@dataclass(frozen=True)
class JsonResult:
    status: int
    payload: dict[str, Any]


@dataclass(frozen=True)
class StreamResult:
    status: int
    media_type: str
    chunks: Iterator[bytes]


class UpstreamClient:
    def __init__(self, profile: ProviderProfile, timeout: int = 120) -> None:
        self.profile = profile
        self.timeout = timeout

    def messages(self, body: dict[str, Any]) -> JsonResult | StreamResult:
        if self.profile.type == "anthropic-compatible":
            return self._anthropic_passthrough(body)
        return self._openai_compatible(body)

    def _openai_compatible(self, body: dict[str, Any]) -> JsonResult | StreamResult:
        payload = anthropic_to_openai(body, self.profile)
        if payload.get("stream"):
            stream = self._post_stream(_join_endpoint(self.profile.base_url, "chat/completions"), payload)
            model = select_model(body.get("model"), self.profile)
            return StreamResult(status=200, media_type="text/event-stream", chunks=openai_stream_to_anthropic_sse(_openai_sse_json(stream), model))

        status, data = self._post_json(_join_endpoint(self.profile.base_url, "chat/completions"), payload)
        if status >= 400:
            return JsonResult(status=status, payload=data)
        return JsonResult(status=status, payload=openai_to_anthropic(data, requested_model=body.get("model")))

    def _anthropic_passthrough(self, body: dict[str, Any]) -> JsonResult | StreamResult:
        forwarded = dict(body)
        forwarded["model"] = select_model(body.get("model"), self.profile)
        if forwarded.get("stream"):
            stream = self._post_stream(_join_endpoint(self.profile.base_url, "v1/messages"), forwarded)
            return StreamResult(status=200, media_type="text/event-stream", chunks=stream)
        status, data = self._post_json(_join_endpoint(self.profile.base_url, "v1/messages"), forwarded)
        return JsonResult(status=status, payload=data)

    def _post_json(self, url: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        request = self._request(url, payload)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return response.status, json.loads(raw) if raw else {}
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                data = {"error": {"message": raw}}
            return exc.code, data
        except URLError as exc:
            return 502, {"error": {"message": str(exc.reason), "type": "upstream_connection_error"}}

    def _post_stream(self, url: str, payload: dict[str, Any]) -> Iterator[bytes]:
        request = self._request(url, payload)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                for line in response:
                    yield line
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            yield f"event: error\ndata: {json.dumps({'error': raw, 'status': exc.code})}\n\n".encode("utf-8")
        except URLError as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc.reason), 'status': 502})}\n\n".encode("utf-8")

    def _request(self, url: str, payload: dict[str, Any]) -> Request:
        headers = {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
        }
        headers.update(self.profile.headers)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return Request(url, data=data, headers=headers, method="POST")

    def _api_key(self) -> str:
        if not self.profile.api_key_env:
            return ""
        return get_api_key(self.profile.api_key_env)


def _join_endpoint(base_url: str, suffix: str) -> str:
    clean_base = base_url.rstrip("/")
    clean_suffix = suffix.strip("/")
    if clean_base.endswith(clean_suffix):
        return clean_base
    return f"{clean_base}/{clean_suffix}"


def _openai_sse_json(lines: Iterator[bytes]) -> Iterator[dict[str, Any]]:
    for raw_line in lines:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line or line.startswith(":") or not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if data == "[DONE]":
            break
        try:
            yield json.loads(data)
        except json.JSONDecodeError:
            continue
