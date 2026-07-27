"""MEC R4 — Config file segmenter (TOML, YAML, JSON).

Extracts top-level sections or major structural elements as memory candidates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ConfigSegment:
    """One structural element from a config file."""
    key_path: str  # e.g. "project.name" or "[tool.ruff]"
    value_text: str  # JSON-serialized representation
    content: str = ""
    source_path: str = ""
    section_type: str = ""  # "top-level", "table", "key"


def _try_parse_toml(text: str) -> dict[str, Any] | None:
    """Try to parse TOML text."""
    try:
        import tomllib  # Python 3.11+
        return tomllib.loads(text)
    except Exception:
        pass
    try:
        import toml  # third-party
        return toml.loads(text)
    except Exception:
        pass
    try:
        import tomli  # fallback
        return tomli.loads(text)
    except Exception:
        pass
    return None


def _try_parse_yaml(text: str) -> dict[str, Any] | None:
    """Try to parse YAML text."""
    try:
        import yaml  # type: ignore[import-untyped]
        return yaml.safe_load(text)
    except Exception:
        pass
    return None


def segment_toml(text: str, source_path: str = "") -> list[ConfigSegment]:
    """Extract top-level tables and keys from TOML."""
    data = _try_parse_toml(text)
    if data is None:
        return [ConfigSegment(
            key_path=source_path,
            value_text=text,
            content=text,
            source_path=source_path,
            section_type="file",
        )]
    if isinstance(data, dict):
        return _dict_to_segments(data, source_path, "")
    return [ConfigSegment(
        key_path=source_path,
        value_text=str(data)[:2000],
        content=str(data)[:2000],
        source_path=source_path,
        section_type="file",
    )]


def segment_yaml(text: str, source_path: str = "") -> list[ConfigSegment]:
    """Extract top-level keys from YAML."""
    data = _try_parse_yaml(text)
    if data is None:
        return [ConfigSegment(
            key_path=source_path,
            value_text=text,
            content=text,
            source_path=source_path,
            section_type="file",
        )]
    if isinstance(data, dict):
        return _dict_to_segments(data, source_path, "")
    if isinstance(data, list):
        segments: list[ConfigSegment] = []
        for i, item in enumerate(data[:50]):
            summary = json.dumps(item, ensure_ascii=False, default=str)[:500] if isinstance(item, dict) else str(item)[:500]
            segments.append(ConfigSegment(
                key_path=f"[{i}]",
                value_text=summary,
                content=json.dumps(item, ensure_ascii=False, default=str)[:2000] if isinstance(item, dict) else str(item)[:2000],
                source_path=source_path,
                section_type="list_item",
            ))
        return segments
    return [ConfigSegment(
        key_path=source_path,
        value_text=str(data)[:2000],
        content=str(data)[:2000],
        source_path=source_path,
        section_type="file",
    )]


def segment_json(text: str, source_path: str = "") -> list[ConfigSegment]:
    """Extract top-level keys from JSON object, or items from JSON array."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return [ConfigSegment(
            key_path=source_path,
            value_text=text,
            content=text,
            source_path=source_path,
            section_type="file",
        )]
    if isinstance(data, list):
        # JSON array — one segment per item summary
        segments: list[ConfigSegment] = []
        for i, item in enumerate(data[:50]):
            if isinstance(item, dict):
                summary = json.dumps(item, ensure_ascii=False, default=str)[:500]
            else:
                summary = str(item)[:500]
            segments.append(ConfigSegment(
                key_path=f"[{i}]",
                value_text=summary,
                content=json.dumps(item, ensure_ascii=False, default=str)[:2000],
                source_path=source_path,
                section_type="list_item",
            ))
        return segments
    if isinstance(data, dict):
        return _dict_to_segments(data, source_path, "")
    return [ConfigSegment(
        key_path=source_path,
        value_text=str(data)[:2000],
        content=str(data)[:2000],
        source_path=source_path,
        section_type="file",
    )]


def _dict_to_segments(
    data: dict[str, Any],
    source_path: str,
    prefix: str,
) -> list[ConfigSegment]:
    """Flatten a dict into key-level segments."""
    segments: list[ConfigSegment] = []
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            # Emit the section itself
            value_text = json.dumps(value, ensure_ascii=False, default=str)
            segments.append(ConfigSegment(
                key_path=full_key,
                value_text=value_text[:2000],
                content=value_text,
                source_path=source_path,
                section_type="table",
            ))
        elif isinstance(value, list):
            safe_list = [
                v if not isinstance(v, (dict, list)) else str(v)[:200]
                for v in value[:20]
            ]
            segments.append(ConfigSegment(
                key_path=full_key,
                value_text=json.dumps(safe_list, ensure_ascii=False),
                content=json.dumps(value, ensure_ascii=False, default=str)[:2000],
                source_path=source_path,
                section_type="key",
            ))
        else:
            segments.append(ConfigSegment(
                key_path=full_key,
                value_text=str(value),
                content=f"{full_key} = {value!r}",
                source_path=source_path,
                section_type="key",
            ))
    return segments


def segment_config(
    text: str,
    source_path: str,
    file_type: str,
) -> list[ConfigSegment]:
    """Dispatch to the right config segmenter."""
    dispatch = {
        "toml": segment_toml,
        "yaml": segment_yaml,
        "json": segment_json,
    }
    fn = dispatch.get(file_type)
    if fn:
        return fn(text, source_path)
    return []
