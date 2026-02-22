from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, List

@dataclass
class Column:
    name: str
    db_type: str
    pk: bool = False
    nullable: bool = True
    unique: bool = False
    increment: bool = False
    default: Optional[str] = None
    note: Optional[str] = None

@dataclass
class Table:
    name: str                   # DBML에서 schema.table 형태도 가능
    columns: Dict[str, Column] = field(default_factory=dict)
    note: Optional[str] = None

@dataclass
class Ref:
    child_table: str
    child_column: str
    parent_table: str
    parent_column: str
    rel: str = ">"  # DBML 관계 기호(>, <, -, <>)

@dataclass
class Schema:
    tables: Dict[str, Table] = field(default_factory=dict)
    refs: List[Ref] = field(default_factory=list)

    def ensure_table(self, name: str) -> Table:
        if name not in self.tables:
            self.tables[name] = Table(name=name)
        return self.tables[name]