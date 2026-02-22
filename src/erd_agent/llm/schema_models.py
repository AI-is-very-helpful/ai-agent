from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal

class EnumModel(BaseModel):
    name: str
    values: List[str] = Field(default_factory=list)
    note: Optional[str] = None

class ColumnModel(BaseModel):
    name: str
    type: str
    pk: bool = False
    nullable: bool = True
    unique: bool = False
    increment: bool = False
    default: Optional[str] = None
    note: Optional[str] = None

class TableModel(BaseModel):
    name: str
    columns: List[ColumnModel] = Field(default_factory=list)
    note: Optional[str] = None

class RefModel(BaseModel):
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    rel: Literal[">", "<", "-", "<>"] = ">"

class ExtractedSchema(BaseModel):
    tables: List[TableModel] = Field(default_factory=list)
    refs: List[RefModel] = Field(default_factory=list)
    enums: List[EnumModel] = Field(default_factory=list)