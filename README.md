## Database Migrations (Alembic)

Migrations manage the schema for the `documents`, `chunks`, and `chunk_embeddings` tables (and the `vector` extension) defined in `src/app/models/rag.py`. The DB connection is read from `VECTOR_DB_URL` in `.env`.

Start Postgres before running any command below:

```bash
docker compose up -d postgres
```

### Apply migrations

```bash
uv run alembic upgrade head
```

### Create a new migration

After changing a model in `src/app/models/`, generate a migration from the diff:

```bash
uv run alembic revision --autogenerate -m "describe the change"
```

Always review the generated file in `alembic/versions/` before applying it — autogenerate can miss things like custom types (e.g. it doesn't know how to import `pgvector.sqlalchemy.Vector`) or data-only changes.

For a migration with no model diff to autogenerate from (e.g. raw SQL, extensions, data backfills), create an empty revision and edit it by hand:

```bash
uv run alembic revision -m "describe the change"
```

### Roll back

```bash
uv run alembic downgrade -1   # one step back
uv run alembic downgrade base # all the way back
```

### Inspect state

```bash
uv run alembic current   # revision currently applied to the DB
uv run alembic history   # full migration chain
```
