# Doc Agent — 레포 하나로 프로젝트 전체 문서화

Git 레포(로컬 경로 또는 URL)를 주면 Azure OpenAI가 소스코드를 분석해서
**5가지 문서**를 자동으로 생성합니다.

| 문서 | 출력 | 설명 |
|------|------|------|
| **ERD** | `database.dbml` + `erd_summary.md` | JPA Entity → DBML (dbdiagram.io 호환) |
| **API 스펙** | `api_spec.md` | Controller 엔드포인트 · 파라미터 · 요청/응답 |
| **아키텍처** | `architecture.md` | 레이어/모듈/외부 시스템 + Mermaid 다이어그램 |
| **DDL** | `schema.sql` | JPA → CREATE TABLE SQL |
| **기술 스택** | `tech_stack.md` | 언어 · 프레임워크 · 의존성 카테고리별 정리 |

---

## 전체 서비스 흐름

```
Teams 사용자
    │  "이 레포 분석해줘 (GitHub URL)"
    ▼
Copilot Studio (AI Agent)
    │  POST /api/run  { "repo_url": "...", "mode": "all" }
    ▼
Azure Function App  ← 이 프로젝트 (docs-ai-agent)
    │  5개 에이전트 실행 후 JSON 반환
    ▼
Copilot Studio → Teams 결과 출력
```

> Copilot Studio 연동 상세는 [`docs/copilot-studio-integration.md`](docs/copilot-studio-integration.md) 참조.

---

## Quick Start

### 로컬 실행 (파일 생성)

```bash
# 1. 클론 & 환경 설정
git clone <this-repo>
cd doc-agent
cp .env.example .env
# .env에 AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT 입력

# 2-A. pip 설치 후 실행
pip install -e .
ai-agent https://github.com/your-org/your-project.git

# 2-B. pip 설치 없이 실행 (권장)
python scripts/run_agent.py https://github.com/your-org/your-project.git
```

`out/` 디렉터리에 5가지 문서가 생성됩니다.

### Azure Function (서버)

```bash
# 로컬 Function 서버 실행
func start

# 다른 터미널에서 호출
curl -X POST http://localhost:7071/api/run \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/your-org/repo.git", "mode": "all"}'
```

---

## 사용법

### scripts/run_agent.py — 로컬 CLI (pip 설치 불필요)

```bash
# 전체 문서 생성 (플래그 없으면 전부)
python scripts/run_agent.py https://github.com/org/repo.git
python scripts/run_agent.py ./my-project

# 원하는 문서만 선택
python scripts/run_agent.py --erd --api https://github.com/org/repo.git
python scripts/run_agent.py -e -a -d ./my-project   # 단축: -e=erd, -a=api, -d=ddl, -s=stack
```

### ai-agent (pip install -e . 후 사용 가능)

```bash
ai-agent https://github.com/org/repo.git
ai-agent --erd --api ./my-project
ai-agent -e -a -d ./my-project
```

| 플래그 | 단축 | 문서 |
|--------|------|------|
| `--erd` | `-e` | ERD (DBML + 요약) |
| `--api` | `-a` | API 스펙 |
| `--arch` | | 아키텍처 다이어그램 |
| `--ddl` | `-d` | DDL (SQL) |
| `--stack` | `-s` | 기술 스택 |

ERD 전용: `--ai-first` (AI 전체 분석), `--use-aoai` (정적 결과 AI 보정)

### 개별 에이전트

```bash
erd-agent ./my-project
api-agent ./my-project
arch-agent ./my-project
ddl-agent ./my-project
stack-agent ./my-project
```

---

## 실행 방법 비교

| | `scripts/run_agent.py` | `function_app.py` (Azure Function) |
|---|---|---|
| **용도** | 로컬 개발 / 테스트 | 프로덕션 서버 |
| **실행** | `python scripts/run_agent.py https://...` | HTTP POST `/api/run` |
| **호출자** | 개발자 (터미널) | Copilot Studio |
| **결과물** | `out/` 폴더에 파일 저장 | JSON 응답으로 반환 |
| **Azure 필요** | ❌ | ✅ |

---

## Azure Function API

### 엔드포인트

```
POST https://docs-ai-agent.azurewebsites.net/api/run
Content-Type: application/json
```

### 요청

```json
{
  "repo_url": "https://github.com/org/repo.git",
  "mode": "all"
}
```

`mode` 값: `all` | `erd` | `api` | `arch` | `ddl` | `stack` (기본값: `all`)

### 응답

