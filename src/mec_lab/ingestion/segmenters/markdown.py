"""MEC R4 — Markdown segmenter.

Splits Markdown files into logical segments by headings.
Each segment preserves hierarchy and source position.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class MarkdownSegment:
    """One logical segment extracted from a Markdown file."""
    heading_chain: list[str] = field(default_factory=list)  # e.g. ["## Section", "### Sub"]
    heading_level: int = 0  # depth of the deepest heading
    content: str = ""
    line_start: int = 0
    line_end: int = 0
    document_title: str = ""
    source_path: str = ""


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def segment_markdown(
    text: str,
    source_path: str = "",
    document_title: str = "",
) -> list[MarkdownSegment]:
    """Split a Markdown document into heading-delimited segments.

    A segment is everything from one heading to the next heading of equal
    or higher level. Text before the first heading becomes a preamble
    segment with the document title as its heading.
    """
    if not text.strip():
        return []

    lines = text.split("\n")
    heading_positions: list[tuple[int, int, str]] = []  # (line_idx, level, title)

    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            heading_positions.append((i, level, title))

    if not heading_positions:
        # Document has no headings — single segment
        seg = MarkdownSegment(
            heading_chain=[document_title or source_path],
            heading_level=0,
            content=text.strip(),
            line_start=1,
            line_end=len(lines),
            document_title=document_title or source_path,
            source_path=source_path,
        )
        return [seg]

    segments: list[MarkdownSegment] = []

    # Preamble: text before the first heading
    first_pos = heading_positions[0][0]
    if first_pos > 0 and any(l.strip() for l in lines[:first_pos]):
        preamble_text = "\n".join(lines[:first_pos]).strip()
        if preamble_text:
            seg = MarkdownSegment(
                heading_chain=[document_title or source_path],
                heading_level=0,
                content=preamble_text,
                line_start=1,
                line_end=first_pos,
                document_title=document_title or source_path,
                source_path=source_path,
            )
            segments.append(seg)

    # Build heading stack and emit segments
    heading_stack: list[tuple[int, str]] = []  # [(level, title), ...]

    for idx, (pos, level, title) in enumerate(heading_positions):
        # Pop headings of equal or higher level
        while heading_stack and heading_stack[-1][0] >= level:
            heading_stack.pop()
        heading_stack.append((level, title))

        # Determine end line
        if idx + 1 < len(heading_positions):
            end_line = heading_positions[idx + 1][0]
        else:
            end_line = len(lines)

        # Collect content lines for this segment
        content_lines = lines[pos:end_line]
        content = "\n".join(content_lines).strip()

        if not content:
            continue

        chain = [t for _, t in heading_stack]
        seg = MarkdownSegment(
            heading_chain=list(chain),
            heading_level=level,
            content=content,
            line_start=pos + 1,
            line_end=end_line,
            document_title=document_title or source_path,
            source_path=source_path,
        )
        segments.append(seg)

    return segments
