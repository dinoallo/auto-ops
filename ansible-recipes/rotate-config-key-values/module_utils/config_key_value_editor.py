"""Format-preserving scalar updates for TOML and YAML configuration files."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence, Tuple


class ConfigEditError(ValueError):
    """Raised when a requested configuration update is unsafe or invalid."""


@dataclass(frozen=True)
class _Replacement:
    start: int
    end: int
    value: str
    path: str


_MISSING = object()
_TOML_BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


def replace_config_values(
    content: str, config_format: str, updates: Sequence[Dict[str, Any]]
) -> Tuple[str, List[str]]:
    """Return content with all requested scalar values replaced.

    Every requested path must resolve to exactly one scalar node. All paths are
    resolved before any replacement is applied, so a failed update cannot
    produce a partially modified file.
    """

    if not isinstance(content, str):
        raise ConfigEditError("configuration content must be text")
    if not isinstance(updates, list) or not updates:
        raise ConfigEditError("updates must be a non-empty list")

    normalized_format = str(config_format).lower()
    if normalized_format not in {"toml", "yaml"}:
        raise ConfigEditError("config_format must be either 'toml' or 'yaml'")

    normalized_updates = _normalize_updates(updates, normalized_format)
    if normalized_format == "toml":
        replacements = _find_toml_replacements(content, normalized_updates)
    else:
        replacements = _find_yaml_replacements(content, normalized_updates)

    _ensure_non_overlapping(replacements)

    updated_paths = []
    updated_content = content
    for replacement in sorted(replacements, key=lambda item: item.start, reverse=True):
        old_value = updated_content[replacement.start : replacement.end]
        if old_value != replacement.value:
            updated_paths.append(replacement.path)
            updated_content = (
                updated_content[: replacement.start]
                + replacement.value
                + updated_content[replacement.end :]
            )

    return updated_content, list(reversed(updated_paths))


def _normalize_updates(
    updates: Sequence[Dict[str, Any]], config_format: str
) -> List[Tuple[Tuple[Any, ...], Any, str]]:
    normalized = []
    seen_paths = set()

    for update_number, update in enumerate(updates, start=1):
        if not isinstance(update, dict):
            raise ConfigEditError("update %d must be a mapping" % update_number)

        path = update.get("path", _MISSING)
        if not isinstance(path, list) or not path:
            raise ConfigEditError(
                "update %d must contain a non-empty path list" % update_number
            )

        for segment in path:
            if isinstance(segment, str):
                if not segment:
                    raise ConfigEditError(
                        "update %d contains an empty path segment" % update_number
                    )
                continue

            if config_format == "yaml" and isinstance(segment, dict):
                _validate_yaml_selector(segment, update_number)
                continue

            raise ConfigEditError(
                "update %d contains an unsupported path segment: %r"
                % (update_number, segment)
            )

        value = update.get("value", _MISSING)
        if value is _MISSING:
            raise ConfigEditError("update %d must contain value" % update_number)
        _validate_scalar(value, update_number)

        path_tuple = tuple(_freeze_path_segment(segment) for segment in path)
        if path_tuple in seen_paths:
            raise ConfigEditError(
                "update %d repeats an earlier path: %s"
                % (update_number, _format_path(path))
            )
        seen_paths.add(path_tuple)
        normalized.append((tuple(path), value, _format_path(path)))

    return normalized


def _freeze_path_segment(segment: Any) -> Any:
    if isinstance(segment, dict):
        return tuple(
            (key, _freeze_path_segment(value))
            for key, value in sorted(segment.items(), key=lambda item: item[0])
        )
    if isinstance(segment, list):
        return tuple(_freeze_path_segment(value) for value in segment)
    return segment


def _validate_yaml_selector(segment: Dict[str, Any], update_number: int) -> None:
    if set(segment) == {"index"}:
        index = segment["index"]
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ConfigEditError(
                "update %d has an invalid YAML list index" % update_number
            )
        return

    if set(segment) == {"select"}:
        selector = segment["select"]
        if not isinstance(selector, dict) or not selector:
            raise ConfigEditError(
                "update %d must use a non-empty YAML select mapping"
                % update_number
            )
        for key, value in selector.items():
            if not isinstance(key, str) or not key:
                raise ConfigEditError(
                    "update %d has an invalid YAML selector key" % update_number
                )
            if not isinstance(value, str):
                raise ConfigEditError(
                    "update %d YAML selector values must be strings" % update_number
                )
        return

    raise ConfigEditError(
        "update %d must use either {index: N} or {select: {key: value}}"
        % update_number
    )


def _validate_scalar(value: Any, update_number: int) -> None:
    if value is None or isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ConfigEditError(
                "update %d cannot use a non-finite floating-point value"
                % update_number
            )
        return
    raise ConfigEditError(
        "update %d value must be a scalar string, boolean, integer, float, or null"
        % update_number
    )


def _format_path(path: Iterable[Any]) -> str:
    parts = []
    for segment in path:
        if isinstance(segment, str):
            parts.append(segment)
        elif isinstance(segment, dict) and set(segment) == {"index"}:
            parts.append("[%s]" % segment["index"])
        elif isinstance(segment, dict) and set(segment) == {"select"}:
            selector = ", ".join(
                "%s=%s" % (key, value)
                for key, value in sorted(segment["select"].items())
            )
            parts.append("[%s]" % selector)
    return ".".join(parts)


def _serialize_scalar(value: Any, config_format: str) -> str:
    if isinstance(value, str):
        # JSON double-quoted strings are valid TOML basic strings and YAML
        # double-quoted scalars. This also safely handles password characters.
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        if config_format == "toml":
            raise ConfigEditError("TOML does not support null values")
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    raise ConfigEditError("unsupported scalar value")


# YAML handling -----------------------------------------------------------


def _find_yaml_replacements(
    content: str, updates: Sequence[Tuple[Tuple[Any, ...], Any, str]]
) -> List[_Replacement]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - depends on the controller
        raise ConfigEditError(
            "PyYAML is required on the Ansible controller for YAML updates"
        ) from exc

    try:
        documents = [
            document
            for document in yaml.compose_all(content, Loader=yaml.BaseLoader)
            if document is not None
        ]
    except yaml.YAMLError as exc:
        raise ConfigEditError("the YAML file cannot be parsed: %s" % exc) from exc

    if len(documents) != 1:
        raise ConfigEditError("the YAML file must contain exactly one document")

    replacements = []
    root = documents[0]
    for path, value, display_path in updates:
        target = _walk_yaml_path(root, path, display_path)
        if target.id != "scalar":
            raise ConfigEditError(
                "YAML path %s does not point to a scalar value" % display_path
            )
        if target.style in {"|", ">"} or (
            target.start_mark.line != target.end_mark.line
        ):
            raise ConfigEditError(
                "YAML path %s points to a multi-line value, which is not supported"
                % display_path
            )

        replacements.append(
            _Replacement(
                start=target.start_mark.index,
                end=target.end_mark.index,
                value=_serialize_scalar(value, "yaml"),
                path=display_path,
            )
        )

    return replacements


def _walk_yaml_path(root: Any, path: Sequence[Any], display_path: str) -> Any:
    current = root
    for segment in path:
        if isinstance(segment, str):
            current = _yaml_mapping_value(current, segment, display_path)
        elif set(segment) == {"index"}:
            if current.id != "sequence":
                raise ConfigEditError(
                    "YAML path %s uses index on a non-list value" % display_path
                )
            index = segment["index"]
            if index >= len(current.value):
                raise ConfigEditError(
                    "YAML path %s refers to missing list index %d"
                    % (display_path, index)
                )
            current = current.value[index]
        else:
            if current.id != "sequence":
                raise ConfigEditError(
                    "YAML path %s uses select on a non-list value" % display_path
                )
            selector = segment["select"]
            matches = [
                item
                for item in current.value
                if item.id == "mapping" and _yaml_item_matches(item, selector)
            ]
            if len(matches) != 1:
                raise ConfigEditError(
                    "YAML selector in path %s matched %d list items; exactly one is required"
                    % (display_path, len(matches))
                )
            current = matches[0]
    return current


def _yaml_mapping_value(node: Any, key: str, display_path: str) -> Any:
    if node.id != "mapping":
        raise ConfigEditError(
            "YAML path %s expects a mapping before key %s" % (display_path, key)
        )
    matches = []
    for key_node, value_node in node.value:
        if key_node.id == "scalar" and key_node.value == key:
            matches.append(value_node)
    if len(matches) != 1:
        raise ConfigEditError(
            "YAML key %s in path %s matched %d entries; exactly one is required"
            % (key, display_path, len(matches))
        )
    return matches[0]


def _yaml_item_matches(node: Any, selector: Dict[str, str]) -> bool:
    for key, expected in selector.items():
        try:
            value_node = _yaml_mapping_value(node, key, key)
        except ConfigEditError:
            return False
        if value_node.id != "scalar" or value_node.value != expected:
            return False
    return True


# TOML handling ----------------------------------------------------------


def _find_toml_replacements(
    content: str, updates: Sequence[Tuple[Tuple[Any, ...], Any, str]]
) -> List[_Replacement]:
    matches: Dict[int, List[_Replacement]] = {
        index: [] for index in range(len(updates))
    }
    wanted = {path: index for index, (path, _value, _display) in enumerate(updates)}
    current_table: Tuple[str, ...] = ()
    multiline_delimiter = None
    offset = 0

    for line in content.splitlines(keepends=True):
        line_body = line.rstrip("\r\n")

        if multiline_delimiter is not None:
            if _find_toml_multiline_delimiter(
                line_body, multiline_delimiter
            ) is not None:
                multiline_delimiter = None
            offset += len(line)
            continue

        header = _parse_toml_header(line_body)
        if header is not None:
            current_table, _is_array = header
            offset += len(line)
            continue

        assignment = _parse_toml_assignment(line_body)
        if assignment is not None:
            key_path, value_start, value_end, value_delimiter = assignment
            full_path = current_table + key_path
            update_index = wanted.get(full_path)
            if update_index is not None:
                if value_delimiter is not None:
                    raise ConfigEditError(
                        "multi-line TOML values cannot be replaced: %s"
                        % _format_path(key_path)
                    )
                _path, value, display_path = updates[update_index]
                matches[update_index].append(
                    _Replacement(
                        start=offset + value_start,
                        end=offset + value_end,
                        value=_serialize_scalar(value, "toml"),
                        path=display_path,
                    )
                )
            if value_delimiter is not None and _find_toml_multiline_delimiter(
                line_body[value_start + 3 :], value_delimiter
            ) is None:
                multiline_delimiter = value_delimiter
        offset += len(line)

    replacements = []
    for index, (_path, _value, display_path) in enumerate(updates):
        if len(matches[index]) != 1:
            raise ConfigEditError(
                "TOML path %s matched %d assignments; exactly one is required"
                % (display_path, len(matches[index]))
            )
        replacements.extend(matches[index])
    return replacements


def _parse_toml_header(line: str) -> Any:
    uncommented = _strip_toml_comment(line).strip()
    if not uncommented.startswith("["):
        return None

    if uncommented.startswith("[["):
        if not uncommented.endswith("]]"):
            raise ConfigEditError("invalid TOML array table header")
        return _parse_toml_key_path(uncommented[2:-2]), True

    if not uncommented.endswith("]") or uncommented.endswith("]]"):
        raise ConfigEditError("invalid TOML table header")
    return _parse_toml_key_path(uncommented[1:-1]), False


def _parse_toml_assignment(line: str) -> Any:
    uncommented = _strip_toml_comment(line)
    equal_index = _find_unquoted_character(uncommented, "=")
    if equal_index < 0:
        return None

    key_path = _parse_toml_key_path(uncommented[:equal_index])
    value_area = uncommented[equal_index + 1 :]
    leading = len(value_area) - len(value_area.lstrip())
    trailing = len(value_area.rstrip())
    value_start = equal_index + 1 + leading
    value_end = equal_index + 1 + trailing
    if value_start >= value_end:
        return None
    value_text = value_area[leading:]
    value_delimiter = (
        value_text[:3] if value_text.startswith(("\"\"\"", "'''")) else None
    )
    return key_path, value_start, value_end, value_delimiter


def _find_toml_multiline_delimiter(text: str, delimiter: str) -> Any:
    index = 0
    while index < len(text):
        if delimiter == '\"\"\"' and text[index] == "\\":
            index += 2
            continue
        if text.startswith(delimiter, index):
            return index
        index += 1
    return None


def _parse_toml_key_path(text: str) -> Tuple[str, ...]:
    path = []
    index = 0
    length = len(text)
    while index < length:
        while index < length and text[index].isspace():
            index += 1
        if index >= length:
            break

        if text[index] in {"\"", "'"}:
            key, index = _parse_toml_quoted_key(text, index)
        else:
            start = index
            while index < length and text[index] not in ". \t\r\n":
                index += 1
            key = text[start:index]
            if not _TOML_BARE_KEY.fullmatch(key):
                raise ConfigEditError("invalid TOML bare key: %s" % key)

        path.append(key)
        while index < length and text[index].isspace():
            index += 1
        if index >= length:
            break
        if text[index] != ".":
            raise ConfigEditError("invalid TOML dotted key: %s" % text)
        index += 1

    if not path:
        raise ConfigEditError("empty TOML key path")
    return tuple(path)


def _parse_toml_quoted_key(text: str, index: int) -> Tuple[str, int]:
    quote = text[index]
    index += 1
    value = []
    while index < len(text):
        character = text[index]
        if character == quote:
            if quote == '"':
                return _decode_toml_basic_string("".join(value)), index + 1
            return "".join(value), index + 1
        if quote == '"' and character == "\\":
            if index + 1 >= len(text):
                break
            value.extend((character, text[index + 1]))
            index += 2
            continue
        value.append(character)
        index += 1
    raise ConfigEditError("unterminated TOML quoted key")


def _decode_toml_basic_string(value: str) -> str:
    decoded = []
    index = 0
    escapes = {
        "b": "\b",
        "t": "\t",
        "n": "\n",
        "f": "\f",
        "r": "\r",
        '"': '"',
        "\\": "\\",
    }
    while index < len(value):
        if value[index] != "\\":
            decoded.append(value[index])
            index += 1
            continue
        index += 1
        if index >= len(value):
            raise ConfigEditError("invalid TOML key escape")
        escape = value[index]
        if escape in escapes:
            decoded.append(escapes[escape])
            index += 1
        elif escape in {"u", "U"}:
            size = 4 if escape == "u" else 8
            codepoint = value[index + 1 : index + 1 + size]
            if len(codepoint) != size:
                raise ConfigEditError("invalid TOML unicode key escape")
            try:
                decoded.append(chr(int(codepoint, 16)))
            except ValueError as exc:
                raise ConfigEditError("invalid TOML unicode key escape") from exc
            index += 1 + size
        else:
            raise ConfigEditError("invalid TOML key escape: \\%s" % escape)
    return "".join(decoded)


def _strip_toml_comment(line: str) -> str:
    quote = None
    index = 0
    while index < len(line):
        character = line[index]
        if quote is None:
            if character in {'"', "'"}:
                quote = character
            elif character == "#":
                return line[:index]
            index += 1
            continue

        if character == quote:
            quote = None
            index += 1
            continue
        if quote == '"' and character == "\\":
            index += 2
            continue
        index += 1
    return line


def _find_unquoted_character(text: str, expected: str) -> int:
    quote = None
    index = 0
    while index < len(text):
        character = text[index]
        if quote is None:
            if character in {'"', "'"}:
                quote = character
            elif character == expected:
                return index
            index += 1
            continue
        if character == quote:
            quote = None
            index += 1
            continue
        if quote == '"' and character == "\\":
            index += 2
            continue
        index += 1
    return -1


def _ensure_non_overlapping(replacements: Sequence[_Replacement]) -> None:
    ordered = sorted(replacements, key=lambda item: (item.start, item.end))
    for previous, current in zip(ordered, ordered[1:]):
        if current.start < previous.end:
            raise ConfigEditError(
                "requested paths overlap: %s and %s"
                % (previous.path, current.path)
            )
