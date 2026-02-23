"""Controller / REST endpoint 후보 파일 스캐너."""
from __future__ import annotations
import re
from pathlib import Path

CONTROLLER_ANN_RE = re.compile(
    r"@\s*(RestController|Controller|RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\b"
)

CONTROLLER_NAME_RE = re.compile(r".*(Controller|Resource|Api)\.java$", re.IGNORECASE)


def scan_controller_files(repo_path: Path) -> list[Path]:
    """@RestController, @Controller 등이 포함된 Java 파일을 찾는다."""
    candidates: set[Path] = set()

    for f in repo_path.rglob("*.java"):
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if CONTROLLER_ANN_RE.search(text):
            candidates.add(f)
        elif CONTROLLER_NAME_RE.match(f.name):
            candidates.add(f)

    return sorted(candidates)
