# ERD Agent Architecture

## Goal
GitHub(또는 로컬) 레포지토리의 소스코드에서 DB 관련 정의(Entity/Annotation 등)를 추출해
dbdiagram.io에서 시각화 가능한 DBML을 생성한다.

## Pipeline
1) Scan: Entity 후보 파일 탐색 (xxEntity, models 폴더, @Table/@Entity 등)
2) Parse: 언어/프레임워크별 Parser plugin으로 Schema 구성
3) Normalize: naming/type/relationship 보정
4) Emit: DBML(database.dbml) 출력
5) Docs: ERD 요약/테이블 설명/변경 이력 문서 생성 (확장)
6) Watch/CI: 변경 감지 후 자동 업데이트 (확장)

## Modules
- scanner.py: 후보 파일 탐지
- parsers/: 언어/프레임워크별 추출기
- model.py: Schema/Table/Column/Ref 데이터 모델
- dbml_writer.py: DBML 생성기
- llm/: Azure OpenAI 보정(선택)
- watch.py: 파일 변경 감지 기반 자동 재생성