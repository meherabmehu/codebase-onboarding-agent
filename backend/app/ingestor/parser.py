"""
Language-agnostic structural parsing with tree-sitter.
Extracts function/class boundaries -> these become CodeChunks (the
atomic indexable unit), per the requirement to chunk by function/class,
not fixed line windows.
"""
from __future__ import annotations
import os
from tree_sitter_languages import get_parser
from app.models import CodeChunk

EXT_TO_LANG = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
}

SYMBOL_NODE_TYPES = {
    "python": {"function_definition": "function", "class_definition": "class"},
    "javascript": {"function_declaration": "function", "class_declaration": "class",
                   "method_definition": "method"},
    "typescript": {"function_declaration": "function", "class_declaration": "class",
                   "method_definition": "method"},
    "tsx": {"function_declaration": "function", "class_declaration": "class",
            "method_definition": "method"},
    "go": {"function_declaration": "function", "method_declaration": "method"},
    "rust": {"function_item": "function", "impl_item": "class"},
    "java": {"method_declaration": "method", "class_declaration": "class"},
}


def _symbol_name(node, source: bytes) -> str:
    for child in node.children:
        if child.type in ("identifier", "type_identifier", "property_identifier"):
            return source[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
    return "<anonymous>"


def parse_file(file_path: str, repo_root: str) -> list[CodeChunk]:
    ext = os.path.splitext(file_path)[1]
    lang = EXT_TO_LANG.get(ext)
    if not lang:
        return []

    try:
        parser = get_parser(lang)
        with open(file_path, "rb") as f:
            source = f.read()
        tree = parser.parse(source)
    except Exception:
        return []

    rel_path = os.path.relpath(file_path, repo_root)
    node_types = SYMBOL_NODE_TYPES.get(lang, {})
    chunks: list[CodeChunk] = []

    def walk(node):
        if node.type in node_types:
            name = _symbol_name(node, source)
            snippet = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
            chunks.append(CodeChunk(
                chunk_id=f"{rel_path}::{name}::{node.start_point[0]}",
                file_path=rel_path,
                symbol_name=name,
                symbol_type=node_types[node.type],
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                source=snippet,
                language=lang,
            ))
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return chunks


def parse_repo(repo_root: str, extensions: set[str] | None = None) -> list[CodeChunk]:
    """Walk the repo tree and parse every recognized source file."""
    extensions = extensions or set(EXT_TO_LANG.keys())
    all_chunks: list[CodeChunk] = []

    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", "venv", ".venv", "dist", "build"}]
        for fname in filenames:
            if os.path.splitext(fname)[1] in extensions:
                full = os.path.join(dirpath, fname)
                all_chunks.extend(parse_file(full, repo_root))

    return all_chunks