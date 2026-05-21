from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any
import json

from .config import ProviderProfile


def select_model(requested_model: str | None, profile: ProviderProfile) -> str:
    if profile.upstream_model:
        return _model_alias(profile.upstream_model, profile) or profile.upstream_model
    if not profile.models:
        return requested_model or ""
    if not requested_model:
        return profile.models.get("big") or next(iter(profile.models.values()))
    exact = _model_alias(requested_model, profile)
    if exact:
        return exact
    model_lower = requested_model.lower()
    if "haiku" in model_lower or "small" in model_lower:
        return profile.models.get("small") or profile.models.get("middle") or profile.models.get("big") or requested_model
    if "sonnet" in model_lower or "middle" in model_lower:
        return profile.models.get("middle") or profile.models.get("big") or requested_model
    if "opus" in model_lower or "big" in model_lower:
        return profile.models.get("big") or requested_model
    return profile.models.get("big") or requested_model


def _model_alias(requested_model: str, profile: ProviderProfile) -> str | None:
    if requested_model in profile.models:
        return profile.models[requested_model]
    model_lower = requested_model.lower()
    for alias, model in profile.models.items():
        if alias.lower() == model_lower:
            return model
    return None


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


def openai_to_anthropic(
    data: dict[str, Any],
    requested_model: str | None = None,
    requested_tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
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
        validation_error = _tool_input_error(function.get("name", ""), parsed_arguments, requested_tools)
        if validation_error:
            content_blocks.append({"type": "text", "text": validation_error})
            continue
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


def openai_stream_to_anthropic_sse(
    chunks: Iterable[dict[str, Any]],
    model: str,
    requested_tools: list[dict[str, Any]] | None = None,
) -> Iterator[bytes]:
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
    emitted_tool_call = False
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
        validation_error = _tool_input_error(state.get("name") or "", tool_input, requested_tools)
        if validation_error:
            yield from _text_block_sse(index, validation_error)
            continue
        emitted_tool_call = True
        yield _sse(
            "content_block_start",
            {
                "type": "content_block_start",
                "index": index,
                "content_block": {
                    "type": "tool_use",
                    "id": state.get("id") or f"call_{index}",
                    "name": state.get("name") or "",
                    "input": {},
                },
            },
        )
        yield _sse(
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": index,
                "delta": {"type": "input_json_delta", "partial_json": json.dumps(tool_input, ensure_ascii=False)},
            },
        )
        yield _sse("content_block_stop", {"type": "content_block_stop", "index": index})

    stop_reason = _finish_reason_to_stop_reason(finish_reason, [{"type": "tool_use"}] if emitted_tool_call else [])
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


def _tool_input_error(tool_name: str, tool_input: Any, requested_tools: list[dict[str, Any]] | None) -> str | None:
    if not requested_tools:
        return None
    schema = _tool_schema(tool_name, requested_tools)
    if not schema:
        return f"Skipped invalid tool call `{tool_name}`: unknown tool."
    required = schema.get("required") or []
    if not isinstance(tool_input, dict):
        return f"Skipped invalid tool call `{tool_name}`: input must be a JSON object."
    missing = [field for field in required if field not in tool_input or tool_input[field] in (None, "")]
    if not missing:
        type_errors = _tool_type_errors(tool_input, schema)
        if not type_errors:
            return None
        return f"Skipped invalid tool call `{tool_name}`: invalid parameter type(s): {', '.join(type_errors)}."
    fields = ", ".join(str(field) for field in missing)
    return f"Skipped invalid tool call `{tool_name}`: missing required parameter(s): {fields}."


def _tool_schema(tool_name: str, requested_tools: list[dict[str, Any]]) -> dict[str, Any] | None:
    for tool in requested_tools:
        if tool.get("name") == tool_name:
            schema = tool.get("input_schema")
            return schema if isinstance(schema, dict) else None
    return None


def _tool_type_errors(tool_input: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    properties = schema.get("properties") or {}
    if not isinstance(properties, dict):
        return []
    errors: list[str] = []
    for field, value in tool_input.items():
        field_schema = properties.get(field)
        if not isinstance(field_schema, dict) or "type" not in field_schema:
            continue
        expected = field_schema["type"]
        if not _json_type_matches(value, expected):
            errors.append(f"{field} expected {_format_json_type(expected)}")
    return errors


def _json_type_matches(value: Any, expected: Any) -> bool:
    expected_types = expected if isinstance(expected, list) else [expected]
    for expected_type in expected_types:
        if expected_type == "string" and isinstance(value, str):
            return True
        if expected_type == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if expected_type == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if expected_type == "boolean" and isinstance(value, bool):
            return True
        if expected_type == "object" and isinstance(value, dict):
            return True
        if expected_type == "array" and isinstance(value, list):
            return True
        if expected_type == "null" and value is None:
            return True
    return False


def _format_json_type(expected: Any) -> str:
    if isinstance(expected, list):
        return " or ".join(str(item) for item in expected)
    return str(expected)


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


def _text_block_sse(index: int, text: str) -> Iterator[bytes]:
    yield _sse(
        "content_block_start",
        {"type": "content_block_start", "index": index, "content_block": {"type": "text", "text": ""}},
    )
    yield _sse(
        "content_block_delta",
        {"type": "content_block_delta", "index": index, "delta": {"type": "text_delta", "text": text}},
    )
    yield _sse("content_block_stop", {"type": "content_block_stop", "index": index})
