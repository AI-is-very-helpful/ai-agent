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
    name: str
    columns: Dict[str, Column] = field(default_factory=dict)
    note: Optional[str] = None

@dataclass
class Ref:
    child_table: str
    child_column: str
    parent_table: str
    parent_column: str
    rel: str = ">"

@dataclass
class EnumType:
    name: str
    values: List[str] = field(default_factory=list)
    note: Optional[str] = None

@dataclass
class Schema:
    tables: Dict[str, Table] = field(default_factory=dict)
    refs: List[Ref] = field(default_factory=list)
    enums: Dict[str, EnumType] = field(default_factory=dict)  # ✅ 추가

    def ensure_table(self, name: str) -> Table:
        if name not in self.tables:
            self.tables[name] = Table(name=name)
        return self.tables[name]

    def ensure_enum(self, name: str) -> EnumType:
        if name not in self.enums:
            self.enums[name] = EnumType(name=name)
        return self.enums[name]