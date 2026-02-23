"""아키텍처 분석 LLM 응답 Pydantic 모델."""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class LayerModel(BaseModel):
    name: str                   # e.g. "Presentation", "Service", "Repository"
    description: Optional[str] = None
    components: list[str] = Field(default_factory=list)  # 클래스명 등


class DependencyModel(BaseModel):
    source: str                  # 레이어/모듈 이름
    target: str
    description: Optional[str] = None


class ExternalSystemModel(BaseModel):
    name: str                    # e.g. "MySQL", "Redis", "Kafka"
    type: str = "database"       # database / cache / message-broker / external-api
    description: Optional[str] = None


class ExtractedArchitecture(BaseModel):
    project_name: Optional[str] = None
    architecture_style: Optional[str] = None  # e.g. "Layered", "Microservice", "Hexagonal"
    summary: Optional[str] = None
    layers: list[LayerModel] = Field(default_factory=list)
    dependencies: list[DependencyModel] = Field(default_factory=list)
    external_systems: list[ExternalSystemModel] = Field(default_factory=list)
    mermaid_diagram: Optional[str] = None
