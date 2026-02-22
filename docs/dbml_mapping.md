# DBML Mapping Rules

## Table/Column
- Table <name> { ... }
- Column settings: [pk], [increment], [unique], [not null], [default: ...], [note: '...']

## Relationship (Ref)
- many-to-one: Ref: child.col > parent.col
- one-to-many: Ref: parent.col < child.col
- one-to-one: Ref: a.col - b.col
- many-to-many: Ref: a.col <> b.col (보통 조인 테이블로 모델링 권장)

참고: dbdiagram DBML 문서/Relationships 문서
``