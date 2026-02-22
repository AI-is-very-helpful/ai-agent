from __future__ import annotations
from pathlib import Path
import re
import javalang
from erd_agent.model import Schema, Column, Ref
from erd_agent.parsers.base import Parser

def camel_to_snake(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

JAVA_TYPE_MAP = {
    "String": "varchar",
    "int": "int",
    "Integer": "int",
    "long": "bigint",
    "Long": "bigint",
    "boolean": "boolean",
    "Boolean": "boolean",
    "LocalDate": "date",
    "LocalDateTime": "timestamp",
    "Date": "datetime",
    "BigDecimal": "decimal",
    "UUID": "uuid",
}

COLLECTION_TYPES = {"List", "Set", "Collection", "Iterable"}

class JPAJavaParser(Parser):
    def can_parse(self, path: Path, text: str) -> bool:
        return path.suffix.lower() == ".java" and ("@Entity" in text or "@Table" in text)

    def parse(self, path: Path, text: str, schema: Schema) -> None:
        try:
            tree = javalang.parse.parse(text)
        except Exception:
            return

        for t in getattr(tree, "types", []) or []:
            if not hasattr(t, "annotations"):
                continue

            ann_names = {a.name for a in (t.annotations or [])}
            if "Entity" not in ann_names and "Table" not in ann_names:
                continue

            table_name = self._resolve_table_name(t)
            table = schema.ensure_table(table_name)

            for field in getattr(t, "fields", []) or []:
                anns = {a.name: a for a in (field.annotations or [])}

                # 컬렉션/관계의 경우 단순 컬럼이 아닐 수 있음
                raw_type = self._simple_type(field.type)

                for declarator in field.declarators:
                    var_name = declarator.name

                    # 관계 매핑 우선 처리
                    if "ManyToOne" in anns or "OneToOne" in anns:
                        join_col = self._join_column_name(field)
                        fk_col_name = join_col or f"{camel_to_snake(var_name)}_id"

                        if fk_col_name not in table.columns:
                            table.columns[fk_col_name] = Column(
                                name=fk_col_name,
                                db_type="bigint",
                                nullable=True
                            )

                        parent_entity = raw_type
                        parent_table = camel_to_snake(parent_entity)
                        schema.refs.append(Ref(
                            child_table=table_name,
                            child_column=fk_col_name,
                            parent_table=parent_table,
                            parent_column="id",
                            rel=">"  # many-to-one 기본 형태 [2](https://docs.dbdiagram.io/relationships/)[1](https://dbml.dbdiagram.io/docs/)
                        ))
                        continue

                    # ManyToMany는 JoinTable이 있으면 조인 테이블 생성(간단 버전)
                    if "ManyToMany" in anns:
                        jt = self._join_table(field)
                        if jt:
                            join_table, join_col, inv_col = jt
                            jt_table = schema.ensure_table(join_table)
                            # 조인 테이블 컬럼
                            if join_col not in jt_table.columns:
                                jt_table.columns[join_col] = Column(join_col, "bigint", nullable=False)
                            if inv_col not in jt_table.columns:
                                jt_table.columns[inv_col] = Column(inv_col, "bigint", nullable=False)
                            # refs (조인 테이블 -> 양쪽 테이블)
                            schema.refs.append(Ref(join_table, join_col, table_name, "id", ">"))
                            schema.refs.append(Ref(join_table, inv_col, camel_to_snake(raw_type), "id", ">"))
                        continue

                    # OneToMany는 FK가 자식 테이블에 존재하는데, 심볼 해석 없이 완전 추론이 어려워
                    # mappedBy로 "반대편이 ManyToOne을 가지고 있을 가능성"이 높으므로
                    # 여기서는 중복/오탐을 줄이기 위해 기본은 스킵(향후 강화 포인트).
                    if "OneToMany" in anns:
                        continue

                    # 일반 컬럼 처리
                    col = Column(
                        name=camel_to_snake(var_name),
                        db_type=JAVA_TYPE_MAP.get(raw_type, "varchar"),
                    )

                    if "Column" in anns:
                        self._apply_column_annotation(col, anns["Column"])

                    if "Id" in anns:
                        col.pk = True
                        col.nullable = False

                    if "GeneratedValue" in anns:
                        col.increment = True  # IDENTITY 등 자동 생성 의미 [11](https://stackoverflow.com/questions/20603638/what-is-the-use-of-annotations-id-and-generatedvaluestrategy-generationtype)[12](https://www.geeksforgeeks.org/advance-java/hibernate-generatedvalue-annotation-in-jpa/)

                    # @Enumerated 등은 일단 varchar로 처리(확장 가능)
                    if "Enumerated" in anns:
                        col.db_type = "varchar"

                    table.columns[col.name] = col

    def _simple_type(self, t) -> str:
        # List<Book> 같은 경우: t.name == "List", t.arguments[0].type.name == "Book"
        try:
            name = t.name
            if name in COLLECTION_TYPES and getattr(t, "arguments", None):
                arg0 = t.arguments[0]
                inner = getattr(arg0, "type", None)
                if inner is not None and getattr(inner, "name", None):
                    return inner.name
            return name
        except Exception:
            return "String"

    def _resolve_table_name(self, class_decl) -> str:
        # @Table(name="STUDENT", schema="SCHOOL") 가능 [3](https://www.baeldung.com/jpa-entities)
        table = None
        schema = None
        entity_name = class_decl.name

        for a in (class_decl.annotations or []):
            if a.name == "Entity":
                # @Entity(name="student") 가능 [3](https://www.baeldung.com/jpa-entities)
                n = self._ann_kv(a, "name")
                if n:
                    entity_name = n
            if a.name == "Table":
                table = self._ann_kv(a, "name")
                schema = self._ann_kv(a, "schema")

        base = table or camel_to_snake(entity_name)
        if schema:
            # DBML: Table schema.table 지원 [1](https://dbml.dbdiagram.io/docs/)
            return f"{schema}.{base}"
        return base

    def _apply_column_annotation(self, col: Column, ann) -> None:
        name = self._ann_kv(ann, "name")
        if name:
            col.name = name

        nullable = self._ann_kv(ann, "nullable")
        if nullable is not None:
            col.nullable = (str(nullable).lower() != "false")

        unique = self._ann_kv(ann, "unique")
        if unique is not None:
            col.unique = (str(unique).lower() == "true")

        length = self._ann_kv(ann, "length")
        if length and col.db_type.startswith("varchar"):
            # DBML 타입은 단어 1개(공백 없이)면 허용되는 케이스가 많아 varchar(255)로 표현 [1](https://dbml.dbdiagram.io/docs/)
            col.db_type = f"varchar({length})"

    def _join_column_name(self, field) -> str | None:
        for a in (field.annotations or []):
            if a.name == "JoinColumn":
                return self._ann_kv(a, "name")
        return None

    def _join_table(self, field):
        # @JoinTable(name="user_roles", joinColumns=@JoinColumn(name="user_id"), inverseJoinColumns=@JoinColumn(name="role_id"))
        for a in (field.annotations or []):
            if a.name != "JoinTable":
                continue
            name = self._ann_kv(a, "name")
            join_col = self._ann_nested_joincol(a, "joinColumns")
            inv_col = self._ann_nested_joincol(a, "inverseJoinColumns")
            if name and join_col and inv_col:
                return name, join_col, inv_col
        return None

    def _ann_kv(self, ann, key: str):
        pairs = ann.element if isinstance(ann.element, list) else ([ann.element] if ann.element else [])
        for p in pairs:
            if getattr(p, "name", None) == key:
                return self._literal(getattr(p, "value", None))
        return None

    def _ann_nested_joincol(self, ann, key: str) -> str | None:
        # JoinTable 안에 joinColumns=@JoinColumn(name="x") 형태
        pairs = ann.element if isinstance(ann.element, list) else ([ann.element] if ann.element else [])
        for p in pairs:
            if getattr(p, "name", None) != key:
                continue
            v = getattr(p, "value", None)
            # v는 Annotation(JoinColumn)일 수 있음
            if getattr(v, "name", None) == "JoinColumn":
                return self._ann_kv(v, "name")
        return None

    def _literal(self, node) -> str | None:
        if node is None:
            return None
        s = getattr(node, "value", None)
        if s is None:
            return None
        return s.strip("\"'")