```json
{
  "status": "ok",
  "repo_url": "https://github.com/org/repo.git",
  "mode": "all",
  "summary": "...첫 번째 파일 앞 2000자...",
  "artifacts": [
    { "name": "database.dbml", "path": "erd/database.dbml", "content": "..." },
    { "name": "erd_summary.md", "path": "erd/erd_summary.md", "content": "..." },
    { "name": "api_spec.md",    "path": "api/api_spec.md",    "content": "..." },
    { "name": "architecture.md","path": "arch/architecture.md","content": "..." },
    { "name": "schema.sql",     "path": "ddl/schema.sql",     "content": "..." },
    { "name": "tech_stack.md",  "path": "stack/tech_stack.md","content": "..." }
  ],
  "warnings": []
}
```

---

## 출력 구조

```
out/
├── erd/           database.dbml, erd_summary.md
├── api/           api_spec.md
├── arch/          architecture.md
├── ddl/           schema.sql
└── stack/         tech_stack.md
```

---

## 각 에이전트가 하는 일

### ERD Agent

```
JPA Entity 파일 스캔 (@Entity, @Table)
  → Enum / EmbeddedId 정의 파일 추가 수집
  → Azure OpenAI: 테이블·컬럼·PK·FK·Enum 추출 (JSON)
  → Pydantic 검증 → DBML + 요약 MD
```

정적 분석 모드(기본)도 지원: Python JPA 파서가 AST 기반으로 추출.

### API Agent

```
Controller 파일 스캔 (@RestController, @Controller, *Controller.java)
  → Azure OpenAI: 엔드포인트·HTTP 메서드·파라미터·요청/응답 추출 (JSON)
  → Pydantic 검증 → Markdown API 스펙
```

### Architecture Agent

```
설정 파일 수집 (pom.xml, application.yml, Dockerfile, ...)
  + 아키텍처 힌트 파일 (@SpringBootApplication, @Service, ...)
  + 디렉터리 트리 생성
  → Azure OpenAI: 레이어·모듈·외부 시스템·Mermaid 다이어그램 (JSON)
  → Pydantic 검증 → Markdown + Mermaid
```

### DDL Agent

```
JPA Entity 스캔 (ERD Agent와 동일한 스캐너)
  → Azure OpenAI: CREATE TABLE DDL 생성 (JSON)
  → Pydantic 검증 → SQL 파일 (MySQL/PostgreSQL 자동 감지)
```

### Stack Agent

```
빌드/의존성 파일 수집 (pom.xml, build.gradle, package.json, ...)
  → Azure OpenAI: 언어·프레임워크·의존성 분류 (JSON)
  → Pydantic 검증 → Markdown 기술 스택 문서
```

---

## 프로젝트 구조

```
.
├── function_app.py         # Azure Function HTTP 엔드포인트 (POST /api/run)
├── scripts/
│   └── run_agent.py        # 로컬 CLI 실행 스크립트 (pip 불필요)
├── docs/
│   ├── copilot-studio-integration.md   # Copilot Studio 연동 가이드
│   └── ...
└── src/
    ├── erd_agent/          # 코어 + ERD 에이전트
    │   ├── cli.py          # ai-agent · doc-agent · *-agent 진입점
    │   ├── config.py       # 환경 설정 (공용)
    │   ├── repo.py         # Git clone / 로컬 경로 처리
    │   ├── scanner.py      # JPA Entity/Enum/Embeddable 스캐너
    │   ├── commands/erd.py # ERD 생성 로직
    │   ├── parsers/        # 정적 JPA 파서
    │   └── llm/            # Azure OpenAI 클라이언트 + 추출기
    ├── api_agent/          # API 스펙 에이전트
    ├── arch_agent/         # 아키텍처 에이전트
    ├── ddl_agent/          # DDL 에이전트
    └── stack_agent/        # 기술 스택 에이전트
```

---

## 환경 변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `AZURE_OPENAI_ENDPOINT` | ✅ | Azure OpenAI 엔드포인트 |
| `AZURE_OPENAI_API_KEY` | ✅ | API 키 |
| `AZURE_OPENAI_DEPLOYMENT` | ✅ | 배포 이름 (예: `gpt-4.1`) |
| `OPENAI_API_VERSION` | | API 버전 (기본: `2024-06-01`) |
| `GITHUB_TOKEN` | | private repo 접근용 |
| `DOC_OUTPUT_DIR` | | 출력 디렉터리 (기본: `./out`) |
| `CACHE_DIR` | | Git clone 캐시 (기본: `./.cache`) |

Azure Function App 배포 시 위 변수를 Azure Portal → 구성(Configuration) → 애플리케이션 설정에 등록하세요.

---

## 요구 사항

- Python 3.12+
- Azure OpenAI 리소스 (GPT-4.1 권장)
- Azure Functions Core Tools (로컬 Function 실행 시)
