from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any
import json

from .config import ProviderProfile


def select_model(requested_model: str | None, profile: ProviderProfile) -> str:
    if not profile.models:
        return requested_model or ""
    if not requested_model:
        return profile.models.get("big") or next(iter(profile.models.values()))
    model_lower = requested_model.lower()
    if "haiku" in model_lower or "small" in model_lower:
        return profile.models.get("small") or profile.models.get("middle") or profile.models.get("big") or requested_model
    if "sonnet" in model_lower or "middle" in model_lower:
        return profile.models.get("middle") or profile.models.get("big") or requested_model
    if "opus" in model_lower or "big" in model_lower:
        return profile.models.get("big") or requested_model
    return profile.models.get("big") or requested_model


def anthropic_to_openai(body: dict[str, Any], profile: ProviderProfile) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": select_model(body.get("model"), profile),
        "messages": [],
    }
    for field in ("max_tokens", "temperature", "top_p", "stop", "stream"):
        if field in body:
            payload[field] = body[field]

    system_messages = _system_to_openai(body.get("system"))
    payload["messages"].extend(system_messages)

    for message in body.get("messages", []):
        payload["messages"].extend(_message_to_openai(message))

    tools = body.get("tools")
    if tools:
        payload["tools"] = [_tool_to_openai(tool) for tool in tools]
        tool_choice = _tool_choice_to_openai(body.get("tool_choice"))
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice

    return payload


def openai_to_anthropic(data: dict[str, Any], requested_model: str | None = None) -> dict[str, Any]:
    choices = data.get("choices") or []
    choice = choices[0] if choices else {}
    message = choice.get("message") or {}
    content_blocks: list[dict[str, Any]] = []

    text = message.get("content")
    if isinstance(text, str) and text:
        content_blocks.append({"type": "text", "text": text})
    elif isinstance(text, list):
        content_blocks.extend(_openai_content_list_to_anthropic(text))

    for tool_call in message.get("tool_calls") or []:
        function = tool_call.get("function") or {}
        arguments = function.get("arguments") or "{}"
        try:
            parsed_arguments = json.loads(arguments)
        except json.JSONDecodeError:
            parsed_arguments = {"raw_arguments": arguments}
        content_blocks.append(
            {
                "type": "tool_use",
                "id": tool_call.get("id", "toolu_0"),
                "name": function.get("name", ""),
                "input": parsed_arguments,
            }
        )

    usage = data.get("usage") or {}
    return {
        "id": data.get("id", "msg_ccproxy"),
        "type": "message",
        "role": "assistant",
        "model": requested_model or data.get("model", ""),
        "content": content_blocks,
        "stop_reason": _finish_reason_to_stop_reason(choice.get("finish_reason"), content_blocks),
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
    }


