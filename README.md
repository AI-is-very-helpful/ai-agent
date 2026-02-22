# ERD Agent (AI‑First JPA ERD Generator)

Java JPA 기반 프로젝트를 분석하여  
**dbdiagram.io에서 바로 시각화 가능한 DBML ERD**를 생성하는 도구입니다.

이 도구는 두 가지 분석 모드를 제공합니다.

- ✅ **정적 분석 모드 (기본)**: Python 기반 JPA 파서
- ✅ **AI‑First 모드 (옵션)**: Azure AI Foundry / GPT‑4.1 기반 의미 분석

---

## ✨ 주요 특징

- ✅ Java JPA Entity 자동 스캔 (`@Entity`)
- ✅ 컬럼, PK, FK, Join Table 자동 추출
- ✅ DBML 포맷 ERD 생성
- ✅ ERD 요약 Markdown 문서 생성
- ✅ **AI‑First 모드로 Enum / 도메인 의미 해석**
- ✅ GitHub Repository 직접 분석 지원

---

## 🔀 분석 모드 개요

### 1️⃣ 정적 분석 모드 (기본)

```bash
erd-agent <repo-path-or-git-url>
```

- Python AST + 규칙 기반 분석
- 빠르고 비용 없음
- 항상 동일한 결과 (deterministic)
- 한계:
  - Enum 의미
  - 도메인 의도
  - 복합 관계 추론 → 제한적

---

### 2️⃣ AI‑First 분석 모드 (권장)
```shell
erd-agent <repo-path-or-git-url> --ai-first
```

- Azure AI Foundry + GPT‑4.1
- 정적 분석을 완전히 건너뜀
- 코드 전체 맥락을 이해하여 ERD 생성
- Enum, Value Object, Join 의도까지 해석

✅ Python은 DBML 생성만 담당
✅ 구조 결정은 AI가 담당

---
## 🤖 AI‑First 모드에서 AI가 하는 일
AI는 다음을 수행합니다:

@Enumerated(EnumType.STRING) → Enum 정의 생성
Enum 값 목록 추출
관계 의도 해석

Many‑to‑Many vs Join Entity


컬럼 타입의 도메인 의미 보정
ERD 관점에서 더 적절한 구조 선택

Python은:

AI가 반환한 구조화 JSON 검증
DBML 문법으로 변환
결과 파일 생성

---

## 📁 프로젝트 구조
src/erd_agent/
├─ agent.py                 # CLI 진입점
├─ scanner.py               # Entity / Enum 후보 파일 탐색
├─ parsers/
│  └─ jpa_java.py           # 정적 JPA 파서
├─ llm/
│  ├─ jpa_ai_extractor.py   # ✅ AI‑First 분석기
│  ├─ schema_models.py      # AI 출력 JSON 스키마
│  └─ aoai_client.py        # Azure AI Foundry / OpenAI client
├─ model.py                 # Schema / Table / Column / Enum 모델
├─ normalize.py             # 스키마 정합성 보정
├─ dbml_writer.py           # DBML 생성
├─ docs_writer.py           # ERD 요약 문서 생성
└─ repo.py                  # Git clone / local repo 처리

---

## ⚙️ 설치
```shell

git clone <this-repo>
cd erd-agent
pip install -e .

```
Python 3.12 이상 권장

---

## 🔑 Azure AI Foundry 설정 (AI‑First 모드)
AI‑First 모드는 Azure AI Foundry를 사용합니다.

### ✅ 필수 환경 변수
```
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://<resource-name>.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=<deployment-name>
```
⚠️ 주의 사항

model 이름 ❌ → deployment 이름 ✅
Foundry 사용 시 /openai/v1 엔드포인트 사용
OpenAI SDK(v1) 기반 호출

---

## 🚀 사용 예시
### 정적 분석
```shell
erd-agent ./my-jpa-project
```

### AI‑First 분석
```shell
erd-agent ./my-jpa-project --ai-first
```

### 결과
out/
├─ database.dbml
└─ erd_summary.md

---

## 🧠 동작 원리 (Architecture 요약)
Repository
   ↓
Python (Scanner)
   ↓
[ AI‑First Mode ]
   ↓
Azure AI Foundry (GPT‑4.1)
   ↓
Structured JSON Schema
   ↓
Python (DBML Writer)
   ↓
ERD (DBML)

