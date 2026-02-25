# Copilot Studio 연동 가이드

Teams → Copilot Studio → Azure Function(이 프로젝트) → 응답 반환 흐름 전체를 설명합니다.

---

## 전체 흐름

```
Teams 사용자
    │  "이 레포 분석해줘 (GitHub URL)"
    ▼
Copilot Studio (AI Agent)
    │  HTTP POST /api/run
    │  { "repo_url": "https://...", "mode": "all" }
    ▼
Azure Function App  ← 이 프로젝트 (docs-ai-agent)
    │  ERD / API / 아키텍처 / DDL / 기술스택 문서 생성
    │  JSON 응답 반환
    ▼
Copilot Studio
    │  artifacts[*].content 추출
    ▼
Teams 사용자에게 결과 출력
```

---

## 1. Azure Function 엔드포인트

배포 후 URL 형태:

```
POST https://docs-ai-agent.azurewebsites.net/api/run
Content-Type: application/json
```

### 요청 Body

```json
{
  "repo_url": "https://github.com/org/repo.git",
  "mode": "all"
}
```

### `mode` 옵션

| 값 | 생성 문서 |
|----|-----------|
| `all` | ERD + API 스펙 + 아키텍처 + DDL + 기술스택 전체 (기본값) |
| `erd` | ERD (database.dbml + erd_summary.md) |
| `api` | API 스펙 (api_spec.md) |
| `arch` | 아키텍처 다이어그램 (architecture.md) |
| `ddl` | DDL SQL (schema.sql) |
| `stack` | 기술 스택 (tech_stack.md) |

### 응답 Body

```json
{
  "status": "ok",
  "repo_url": "https://github.com/org/repo.git",
  "mode": "all",
  "summary": "# ERD Summary\n- Tables: 5\n...",
  "artifacts": [
    {
      "name": "database.dbml",
      "path": "erd/database.dbml",
      "content_type": "text/plain",
      "content": "Table orders { ... }"
    },
    {
      "name": "erd_summary.md",
      "path": "erd/erd_summary.md",
      "content_type": "text/markdown",
      "content": "# ERD Summary\n..."
    },
    {
      "name": "api_spec.md",
      "path": "api/api_spec.md",
      "content_type": "text/markdown",
      "content": "# API Specification\n..."
    },
    {
      "name": "architecture.md",
      "path": "arch/architecture.md",
      "content_type": "text/markdown",
      "content": "# Architecture\n..."
    },
    {
      "name": "schema.sql",
      "path": "ddl/schema.sql",
      "content_type": "text/plain",
      "content": "CREATE TABLE orders ( ... );"
    },
    {
      "name": "tech_stack.md",
      "path": "stack/tech_stack.md",
      "content_type": "text/markdown",
      "content": "# Tech Stack\n..."
    }
  ],
  "warnings": []
}
```

> `status`가 `"partial"`이면 일부 에이전트 실패. `warnings[].failed_agents` 로 확인 가능.

---

## 2. Copilot Studio Action 설정

### 경로

```
Copilot Studio
  → 내 코파일럿 선택
  → [작업(Actions)] 탭
  → [+ 추가] → [새 작업] → [HTTP 요청]
```

### 설정값

| 항목 | 값 |
|------|----|
| 이름 | 레포 분석 |
| URL | `https://docs-ai-agent.azurewebsites.net/api/run` |
| 메서드 | `POST` |
| 헤더 | `Content-Type: application/json` |

### 요청 Body (Copilot Studio 변수 포함)

```json
{
  "repo_url": "{topic.repoUrl}",
  "mode": "all"
}
```

### 응답 변수 매핑

| Copilot Studio 변수 | JSON 경로 |
|---------------------|-----------|
| `topic.status` | `$.status` |
| `topic.summary` | `$.summary` |
| `topic.artifacts` | `$.artifacts` |

---

## 3. Copilot Studio 토픽(대화 흐름) 예시

```
[트리거]
  사용자: "레포 분석해줘" / "이 프로젝트 분석해줘"

[질문 노드]
  봇: "분석할 GitHub 레포 URL을 입력해 주세요."
  사용자 입력 → topic.repoUrl 저장

[Action 호출]
  HTTP POST https://docs-ai-agent.azurewebsites.net/api/run
  Body: { "repo_url": topic.repoUrl, "mode": "all" }
  결과 → topic.result 저장

[조건 분기]
  topic.result.status == "ok"  → 성공 메시지 노드
  topic.result.status == "partial" → 경고 포함 메시지 노드
  그 외 → 오류 메시지 노드

[성공 메시지]
  분석이 완료됐습니다! 📄

  **요약**
  {topic.result.summary}

  상세 문서는 아래에서 확인하세요.
  - ERD: {topic.result.artifacts[0].content}
  - API 스펙: {topic.result.artifacts[2].content}
  - 아키텍처: {topic.result.artifacts[3].content}
  - DDL: {topic.result.artifacts[4].content}
  - 기술 스택: {topic.result.artifacts[5].content}

[오류 메시지]
  죄송합니다. 분석 중 오류가 발생했습니다.
  잠시 후 다시 시도하거나 URL을 확인해 주세요.
```

---

## 4. curl 테스트 예시

### 로컬 테스트 (Azure Functions Core Tools)

```bash
# 로컬 Function 서버 실행
func start

# 다른 터미널에서 요청
curl -X POST http://localhost:7071/api/run \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/AI-is-very-helpful/hae_shopping_mall.git",
    "mode": "all"
  }'
```

### 특정 모드만 요청

```bash
# ERD만
curl -X POST http://localhost:7071/api/run \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/org/repo.git", "mode": "erd"}'

# API 스펙만
curl -X POST http://localhost:7071/api/run \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/org/repo.git", "mode": "api"}'
```

### 배포 후 운영 테스트

```bash
curl -X POST https://docs-ai-agent.azurewebsites.net/api/run \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/AI-is-very-helpful/hae_shopping_mall.git",
    "mode": "all"
  }'
```

### Python으로 테스트

```python
import requests, json

resp = requests.post(
    "https://docs-ai-agent.azurewebsites.net/api/run",
    json={
        "repo_url": "https://github.com/AI-is-very-helpful/hae_shopping_mall.git",
        "mode": "all",
    },
    timeout=300,
)

data = resp.json()
print("status:", data["status"])
print("artifacts:", [a["name"] for a in data["artifacts"]])

for artifact in data["artifacts"]:
    print(f"\n=== {artifact['name']} ===")
    print(artifact["content"][:500])
```

---

## 5. 환경 변수 (Azure Function App 설정)

Azure Portal → Function App → 구성(Configuration) → 애플리케이션 설정에 아래 값 등록:

| 키 | 값 | 필수 |
|----|----|------|
| `AZURE_OPENAI_ENDPOINT` | `https://<resource>.cognitiveservices.azure.com` | ✅ |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API 키 | ✅ |
| `AZURE_OPENAI_DEPLOYMENT` | 배포 이름 (예: `gpt-4.1`) | ✅ |
| `OPENAI_API_VERSION` | `2024-05-01-preview` | ✅ |
| `GITHUB_TOKEN` | GitHub PAT (private repo 접근 시) | 선택 |

---

## 6. 배포 구조 요약

```
GitHub push (main 브랜치)
    │
    ▼
GitHub Actions (.github/workflows/main_docs-ai-agent.yml)
    │  pip install --target=.python_packages/lib/site-packages
    │  zip → Azure Functions Action
    ▼
Azure Function App (docs-ai-agent)
    │  POST /api/run
    ▼
응답 JSON → Copilot Studio → Teams
```
