"""MEC R4 — Ingestion segmenters.

Each segmenter transforms source text into a list of structured entities
suitable for memory creation.
"""

from mec_lab.ingestion.segmenters.config_files import ConfigSegment, segment_config
from mec_lab.ingestion.segmenters.markdown import MarkdownSegment, segment_markdown
from mec_lab.ingestion.segmenters.python_ast import PythonEntity, segment_python

__all__ = [
    "MarkdownSegment",
    "segment_markdown",
    "PythonEntity",
    "segment_python",
    "ConfigSegment",
    "segment_config",
]
