"""기술 스택 LLM 응답 Pydantic 모델."""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class DependencyItem(BaseModel):
    name: str
    version: Optional[str] = None
    scope: Optional[str] = None     # compile / runtime / test / dev
    description: Optional[str] = None


class CategoryModel(BaseModel):
    category: str                   # e.g. "Framework", "Database", "Testing", "Build"
    items: list[DependencyItem] = Field(default_factory=list)


class ExtractedStack(BaseModel):
    language: Optional[str] = None         # Java, Python, Go, ...
    language_version: Optional[str] = None
    framework: Optional[str] = None        # Spring Boot, Django, ...
    framework_version: Optional[str] = None
    build_tool: Optional[str] = None       # Maven, Gradle, npm, ...
    summary: Optional[str] = None
    categories: list[CategoryModel] = Field(default_factory=list)
