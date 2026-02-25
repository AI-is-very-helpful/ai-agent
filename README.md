# Doc Agent — 레포 하나로 프로젝트 전체 문서화

Git 레포 URL을 주면 Azure OpenAI로 소스코드를 분석해 **5가지 문서**를 자동 생성합니다.

| 문서 | 출력 | 설명 |
|------|------|------|
| **ERD** | `database.dbml` + `erd_summary.md` | JPA Entity → DBML (dbdiagram.io 호환) |
| **API 스펙** | `api_spec.md` | Controller 엔드포인트 · 파라미터 · 요청/응답 |
| **아키텍처** | `architecture.md` | 레이어/모듈/외부 시스템 + Mermaid 다이어그램 |
| **DDL** | `schema.sql` | JPA → CREATE TABLE SQL |
| **기술 스택** | `tech_stack.md` | 언어 · 프레임워크 · 의존성 정리 |

---

## 전체 서비스 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│  Teams 사용자                                                    │
│  "이 레포 분석해줘: https://github.com/org/repo.git"              │
└───────────────────────────┬─────────────────────────────────────┘
                            │ ① 사용자 메시지 (텍스트)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Copilot Studio (AI Agent)                                       │
│                                                                   │
│  - 사용자 메시지에서 GitHub URL 추출                               │
│  - HTTP Action으로 Azure Function 호출                            │
│                                                                   │
│  POST https://docs-ai-agent.azurewebsites.net/api/run            │
│  Body: { "repo_url": "<URL>", "mode": "all" }                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │ ② HTTP POST (JSON 요청)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Azure Function App (이 프로젝트)                                 │
│                                                                   │
│  function_app.py  POST /api/run                                  │
│    1. prepare_repo() — Git clone                                 │
│    2. run_erd / run_api / run_arch / run_ddl / run_stack 실행     │
│    3. 생성된 파일 내용을 JSON artifacts 배열에 담아 응답              │
│                                                                   │
│  응답: { "status": "ok", "artifacts": [...], ... }               │
└───────────────────────────┬─────────────────────────────────────┘
                            │ ③ HTTP 200 (JSON 응답)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Copilot Studio                                                   │
