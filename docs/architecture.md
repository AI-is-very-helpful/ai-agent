# Doc Agent — 아키텍처 문서

## 개요

Doc Agent는 Git 레포를 분석해 5종류의 프로젝트 문서를 자동 생성하는 CLI 도구입니다.
각 문서 유형은 독립된 에이전트 패키지로 구현되어 있으며,
공통 인프라(`config`, `repo`, `aoai_client`)를 공유합니다.

## 아키텍처 스타일

**Modular Monolith** — 하나의 패키지(`pip install -e .`)로 설치되지만,
에이전트별로 패키지가 분리되어 독립적으로 개발/확장 가능합니다.

## 구성

```
┌─────────────────────────────────────────────────────┐
│                   CLI Layer                          │
│   ai-agent · doc-agent · erd-agent · api-agent ...  │
│                  (erd_agent/cli.py)                  │
└──────────┬──────────────────────────────┬───────────┘
           │                              │
     ┌─────▼──────┐  ┌────────┐ ┌────────▼────────┐
     │ erd_agent   │  │ 공용    │ │  api_agent      │
     │ commands/   │  │ config │ │  arch_agent     │
     │ scanner     │  │ repo   │ │  ddl_agent      │
     │ parsers     │  │ aoai   │ │  stack_agent    │
     │ llm         │  │ client │ │                 │
     │ model       │  └────────┘ │ scanner         │
     │ dbml_writer │             │ models          │
     │ normalize   │             │ extractor       │
     └─────────────┘             │ writer          │
                                 │ run             │
                                 └─────────────────┘
```

## 에이전트별 파이프라인

모든 에이전트가 동일한 4단계를 따릅니다:

```
1. scan_*()        — 레포에서 관련 파일 수집
2. ai_extract_*()  — Azure OpenAI에 프롬프트 전송, JSON 응답
3. Pydantic 검증   — 응답을 타입 안전하게 파싱
4. write_*()       — 최종 문서 파일 출력 (MD / SQL / DBML)
```

### ERD Agent
- 스캔: `@Entity`, `@Table`, Enum, `@Embeddable`
- 출력: DBML (dbdiagram.io) + 요약 MD
- 특이점: 정적 분석 모드(Python 파서) 별도 지원

### API Agent
- 스캔: `@RestController`, `@Controller`, `*Controller.java`
- 출력: Markdown (엔드포인트 테이블, 파라미터, 요청/응답)

### Architecture Agent
- 스캔: `pom.xml`, `application.yml`, `Dockerfile`, `@SpringBootApplication` 등
- 추가 입력: 디렉터리 트리 (depth 4)
- 출력: Markdown + Mermaid 다이어그램

### DDL Agent
- 스캔: ERD Agent와 동일 (JPA Entity + Enum + Embeddable)
- 출력: CREATE TABLE SQL (MySQL/PostgreSQL dialect 자동 감지)

### Stack Agent
- 스캔: `pom.xml`, `build.gradle`, `package.json`, `requirements.txt`, `Dockerfile`
- 출력: Markdown (언어/프레임워크/의존성 카테고리)

## 공용 모듈 (erd_agent)

| 모듈 | 역할 |
|------|------|
| `config.py` | 환경 변수 로딩 (DOC_OUTPUT_DIR, AZURE_OPENAI_*, GITHUB_TOKEN) |
| `repo.py` | `prepare_repo()` — 로컬 경로 또는 Git URL → 로컬 디렉터리 |
| `llm/aoai_client.py` | `build_aoai_client()` — Azure OpenAI SDK 클라이언트 생성 |

## 확장 방법

새 문서 유형을 추가하려면:

1. `src/새_agent/` 패키지 생성
2. `scanner.py`, `models.py`, `extractor.py`, `writer.py`, `run.py` 작성
3. `erd_agent/cli.py`에 CLI 연결
4. `pyproject.toml`에 스크립트 등록
