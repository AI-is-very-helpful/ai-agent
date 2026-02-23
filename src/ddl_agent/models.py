"""DDL 생성 LLM 응답 Pydantic 모델."""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class DDLColumnModel(BaseModel):
    name: str
    type: str           # VARCHAR(255), BIGINT, TIMESTAMP, etc.
    pk: bool = False
    nullable: bool = True
    unique: bool = False
    auto_increment: bool = False
    default: Optional[str] = None
    comment: Optional[str] = None


class DDLConstraintModel(BaseModel):
    name: str
    type: str            # PRIMARY KEY / FOREIGN KEY / UNIQUE / INDEX
    columns: list[str]
    ref_table: Optional[str] = None
    ref_columns: list[str] = Field(default_factory=list)


class DDLTableModel(BaseModel):
    name: str
    schema_name: Optional[str] = None
    columns: list[DDLColumnModel] = Field(default_factory=list)
    constraints: list[DDLConstraintModel] = Field(default_factory=list)
    comment: Optional[str] = None


class ExtractedDDL(BaseModel):
    dialect: str = "mysql"   # mysql / postgresql / h2 / oracle
    tables: list[DDLTableModel] = Field(default_factory=list)