│                                                                   │
│  - JSON 응답에서 summary, artifacts[].content 추출                │
│  - Adaptive Card 또는 텍스트 메시지로 포맷                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │ ④ 포맷된 메시지 (Adaptive Card / 텍스트)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Teams 사용자                                                    │
│                                                                   │
│  "분석 완료! 📄"                                                  │
│  - ERD: 5개 테이블, 1개 관계 ...                                  │
│  - API: 15개 엔드포인트 ...                                       │
│  - 아키텍처: Layered + Redis + MySQL ...                          │
│  - DDL: CREATE TABLE ...                                         │
│  - 기술 스택: Java 17 + Spring Boot 3.2 ...                       │
└─────────────────────────────────────────────────────────────────┘
```

### 데이터 형식 정리

| 구간 | 보내는 쪽 | 받는 쪽 | 형식 |
|------|-----------|---------|------|
| ① Teams → Copilot Studio | Teams 사용자 | Copilot Studio | **텍스트** (자연어) |
| ② Copilot Studio → Azure Function | Copilot Studio | function_app.py | **JSON** (HTTP POST) |
| ③ Azure Function → Copilot Studio | function_app.py | Copilot Studio | **JSON** (HTTP 200 응답) |
| ④ Copilot Studio → Teams | Copilot Studio | Teams 사용자 | **Adaptive Card / 텍스트** |

> Teams 사용자는 JSON을 직접 보지 않습니다. Copilot Studio가 JSON을 받아서 사람이 읽을 수 있는 메시지로 변환한 뒤 Teams에 보냅니다.

---

## Azure Function API 상세

### 요청 (Copilot Studio → Azure Function)

```
POST https://docs-ai-agent.azurewebsites.net/api/run
Content-Type: application/json
```

```json
{
  "repo_url": "https://github.com/AI-is-very-helpful/hae_shopping_mall.git",
  "mode": "all"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `repo_url` | string | ✅ | GitHub 레포 URL |
| `mode` | string | | `all` · `erd` · `api` · `arch` · `ddl` · `stack` (기본 `all`) |

### 응답 (Azure Function → Copilot Studio)

```json
{
  "status": "ok",
  "repo_url": "https://github.com/org/repo.git",
  "mode": "all",
  "summary": "# ERD Summary\n- Tables: 5\n...(앞 2000자)",
  "agents": {
    "erd":   { "status": "ok" },
    "api":   { "status": "ok" },
    "arch":  { "status": "ok" },
    "ddl":   { "status": "ok" },
    "stack": { "status": "ok" }
  },
  "artifacts": [
    {
      "name": "database.dbml",
      "agent": "erd",
      "content_type": "text/plain",
      "content": "Table orders {\n  id bigint [pk]\n  ...\n}"
    },
    {
      "name": "erd_summary.md",
      "agent": "erd",
      "content_type": "text/markdown",
      "content": "# ERD Summary\n- Tables: 5\n..."
    },
    {
      "name": "api_spec.md",
      "agent": "api",
      "content_type": "text/markdown",
      "content": "# API Specification\n## OrderController\n..."
    },
    {
      "name": "architecture.md",
      "agent": "arch",
      "content_type": "text/markdown",
      "content": "# Architecture\n## Style: Layered\n..."
    },
    {
      "name": "schema.sql",
      "agent": "ddl",
      "content_type": "text/plain",
      "content": "CREATE TABLE orders (\n  id BIGINT PRIMARY KEY\n);"
    },
    {
      "name": "tech_stack.md",
      "agent": "stack",
      "content_type": "text/markdown",
      "content": "# Tech Stack\n## Language: Java 17\n..."
    }
  ]
}
```

| 응답 필드 | 설명 |
|-----------|------|
| `status` | `"ok"` = 전체 성공, `"partial"` = 일부 에이전트 실패 |
| `summary` | 첫 번째 artifact 내용 앞 2000자 (Copilot Studio가 빠르게 표시할 수 있도록) |
| `agents` | 에이전트별 성공/실패 상태 |
| `artifacts` | 생성된 문서 배열 — `content`에 파일 전체 내용이 문자열로 포함 |

### 에러 응답

```json
{
  "error": {
    "code": "MISSING_REPO_URL",
    "message": "repo_url은 필수입니다."
  }
}
```

---

## Copilot Studio에서 Teams로 전달하는 방식

Copilot Studio 토픽에서 JSON 응답을 받은 뒤:

1. `summary` → 간단한 텍스트 메시지로 바로 출력
2. `artifacts[].content` → 각 문서별로 Adaptive Card 또는 텍스트 블록으로 나눠 출력
3. `agents` → 실패한 에이전트가 있으면 경고 메시지 추가

```
[Copilot Studio 토픽 흐름 예시]

트리거:  "레포 분석해줘"
    ↓
질문:    "GitHub 레포 URL을 입력하세요" → topic.repoUrl
    ↓
Action:  POST /api/run  { "repo_url": topic.repoUrl, "mode": "all" }
    ↓
응답 저장: topic.result
    ↓
메시지 출력:
    "분석이 완료됐습니다!

     📌 요약
     {topic.result.summary}

     📄 ERD
     {topic.result.artifacts[0].content}

     📄 API 스펙
     {topic.result.artifacts[2].content}
     ..."
```

연동 상세: [docs/copilot-studio-integration.md](docs/copilot-studio-integration.md)

---

## Quick Start

### 로컬 실행 (pip 설치 없이)

```bash
git clone <this-repo>
cd ai-agent
cp .env.example .env
# .env에 AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT 입력

python scripts/run_agent.py https://github.com/your-org/your-project.git
```

결과는 `out/` 디렉터리에 파일로 생성됩니다.

### pip 설치 후 CLI

```bash
pip install -e .
ai-agent https://github.com/your-org/your-project.git
```

### Azure Function 로컬 테스트

```bash
func start
# 다른 터미널
curl -X POST http://localhost:7071/api/run \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/org/repo.git", "mode": "all"}'
```

---

## 사용법 (로컬 CLI)

```bash
# 전체 문서 생성
python scripts/run_agent.py https://github.com/org/repo.git

# 문서 종류 선택
python scripts/run_agent.py --erd --api ./my-project
python scripts/run_agent.py -e -a -d https://github.com/org/repo.git
```

| 플래그 | 단축 | 문서 |
|--------|------|------|
| `--erd` | `-e` | ERD |
| `--api` | `-a` | API 스펙 |
| `--arch` | | 아키텍처 |
| `--ddl` | `-d` | DDL |
| `--stack` | `-s` | 기술 스택 |

---

## 로컬 CLI vs Azure Function

| | scripts/run_agent.py | Azure Function (POST /api/run) |
|--|----------------------|--------------------------------|
| 용도 | 로컬 개발·테스트 | Copilot Studio → Teams 연동 |
| 호출자 | 개발자 (터미널) | Copilot Studio (HTTP) |
| 결과 형식 | `out/` 폴더에 **파일** | HTTP 응답 **JSON** |
| Azure 필요 | ❌ | ✅ |

---

## 프로젝트 구조

```
.
├── function_app.py       # Azure Function (POST /api/run → JSON 응답)
├── host.json             # Function App 설정
├── requirements.txt
├── pyproject.toml
├── scripts/
│   └── run_agent.py      # 로컬 CLI (out/ 폴더에 파일 생성)
├── docs/
│   └── copilot-studio-integration.md
└── src/
    ├── erd_agent/        # ERD + 공용 (config, repo, cli)
    ├── api_agent/
    ├── arch_agent/
    ├── ddl_agent/
    └── stack_agent/
```

---

## 환경 변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `AZURE_OPENAI_ENDPOINT` | ✅ | Azure OpenAI 엔드포인트 |
| `AZURE_OPENAI_API_KEY` | ✅ | API 키 |
| `AZURE_OPENAI_DEPLOYMENT` | ✅ | 배포 이름 (예: gpt-4.1) |
| `OPENAI_API_VERSION` | | API 버전 (기본: 2024-06-01) |
| `GITHUB_TOKEN` | | private repo용 |
| `DOC_OUTPUT_DIR` | | 로컬 CLI 출력 디렉터리 (기본: ./out) |
| `CACHE_DIR` | | Git clone 캐시 (기본: ./.cache) |

Azure Function 배포 시: Portal → Function App → 구성 → 애플리케이션 설정에 등록.

---

## 배포 (GitHub Actions)

- 워크플로: [.github/workflows/main_docs-ai-agent.yml](.github/workflows/main_docs-ai-agent.yml)
- `main` push 시 빌드 → Azure Function App 배포
- GitHub Secrets 필요: `AZUREAPPSERVICE_CLIENTID_*`, `AZUREAPPSERVICE_TENANTID_*`, `AZUREAPPSERVICE_SUBSCRIPTIONID_*`

---

## 요구 사항

- Python 3.12+
- Azure OpenAI 리소스 (GPT-4 권장)
- Azure Functions Core Tools (로컬 Function 실행 시)
