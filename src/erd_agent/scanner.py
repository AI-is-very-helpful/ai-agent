from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List
from typing import Set
import re

# 파일명 힌트: *Entity.java
ENTITY_NAME_RE = re.compile(r".*Entity\.java$", re.IGNORECASE)

# 본문 힌트: @Entity 중심
ENTITY_ANN_RE = re.compile(r"@\s*Entity\b")
TABLE_ANN_RE = re.compile(r"@\s*Table\b")  # 보조 신호(테이블명 추출용)

# Enum
ENUM_DEF_RE = re.compile(r"\benum\s+([A-Z]\w*)\b")
ENUM_FIELD_RE = re.compile(r"@Enumerated\s*\(\s*EnumType\.STRING\s*\)\s*@Column[^{;]*\s+private\s+([A-Z]\w*)\s+\w+\s*;", re.DOTALL)

@dataclass
class ScanConfig:
    prefer_dirs: tuple[str, ...] = ("models", "model", "entity", "entities", "domain")
    exts: tuple[str, ...] = (".java",)
    include_table_only: bool = False  # 레거시 대응 옵션(기본 False)

def find_enum_type_names_in_entity_text(text: str) -> Set[str]:
    # @Enumerated(EnumType.STRING) 필드에서 enum 타입 이름만 추출
    return set(ENUM_FIELD_RE.findall(text))

def find_enum_definition_files(repo_path: Path, enum_names: Set[str]) -> list[Path]:
    # enum Role { ... } 정의가 들어있는 파일을 찾아 추가 입력으로 사용
    if not enum_names:
        return []
    hits = []
    for f in repo_path.rglob("*.java"):
        try:
            t = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for name in enum_names:
            if re.search(rf"\benum\s+{re.escape(name)}\b", t):
                hits.append(f)
                break
    return sorted(set(hits))

def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def _has_entity(text: str) -> bool:
    return bool(ENTITY_ANN_RE.search(text))

def _has_table(text: str) -> bool:
    return bool(TABLE_ANN_RE.search(text))

def scan_repo(repo_path: Path, cfg: ScanConfig | None = None) -> List[Path]:
    """
    JPA 엔티티 후보 파일을 찾아 반환한다.
    우선순위:
      1) @Entity가 있는 파일
      2) 파일명이 *Entity.java 인 파일 (보조)
      3) (옵션) @Table만 있는 파일 include_table_only=True일 때만
    """
    cfg = cfg or ScanConfig()
    candidates: set[Path] = set()

    def consider_file(f: Path):
        if not f.is_file() or f.suffix not in cfg.exts:
            return
        text = _read_text(f)

        if _has_entity(text):
            candidates.add(f)
            return

        # 보조: 파일명 패턴
        if ENTITY_NAME_RE.match(f.name):
            candidates.add(f)
            return

        # 매우 예외적인 케이스만: @Table only
        if cfg.include_table_only and _has_table(text):
            candidates.add(f)

    # 1) prefer_dirs 우선 탐색
    for d in cfg.prefer_dirs:
        p = repo_path / d
        if p.exists() and p.is_dir():
            for f in p.rglob("*"):
                consider_file(f)

    # 2) 전체 탐색 (보완)
    for f in repo_path.rglob("*.java"):
        consider_file(f)

    return sorted(candidates)