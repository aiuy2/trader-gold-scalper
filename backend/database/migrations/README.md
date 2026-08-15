# backend/database/migrations/

Intentionally empty for now.

`backend/database/database.py:init_db()` calls
`Base.metadata.create_all(bind=engine)` on startup, which is sufficient
for the local/dev path (SQLite, or a fresh Postgres database) since it
creates any table that doesn't exist yet from the current SQLAlchemy
models.

What `create_all` **cannot** do is evolve an existing table (rename/drop a
column, change a constraint) without losing data. If/when the schema
needs that kind of change against a live database, add
[Alembic](https://alembic.sqlalchemy.org/) here:

```
pip install alembic
alembic init backend/database/migrations
# point alembic.ini's sqlalchemy.url at settings.DB_URL,
# set target_metadata = Base.metadata in env.py
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

Until then, the Supabase-facing schema lives in `../../database/schema.sql`
(and `views.sql` / `indexes.sql` / `triggers.sql` alongside it) - keep
both in sync by hand when you add/change a model.
