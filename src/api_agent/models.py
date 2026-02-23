"""API 스펙 LLM 응답 Pydantic 모델."""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class ParamModel(BaseModel):
    name: str
    location: str = "query"   # path / query / header / body
    type: str = "string"
    required: bool = False
    description: Optional[str] = None


class EndpointModel(BaseModel):
    method: str                 # GET / POST / PUT / DELETE / PATCH
    path: str                   # /api/users/{id}
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: list[ParamModel] = Field(default_factory=list)
    request_body: Optional[str] = None   # JSON 예시 or 타입 설명
    response_body: Optional[str] = None  # JSON 예시 or 타입 설명
    response_status: int = 200
    tags: list[str] = Field(default_factory=list)


class ControllerModel(BaseModel):
    name: str                   # 클래스명
    base_path: Optional[str] = None  # @RequestMapping("/api/users")
    description: Optional[str] = None
    endpoints: list[EndpointModel] = Field(default_factory=list)


class ExtractedApiSpec(BaseModel):
    controllers: list[ControllerModel] = Field(default_factory=list)
