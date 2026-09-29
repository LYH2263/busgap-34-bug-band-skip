from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# create_all 不会给已存在的表补列，这里做幂等的补列迁移。
_ADD_COLUMN_DDL = {
    ("lines", "early_tolerance_min"): "ALTER TABLE lines ADD COLUMN early_tolerance_min FLOAT NOT NULL DEFAULT 0",
    ("lines", "late_tolerance_min"): "ALTER TABLE lines ADD COLUMN late_tolerance_min FLOAT NOT NULL DEFAULT 0",
    ("arrivals", "planned_arrive"): "ALTER TABLE arrivals ADD COLUMN planned_arrive TIMESTAMP",
}


def ensure_columns() -> None:
    insp = inspect(engine)
    with engine.begin() as conn:
        for (table, column), ddl in _ADD_COLUMN_DDL.items():
            if not insp.has_table(table):
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            if column not in existing:
                conn.execute(text(ddl))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
