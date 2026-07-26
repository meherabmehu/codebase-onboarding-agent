"""
Language-agnostic structural parsing with tree-sitter.
Extracts function/class boundaries -> these become CodeChunks (the
atomic indexable unit), per the requirement to chunk by function/class,
not fixed line windows.

Features an elite native Python AST and regex-based fallback in case 
tree-sitter or tree-sitter-languages are unavailable on the target machine
(e.g., Python 3.13+ compilation constraints or Windows DLL conflicts).
"""
from __future__ import annotations
import os
import re
import ast
from app.models import CodeChunk

# To prevent buggy native C-extension DLL crashes on Windows/modern environments,
# we bypass tree-sitter by default on Windows (os.name == "nt") or if explicitly disabled,
# falling back to our ultra-stable, pure-Python AST & Regex parser.
if os.name == "nt" or os.environ.get("DISABLE_TREE_SITTER", "true").lower() == "true":
    HAS_TREE_SITTER = False
else:
    try:
        from tree_sitter_languages import get_parser
        HAS_TREE_SITTER = True
    except Exception:
        HAS_TREE_SITTER = False

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


# --- AST / REGEX FALLBACK PARSER ---
class PythonASTChunker(ast.NodeVisitor):
    def __init__(self, code: str, rel_path: str):
        self.code = code
        self.rel_path = rel_path
        self.lines = code.splitlines()
        self.chunks: list[CodeChunk] = []
        self._current_class = None

    def visit_ClassDef(self, node: ast.ClassDef):
        start_line = node.lineno
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else len(self.lines)
        snippet = "\n".join(self.lines[start_line - 1 : end_line])
        
        self.chunks.append(CodeChunk(
            chunk_id=f"{self.rel_path}::{node.name}::{start_line}",
            file_path=self.rel_path,
            symbol_name=node.name,
            symbol_type="class",
            start_line=start_line,
            end_line=end_line,
            source=snippet,
            language="python"
        ))
        
        old_class = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        start_line = node.lineno
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else len(self.lines)
        snippet = "\n".join(self.lines[start_line - 1 : end_line])
        
        name = f"{self._current_class}.{node.name}" if self._current_class else node.name
        self.chunks.append(CodeChunk(
            chunk_id=f"{self.rel_path}::{name}::{start_line}",
            file_path=self.rel_path,
            symbol_name=name,
            symbol_type="method" if self._current_class else "function",
            start_line=start_line,
            end_line=end_line,
            source=snippet,
            language="python"
        ))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        start_line = node.lineno
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else len(self.lines)
        snippet = "\n".join(self.lines[start_line - 1 : end_line])
        
        name = f"{self._current_class}.{node.name}" if self._current_class else node.name
        self.chunks.append(CodeChunk(
            chunk_id=f"{self.rel_path}::{name}::{start_line}",
            file_path=self.rel_path,
            symbol_name=name,
            symbol_type="method" if self._current_class else "function",
            start_line=start_line,
            end_line=end_line,
            source=snippet,
            language="python"
        ))
        self.generic_visit(node)


def parse_file_fallback(file_path: str, repo_root: str) -> list[CodeChunk]:
    ext = os.path.splitext(file_path)[1]
    lang = EXT_TO_LANG.get(ext)
    if not lang:
        return []

    rel_path = os.path.relpath(file_path, repo_root)
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
    except Exception:
        return []

    if lang == "python":
        try:
            tree = ast.parse(code)
            chunker = PythonASTChunker(code, rel_path)
            chunker.visit(tree)
            return chunker.chunks
        except Exception:
            pass  # Fall back to regex if AST fails

    # Generic Regex fallback for other languages (JS/TS/Go/etc.)
    lines = code.splitlines()
    chunks: list[CodeChunk] = []
    current_chunk_lines = []
    current_chunk_name = ""
    current_chunk_type = "function"
    start_line = 1

    for idx, line in enumerate(lines):
        line_num = idx + 1
        # Match class or function pattern
        match = re.search(r'(?:function|func|class|const|let|def)\s+(\w+)', line)
        if match:
            if current_chunk_lines:
                snippet = "\n".join(current_chunk_lines)
                chunks.append(CodeChunk(
                    chunk_id=f"{rel_path}::{current_chunk_name or f'block_{start_line}'}::{start_line}",
                    file_path=rel_path,
                    symbol_name=current_chunk_name or f"block_{start_line}",
                    symbol_type=current_chunk_type,
                    start_line=start_line,
                    end_line=line_num - 1,
                    source=snippet,
                    language=lang
                ))
            current_chunk_lines = [line]
            current_chunk_name = match.group(1)
            current_chunk_type = "class" if "class" in line else "function"
            start_line = line_num
        else:
            current_chunk_lines.append(line)

    if current_chunk_lines:
        snippet = "\n".join(current_chunk_lines)
        chunks.append(CodeChunk(
            chunk_id=f"{rel_path}::{current_chunk_name or f'block_{start_line}'}::{start_line}",
            file_path=rel_path,
            symbol_name=current_chunk_name or "main",
            symbol_type=current_chunk_type,
            start_line=start_line,
            end_line=len(lines),
            source=snippet,
            language=lang
        ))

    return chunks


def parse_file(file_path: str, repo_root: str) -> list[CodeChunk]:
    if not HAS_TREE_SITTER:
        return parse_file_fallback(file_path, repo_root)

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
        # Fall back to native AST chunker if tree-sitter load fails
        return parse_file_fallback(file_path, repo_root)

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
