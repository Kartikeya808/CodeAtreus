"""Symbol + import extraction.

Prefers tree-sitter ASTs (via tree-sitter-language-pack) and falls back to
language-aware regex when a grammar is unavailable, so every file yields a
usable symbol table and import list regardless of the runtime environment.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.services.indexing.walk import SourceFile

logger = get_logger("indexing.symbols")

# ── Regex fallbacks, keyed by language ───────────────────────────────────────
_FUNC_PATTERNS = {
    "Python": re.compile(r"^\s*(?:async\s+)?def\s+(\w+)", re.M),
    "JavaScript": re.compile(r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()", re.M),
    "TypeScript": re.compile(r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()", re.M),
    "Go": re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?(\w+)", re.M),
    "Java": re.compile(r"(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)\s*\{", re.M),
}
_CLASS_PATTERNS = {
    "Python": re.compile(r"^\s*class\s+(\w+)", re.M),
    "TypeScript": re.compile(r"\b(?:class|interface|enum)\s+(\w+)", re.M),
    "JavaScript": re.compile(r"\bclass\s+(\w+)", re.M),
    "Java": re.compile(r"\b(?:class|interface|enum)\s+(\w+)", re.M),
    "Go": re.compile(r"\btype\s+(\w+)\s+struct", re.M),
}
_IMPORT_PATTERNS = {
    "Python": re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.M),
    "TypeScript": re.compile(r"""import\s+(?:.+?\s+from\s+)?['"]([^'"]+)['"]""", re.M),
    "JavaScript": re.compile(r"""(?:import\s+(?:.+?\s+from\s+)?['"]([^'"]+)['"]|require\(['"]([^'"]+)['"]\))""", re.M),
    "Go": re.compile(r"""['"]([\w./-]+)['"]""", re.M),
    "Java": re.compile(r"^\s*import\s+([\w.]+)", re.M),
}


@dataclass
class FileSymbols:
    rel_path: str
    language: str | None
    functions: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


def _read_text(sf: SourceFile) -> str:
    try:
        return sf.abs_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _regex_extract(sf: SourceFile, text: str) -> FileSymbols:
    lang = sf.language
    syms = FileSymbols(rel_path=sf.rel_path, language=lang)
    if not lang:
        return syms

    def _collect(pat: re.Pattern[str] | None) -> list[str]:
        if pat is None:
            return []
        out: list[str] = []
        for m in pat.finditer(text):
            name = next((g for g in m.groups() if g), None)
            if name:
                out.append(name)
        return out

    syms.functions = _collect(_FUNC_PATTERNS.get(lang))[:200]
    syms.classes = _collect(_CLASS_PATTERNS.get(lang))[:200]
    syms.imports = _collect(_IMPORT_PATTERNS.get(lang))[:200]
    return syms


def extract_symbols(files: list[SourceFile]) -> list[FileSymbols]:
    """Extract a symbol table for every source file.

    Attempts tree-sitter first; on any failure (missing grammar, parse error)
    silently falls back to regex extraction for that file.
    """
    ts_available = _tree_sitter_available()
    results: list[FileSymbols] = []
    for sf in files:
        if sf.language is None:
            continue
        text = _read_text(sf)
        if not text:
            continue
        syms = None
        if ts_available:
            try:
                syms = _tree_sitter_extract(sf, text)
            except Exception as exc:  # noqa: BLE001 - fall back per file
                logger.debug("tree-sitter failed for %s: %s", sf.rel_path, exc)
        results.append(syms or _regex_extract(sf, text))
    return results


# ── Optional tree-sitter path ─────────────────────────────────────────────────
_TS_LANG_NAMES = {
    "Python": "python", "JavaScript": "javascript", "TypeScript": "typescript",
    "Go": "go", "Java": "java", "Rust": "rust", "C": "c", "C++": "cpp",
    "Ruby": "ruby", "C#": "c_sharp",
}


def _tree_sitter_available() -> bool:
    try:
        import tree_sitter_language_pack  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _tree_sitter_extract(sf: SourceFile, text: str) -> FileSymbols:
    from tree_sitter_language_pack import get_parser

    ts_name = _TS_LANG_NAMES.get(sf.language or "")
    if ts_name is None:
        raise ValueError(f"no grammar for {sf.language}")

    parser = get_parser(ts_name)
    tree = parser.parse(text.encode("utf-8"))
    syms = FileSymbols(rel_path=sf.rel_path, language=sf.language)

    func_types = {"function_definition", "function_declaration", "method_definition",
                  "function_item", "method_declaration"}
    class_types = {"class_definition", "class_declaration", "struct_item",
                   "interface_declaration", "type_declaration", "enum_declaration"}
    import_types = {"import_statement", "import_from_statement", "import_declaration",
                    "import_spec", "use_declaration"}

    def _name_of(node) -> str | None:
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            return name_node.text.decode("utf-8", "ignore")
        return None

    def _visit(node) -> None:
        if node.type in func_types:
            if (n := _name_of(node)):
                syms.functions.append(n)
        elif node.type in class_types:
            if (n := _name_of(node)):
                syms.classes.append(n)
        elif node.type in import_types:
            syms.imports.append(node.text.decode("utf-8", "ignore")[:200])
        for child in node.children:
            _visit(child)

    _visit(tree.root_node)
    # Keep import extraction consistent with the regex path (module targets).
    if not syms.imports:
        syms = _regex_extract(sf, text)
    syms.functions = syms.functions[:200]
    syms.classes = syms.classes[:200]
    return syms
