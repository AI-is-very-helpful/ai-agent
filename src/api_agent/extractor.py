"""LLM 기반 API 스펙 추출기."""
from __future__ import annotations
import json
from pathlib import Path

from erd_agent.config import settings
from erd_agent.llm.aoai_client import build_aoai_client
from api_agent.models import ExtractedApiSpec

SYSTEM_PROMPT = """You are a senior backend engineer specializing in REST API documentation.
You extract API endpoint specifications from Java Spring Boot controller source code.
Focus on: HTTP method, URL path, path/query/header parameters, request body, response body, status codes.
Return ONLY valid JSON (no markdown, no explanation).
"""

USER_PROMPT_TEMPLATE = """Analyze the following Java controller source files and extract REST API specifications.

Rules:
- Each class annotated with @RestController or @Controller is a controller.
- @RequestMapping on the class level defines the base path.
- @GetMapping, @PostMapping, @PutMapping, @DeleteMapping, @PatchMapping define endpoints.
- @PathVariable => parameter with location "path"
- @RequestParam => parameter with location "query"
- @RequestHeader => parameter with location "header"
- @RequestBody => extract the type/fields as request_body description
- Return type / @ResponseBody / ResponseEntity<T> => extract as response_body description
- @ResponseStatus => response status code
- If Swagger/OpenAPI annotations exist (@Operation, @ApiResponse, @Tag), use their info for summary/description/tags.

Output JSON schema:
{{
  "controllers": [
    {{
      "name": "UserController",
      "base_path": "/api/users",
      "description": "User management endpoints",
      "endpoints": [
        {{
          "method": "GET",
          "path": "/api/users/{{id}}",
          "summary": "Get user by ID",
          "description": "...",
          "parameters": [
            {{"name": "id", "location": "path", "type": "Long", "required": true, "description": "User ID"}}
          ],
          "request_body": null,
          "response_body": "User object with id, name, email fields",
          "response_status": 200,
          "tags": ["User"]
        }}
      ]
    }}
  ]
}}

FILES:
{files_blob}
"""


def _chunk_files(files: list[tuple[Path, str]], max_chars: int = 120_000) -> list[list[tuple[Path, str]]]:
    chunks: list[list[tuple[Path, str]]] = []
    cur: list[tuple[Path, str]] = []
    cur_len = 0
    for p, txt in files:
        if cur and cur_len + len(txt) > max_chars:
            chunks.append(cur)
            cur, cur_len = [], 0
        cur.append((p, txt))
        cur_len += len(txt)
    if cur:
        chunks.append(cur)
    return chunks


def _make_files_blob(chunk: list[tuple[Path, str]]) -> str:
    parts = []
    for p, txt in chunk:
        parts.append(f'<file path="{p.as_posix()}">\n{txt}\n</file>')
    return "\n\n".join(parts)


def _call_llm(files_blob: str) -> ExtractedApiSpec:
    client = build_aoai_client()
    if client is None:
        raise RuntimeError("Azure OpenAI 설정이 없습니다. (.env의 AZURE_OPENAI_* 값을 설정하세요)")

    resp = client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(files_blob=files_blob)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    data = json.loads(resp.choices[0].message.content)
    return ExtractedApiSpec.model_validate(data)


def _merge_specs(chunks: list[ExtractedApiSpec]) -> ExtractedApiSpec:
    all_controllers: dict[str, dict] = {}
    for spec in chunks:
        for ctrl in spec.controllers:
            key = ctrl.name
            if key not in all_controllers:
                all_controllers[key] = ctrl.model_dump()
            else:
                existing_paths = {(e["method"], e["path"]) for e in all_controllers[key]["endpoints"]}
                for ep in ctrl.endpoints:
                    if (ep.method, ep.path) not in existing_paths:
                        all_controllers[key]["endpoints"].append(ep.model_dump())
    return ExtractedApiSpec.model_validate({"controllers": list(all_controllers.values())})


def ai_extract_api(file_texts: list[tuple[Path, str]]) -> ExtractedApiSpec:
    chunks = _chunk_files(file_texts)
    extracted = [_call_llm(_make_files_blob(ch)) for ch in chunks]
    return _merge_specs(extracted)
