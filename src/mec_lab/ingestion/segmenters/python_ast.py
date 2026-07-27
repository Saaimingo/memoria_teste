"""MEC R4 — Python AST segmenter.

Uses Python's ast module to extract module, class, function, and method
definitions as individual memory candidates. Each carries a qualified
name, signature, docstring, and source location.

R4.1: Also extracts decorators, CLI command/option detection from Click
decorators, and stores explicit module_name/class_name/function_name/
method_name/symbol_kind for the symbol index.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PythonEntity:
    """One Python code entity suitable for a memory record."""
    entity_type: str  # "module", "class", "function", "method", "constant", "command", "option"
    qualified_name: str
    signature: str = ""
    docstring: str = ""
    content: str = ""  # the full source block
    line_start: int = 0
    line_end: int = 0
    source_path: str = ""
    imports: list[str] = field(default_factory=list)
    # R4.1: symbol metadata
    module_name: str = ""
    class_name: str = ""
    function_name: str = ""
    method_name: str = ""
    symbol_kind: str = ""
    decorators: list[str] = field(default_factory=list)
    cli_command: str = ""
    cli_option: str = ""

    @property
    def simple_name(self) -> str:
        return self.qualified_name.rsplit(".", 1)[-1]


def _get_docstring(node: ast.AST) -> str:
    """Extract docstring from a function/class/module node."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
        doc = ast.get_docstring(node)
        return doc if doc else ""
    return ""


def _get_imports(tree: ast.Module) -> list[str]:
    """Extract top-level import statements as strings."""
    imports: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = ", ".join(a.name for a in node.names)
            imports.append(f"from {module} import {names}")
    return imports


def _signature_from_func(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Build a readable signature string."""
    args = []
    # Positional args
    for a in node.args.args:
        arg = a.arg
        if a.annotation:
            arg += f": {ast.unparse(a.annotation)}"
        args.append(arg)
    # Defaults (matched from the right)
    defaults = node.args.defaults
    if defaults:
        offset = len(args) - len(defaults)
        for i, d in enumerate(defaults):
            idx = offset + i
            args[idx] += f"={ast.unparse(d)}"
    # *args
    if node.args.vararg:
        a = f"*{node.args.vararg.arg}"
        if node.args.vararg.annotation:
            a += f": {ast.unparse(node.args.vararg.annotation)}"
        args.append(a)
    # **kwargs
    if node.args.kwarg:
        a = f"**{node.args.kwarg.arg}"
        if node.args.kwarg.annotation:
            a += f": {ast.unparse(node.args.kwarg.annotation)}"
        args.append(a)
    returns = ""
    if node.returns:
        returns = f" -> {ast.unparse(node.returns)}"
    return f"def {node.name}({', '.join(args)}){returns}"


def _source_block(source_lines: list[str], node: ast.AST) -> str:
    """Extract the source block for a node, respecting line numbers."""
    start = node.lineno - 1  # Convert to 0-based index
    end = (node.end_lineno or start + 1)  # end_lineno is 1-based inclusive
    return "\n".join(source_lines[start:end])


def _detect_cli_from_decorators(decorators: list[str], func_name: str) -> tuple[str, str]:
    """Return (cli_command_name, cli_option_name) from decorator strings."""
    cli_command_name = ""
    cli_option_name = ""
    for dec in decorators:
        # @<group>.command("name") or @cli.command()
        cmd_m = re.search(r"\.command\s*\(\s*(?:name\s*=\s*)?['\"]([^'\"]+)['\"]", dec)
        if cmd_m:
            cli_command_name = cmd_m.group(1)
        elif re.search(r"\.command\s*\(\s*\)", dec):
            cli_command_name = func_name.replace("_", "-")

        # @click.option("--retrieval-mode", ...) or @click.option("retrieval-mode", ...)
        opt_m = re.search(r"\.option\s*\(\s*['\"](--?[\w\-]+)['\"]", dec)
        if opt_m:
            cli_option_name = opt_m.group(1)
    return cli_command_name, cli_option_name


def segment_python(
    text: str,
    source_path: str = "",
) -> list[PythonEntity]:
    """Parse Python source and extract module, class, function, and method entities."""
    try:
        tree = ast.parse(text, filename=source_path)
    except SyntaxError:
        return []

    lines = text.split("\n")
    entities: list[PythonEntity] = []

    # Module-level entity
    module_name = source_path.replace("/", ".").replace("\\", ".").removesuffix(".py")
    module_doc = _get_docstring(tree)
    imports = _get_imports(tree)

    entities.append(PythonEntity(
        entity_type="module",
        qualified_name=module_name,
        docstring=module_doc,
        content=text.strip(),
        line_start=1,
        line_end=len(lines),
        source_path=source_path,
        imports=imports,
        module_name=module_name,
        symbol_kind="module",
    ))

    # Walk top-level and class-level definitions
    def walk(nodes: list[ast.AST], parent_name: str) -> None:
        for node in nodes:
            if isinstance(node, ast.ClassDef):
                qname = f"{parent_name}.{node.name}" if parent_name else node.name
                doc = _get_docstring(node)
                bases = ", ".join(ast.unparse(b) for b in node.bases) if node.bases else ""
                sig = f"class {node.name}({bases})" if bases else f"class {node.name}"
                decorators = [ast.unparse(d) for d in node.decorator_list]
                entities.append(PythonEntity(
                    entity_type="class",
                    qualified_name=qname,
                    signature=sig,
                    docstring=doc,
                    content=_source_block(lines, node),
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    source_path=source_path,
                    module_name=module_name,
                    class_name=qname,
                    symbol_kind="class",
                    decorators=decorators,
                ))
                walk(node.body, qname)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qname = f"{parent_name}.{node.name}" if parent_name else node.name
                entity_type = "method" if parent_name else "function"
                sig = _signature_from_func(node)
                doc = _get_docstring(node)
                decorators = [ast.unparse(d) for d in node.decorator_list]

                # Detect Click CLI command and option from decorators
                cli_cmd, cli_opt = _detect_cli_from_decorators(decorators, node.name)

                if cli_cmd:
                    entity_type = "command"
                elif cli_opt:
                    entity_type = "option"

                ent_class_name = parent_name if parent_name else ""
                ent_method_name = qname if entity_type == "method" else ""
                ent_func_name = node.name if entity_type in ("function", "command", "option") else ""

                entities.append(PythonEntity(
                    entity_type=entity_type,
                    qualified_name=qname,
                    signature=sig,
                    docstring=doc,
                    content=_source_block(lines, node),
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    source_path=source_path,
                    module_name=module_name,
                    class_name=ent_class_name,
                    function_name=ent_func_name,
                    method_name=ent_method_name,
                    symbol_kind=entity_type,
                    decorators=decorators,
                    cli_command=cli_cmd,
                    cli_option=cli_opt,
                ))

    walk(tree.body, "")

    # Filter: keep only entities with meaningful content
    entities = [e for e in entities if e.content.strip()]

    return entities