def openai_stream_to_anthropic_sse(chunks: Iterable[dict[str, Any]], model: str) -> Iterator[bytes]:
    yield _sse(
        "message_start",
        {
            "type": "message_start",
            "message": {
                "id": "msg_ccproxy_stream",
                "type": "message",
                "role": "assistant",
                "model": model,
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        },
    )

    text_started = False
    text_index = 0
    tool_calls: dict[int, dict[str, Any]] = {}
    finish_reason: str | None = None

    for chunk in chunks:
        choices = chunk.get("choices") or []
        if not choices:
            continue
        choice = choices[0]
        finish_reason = choice.get("finish_reason") or finish_reason
        delta = choice.get("delta") or {}

        text_delta = delta.get("content")
        if text_delta:
            if not text_started:
                text_started = True
                yield _sse(
                    "content_block_start",
                    {"type": "content_block_start", "index": text_index, "content_block": {"type": "text", "text": ""}},
                )
            yield _sse(
                "content_block_delta",
                {"type": "content_block_delta", "index": text_index, "delta": {"type": "text_delta", "text": text_delta}},
            )

        for tool_delta in delta.get("tool_calls") or []:
            index = int(tool_delta.get("index", 0))
            state = tool_calls.setdefault(index, {"id": "", "name": "", "arguments": ""})
            if tool_delta.get("id"):
                state["id"] = tool_delta["id"]
            function = tool_delta.get("function") or {}
            if function.get("name"):
                state["name"] = function["name"]
            if function.get("arguments"):
                state["arguments"] += function["arguments"]

    if text_started:
        yield _sse("content_block_stop", {"type": "content_block_stop", "index": text_index})
        next_index = text_index + 1
    else:
        next_index = 0

    for offset, state in enumerate(tool_calls.values()):
        index = next_index + offset
        arguments = state.get("arguments") or "{}"
        try:
            tool_input = json.loads(arguments)
        except json.JSONDecodeError:
            tool_input = {"raw_arguments": arguments}
        yield _sse(
            "content_block_start",
            {
                "type": "content_block_start",
                "index": index,
                "content_block": {
                    "type": "tool_use",
                    "id": state.get("id") or f"call_{index}",
                    "name": state.get("name") or "",
                    "input": tool_input,
                },
            },
        )
        yield _sse("content_block_stop", {"type": "content_block_stop", "index": index})

    stop_reason = _finish_reason_to_stop_reason(finish_reason, [{"type": "tool_use"}] if tool_calls else [])
    yield _sse(
        "message_delta",
        {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {"output_tokens": 0},
        },
    )
    yield _sse("message_stop", {"type": "message_stop"})


def _system_to_openai(system: Any) -> list[dict[str, Any]]:
    if system is None:
        return []
    if isinstance(system, str):
        return [{"role": "system", "content": system}]
    if isinstance(system, list):
        text = "\n".join(str(block.get("text", "")) for block in system if isinstance(block, dict) and block.get("type") == "text")
        return [{"role": "system", "content": text}] if text else []
    return [{"role": "system", "content": str(system)}]


def _message_to_openai(message: dict[str, Any]) -> list[dict[str, Any]]:
    role = message.get("role", "user")
    content = message.get("content", "")
    if isinstance(content, str):
        return [{"role": role, "content": content}]
    if not isinstance(content, list):
        return [{"role": role, "content": str(content)}]

    if role == "assistant":
        return [_assistant_blocks_to_openai(content)]

    output: list[dict[str, Any]] = []
    user_content = _content_blocks_to_openai_content(content)
    if user_content:
        output.append({"role": "user", "content": user_content})
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_result":
            output.append(
                {
                    "role": "tool",
                    "tool_call_id": block.get("tool_use_id", ""),
                    "content": _tool_result_content(block.get("content", "")),
                }
            )
    return output


def _assistant_blocks_to_openai(blocks: list[Any]) -> dict[str, Any]:
    text_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type == "text":
            text_parts.append(str(block.get("text", "")))
        elif block_type == "tool_use":
            tool_calls.append(
                {
                    "id": block.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": block.get("name", ""),
                        "arguments": json.dumps(block.get("input", {}), ensure_ascii=False),
                    },
                }
            )
    message: dict[str, Any] = {"role": "assistant", "content": "\n".join(part for part in text_parts if part) or None}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return message


def _content_blocks_to_openai_content(blocks: list[Any]) -> str | list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    text_only = True
    text_parts: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type == "text":
            text = str(block.get("text", ""))
            text_parts.append(text)
            converted.append({"type": "text", "text": text})
        elif block_type == "image":
            text_only = False
            source = block.get("source") or {}
            if source.get("type") == "base64":
                media_type = source.get("media_type", "application/octet-stream")
                data = source.get("data", "")
                converted.append({"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{data}"}})
        elif block_type == "tool_result":
            continue
    if not converted:
        return ""
    if text_only:
        return "\n".join(part for part in text_parts if part)
    return converted


def _tool_result_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "\n".join(part for part in parts if part)
    return json.dumps(content, ensure_ascii=False)


def _tool_to_openai(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.get("name", ""),
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
        },
    }


def _tool_choice_to_openai(tool_choice: Any) -> Any:
    if tool_choice is None:
        return None
    if isinstance(tool_choice, str):
        return tool_choice
    if not isinstance(tool_choice, dict):
        return None
    choice_type = tool_choice.get("type")
    if choice_type == "auto":
        return "auto"
    if choice_type == "any":
        return "required"
    if choice_type == "tool":
        return {"type": "function", "function": {"name": tool_choice.get("name", "")}}
    return None


def _openai_content_list_to_anthropic(content: list[Any]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            blocks.append({"type": "text", "text": str(item.get("text", ""))})
    return blocks


def _finish_reason_to_stop_reason(reason: str | None, content_blocks: list[dict[str, Any]]) -> str:
    if any(block.get("type") == "tool_use" for block in content_blocks):
        return "tool_use"
    if reason == "length":
        return "max_tokens"
    if reason in {"stop", "eos"}:
        return "end_turn"
    return "end_turn"


def _sse(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")
