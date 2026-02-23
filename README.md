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

## Quick Start

```bash
# 1. 설치
git clone <this-repo>
cd doc-agent
pip install -e .

# 2. Azure OpenAI 설정
cp .env.example .env
# .env에 AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT 입력

# 3. 실행
ai-agent https://github.com/your-org/your-project.git
```

`out/` 디렉터리에 5가지 문서가 생성됩니다.

---

## 사용법

### ai-agent (권장) — 플래그로 선택

```bash
# 전체 문서 생성 (플래그 없으면 전부)
ai-agent ./my-project
ai-agent https://github.com/org/repo.git

# 원하는 문서만 선택
ai-agent --erd --api ./my-project
ai-agent --api --arch --stack ./my-project
ai-agent -e -a -d ./my-project     # 단축: -e=erd, -a=api, -d=ddl, -s=stack
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

### doc-agent (서브커맨드)

```bash
doc-agent all ./my-project
doc-agent erd ./my-project
doc-agent api ./my-project
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

출력 위치는 환경변수 `DOC_OUTPUT_DIR`로 변경 가능 (기본: `./out`).

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
src/
├── erd_agent/              # 코어 + ERD 에이전트
│   ├── cli.py              # ai-agent · doc-agent · *-agent 진입점
│   ├── config.py           # 환경 설정 (공용)
│   ├── repo.py             # Git clone / 로컬 경로 처리 (공용)
│   ├── scanner.py          # JPA Entity/Enum/Embeddable 스캐너
│   ├── commands/erd.py     # ERD 생성 로직
│   ├── parsers/jpa_java.py # 정적 JPA 파서
│   ├── llm/
│   │   ├── aoai_client.py  # Azure OpenAI 클라이언트 (공용)
│   │   ├── jpa_ai_extractor.py
│   │   ├── schema_models.py
│   │   └── schema_refiner.py
│   ├── model.py            # Schema/Table/Column/Ref 모델
│   ├── normalize.py        # 스키마 정합성 보정
│   ├── dbml_writer.py      # DBML 생성
│   └── docs_writer.py      # ERD 요약 MD
│
├── api_agent/              # API 스펙 에이전트
│   ├── scanner.py          # @RestController 파일 탐색
│   ├── models.py           # Endpoint/Controller Pydantic 모델
│   ├── extractor.py        # LLM 프롬프트 + 호출
│   ├── writer.py           # Markdown 출력
│   └── run.py              # run_api()
│
├── arch_agent/             # 아키텍처 에이전트
│   ├── scanner.py          # 설정 파일 + 디렉터리 트리
│   ├── models.py           # Layer/Dependency/Mermaid 모델
│   ├── extractor.py        # LLM 프롬프트
│   ├── writer.py           # Markdown + Mermaid 출력
│   └── run.py              # run_arch()
│
├── ddl_agent/              # DDL 에이전트
│   ├── models.py           # DDL Table/Column/Constraint 모델
│   ├── extractor.py        # LLM 프롬프트
│   ├── writer.py           # SQL 출력
│   └── run.py              # run_ddl()
│
└── stack_agent/            # 기술 스택 에이전트
    ├── scanner.py          # 빌드/의존성 파일 탐색
    ├── models.py           # Stack/Category/Dependency 모델
    ├── extractor.py        # LLM 프롬프트
    ├── writer.py           # Markdown 출력
    └── run.py              # run_stack()
```

---

## 환경 변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `AZURE_OPENAI_ENDPOINT` | O | Azure OpenAI 엔드포인트 |
| `AZURE_OPENAI_API_KEY` | O | API 키 |
| `AZURE_OPENAI_DEPLOYMENT` | O | 배포 이름 (예: `gpt-4.1`) |
| `OPENAI_API_VERSION` | | API 버전 (기본: `2024-06-01`) |
| `GITHUB_TOKEN` | | private repo 접근용 |
| `DOC_OUTPUT_DIR` | | 출력 디렉터리 (기본: `./out`) |
| `CACHE_DIR` | | Git clone 캐시 (기본: `./.cache`) |

---

## 동작 흐름

```
레포 (경로 또는 Git URL)
    │
    ▼
prepare_repo()  ─── Git URL이면 clone, 로컬이면 그대로
    │
    ▼
┌─────────────────────────────────────────┐
│  선택된 에이전트별 실행                   │
│                                          │
│  scan_*()  →  파일 수집                  │
│      ↓                                   │
│  ai_extract_*()  →  Azure OpenAI 호출    │
│      ↓                                   │
│  Pydantic 검증  →  구조화 데이터          │
│      ↓                                   │
│  write_*()  →  MD / SQL / DBML 출력      │
└─────────────────────────────────────────┘
    │
    ▼
out/erd/  out/api/  out/arch/  out/ddl/  out/stack/
```

---

## 요구 사항

- Python 3.12+
- Azure OpenAI 리소스 (GPT-4.1 권장)
