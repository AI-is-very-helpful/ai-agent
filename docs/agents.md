# 에이전트별 상세

## ERD Agent (`erd_agent`)

**입력:** JPA Entity 소스 (`.java`)
**출력:** `database.dbml`, `erd_summary.md`

### 스캐너 (`scanner.py`)
- `@Entity` 어노테이션 탐지
- `*Entity.java` 파일명 패턴
- `@Enumerated(EnumType.STRING)` → Enum 정의 파일 추가 수집
- `@EmbeddedId` → `@Embeddable` 클래스 파일 추가 수집

### LLM 프롬프트 핵심 규칙
- `@Entity` → Table
- `@Table(name)` → 테이블명
- `@Id` → PK, `@GeneratedValue` → AUTO_INCREMENT
- `@ManyToOne` + `@JoinColumn` → FK
- `@ManyToMany` + `@JoinTable` → Join 테이블
- `@EmbeddedId` → 복합 PK 확장

### 청크 처리
파일이 120K 문자 초과 시 자동으로 청크 분할 후 결과 병합.

---

## API Agent (`api_agent`)

**입력:** Spring Controller 소스
**출력:** `api_spec.md`

### 스캐너 (`scanner.py`)
- `@RestController`, `@Controller`, `@RequestMapping`
- `@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`, `@PatchMapping`
- 파일명 패턴: `*Controller.java`, `*Resource.java`, `*Api.java`

### LLM 프롬프트 핵심 규칙
- `@PathVariable` → path 파라미터
- `@RequestParam` → query 파라미터
- `@RequestBody` → request body
- `ResponseEntity<T>` → response body
- Swagger/OpenAPI 어노테이션 활용

---

## Architecture Agent (`arch_agent`)

**입력:** 설정 파일 + 아키텍처 힌트 파일 + 디렉터리 구조
**출력:** `architecture.md` (Mermaid 다이어그램 포함)

### 스캐너 (`scanner.py`)
- 설정: `pom.xml`, `build.gradle`, `application.yml`, `Dockerfile`, `docker-compose.yml`
- 어노테이션: `@SpringBootApplication`, `@Service`, `@Repository`, `@EnableKafka` 등
- 디렉터리 트리 생성 (depth 4, 빌드 산출물/숨김 폴더 제외)

### LLM 분석 항목
1. 아키텍처 스타일 (Layered, Hexagonal, Microservice 등)
2. 레이어/모듈과 구성 컴포넌트
3. 모듈 간 의존 관계
4. 외부 시스템 (DB, Cache, MQ, 외부 API)
5. Mermaid flowchart 코드

---

## DDL Agent (`ddl_agent`)

**입력:** JPA Entity 소스 (ERD Agent 스캐너 재사용)
**출력:** `schema.sql`

### LLM 프롬프트 핵심 규칙
- Java 타입 → SQL 타입 매핑 (String→VARCHAR, Long→BIGINT 등)
- `@GeneratedValue` → AUTO_INCREMENT / SERIAL
- FK constraint, PK constraint 생성
- Dialect 자동 감지 (MySQL / PostgreSQL)

---

## Stack Agent (`stack_agent`)

**입력:** 빌드·의존성·설정 파일
**출력:** `tech_stack.md`

### 스캐너 (`scanner.py`)
- `pom.xml`, `build.gradle`, `package.json`, `requirements.txt`, `go.mod`
- `Dockerfile`, `docker-compose.yml`
- CI/CD: `.github/workflows/*.yml`
- `application.yml`, `application.properties`

### LLM 분석 항목
1. 언어 + 버전
2. 프레임워크 + 버전
3. 빌드 도구
4. 카테고리별 의존성 분류 (Framework, Database, Testing, Security, Messaging, Cache 등)
