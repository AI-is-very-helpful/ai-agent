# ERD Agent Design

## Why "Static-first + LLM optional"
- Entity/Annotation 기반 구조는 정적 분석이 비용/재현성/테스트 측면에서 유리
- LLM은 모호한 경우(JoinColumn 추론, 커스텀 규칙, 누락된 관계 등)만 제한적으로 사용

## Parser Plugin Interface
- `can_parse(path, text) -> bool`
- `parse(path, text, schema) -> None`
새 파서는 parsers/ 폴더에 추가하고 agent.py에서 등록한다.

## Extensibility Roadmap
1) Kotlin(JPA) parser 강화
2) SQLAlchemy / Django ORM / EF Core parser 추가
3) ERD 외 문서(예: API spec, DDD context map) generator 추가
4) CI(GitHub Actions)로 PR마다 자동 생성 및 diff 코멘트