from pgvector.sqlalchemy import Vector

from app.core.config import EMBEDDING_DIMENSION
from app.db.base import Base
import app.models  # noqa: F401


def test_schema_contains_all_application_tables() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "profiles",
        "pool_items",
        "jobs",
        "generated_cvs",
        "github_connections",
        "pipeline_runs",
    }


def test_tenant_tables_have_indexed_user_id() -> None:
    for table_name in Base.metadata.tables.keys() - {"users"}:
        table = Base.metadata.tables[table_name]
        assert table.c.user_id.index is True
        assert any(fk.target_fullname == "users.id" for fk in table.c.user_id.foreign_keys)


def test_pool_item_embedding_uses_configured_dimension() -> None:
    embedding_type = Base.metadata.tables["pool_items"].c.embedding.type

    assert isinstance(embedding_type, Vector)
    assert embedding_type.dim == EMBEDDING_DIMENSION == 1024
