from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List
import re

ENTITY_NAME_RE = re.compile(r".*Entity\.java$", re.IGNORECASE)
JPA_HINT_RE = re.compile(r"@\s*(Entity|Table)\b")

@dataclass
class ScanConfig:
    prefer_dirs: tuple[str, ...] = ("models", "model", "entity", "entities", "domain")
    exts: tuple[str, ...] = (".java",)

def file_has_jpa_hint(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return bool(JPA_HINT_RE.search(text))
    except Exception:
        return False

def scan_repo(repo_path: Path, cfg: ScanConfig | None = None) -> List[Path]:
    cfg = cfg or ScanConfig()
    candidates: list[Path] = []

    # 1) prefer_dirs 우선
    for d in cfg.prefer_dirs:
        p = repo_path / d
        if p.exists() and p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix in cfg.exts and (ENTITY_NAME_RE.match(f.name) or file_has_jpa_hint(f)):
                    candidates.append(f)

    # 2) 전체 스캔(보완)
    for f in repo_path.rglob("*.java"):
        if f.is_file() and (ENTITY_NAME_RE.match(f.name) or file_has_jpa_hint(f)):
            candidates.append(f)

    return sorted(set(candidates))