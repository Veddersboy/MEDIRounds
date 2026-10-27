# ORM and Schema Validation

Added SQLAlchemy models, Pydantic schemas, and Alembic migrations to manage the MediRounds database.

### Database Changes

Database tables are defined in `app/models.py`, and input validation is handled in `app/schemas.py`.

When adding or modifying a database table:

1. Make the changes in `app/models.py`.

2. Generate a migration:

   ```bash
   python -m alembic revision --autogenerate --rev-id 000x -m "add new field"
   ```

3. Review the generated migration and apply it:

   ```bash
   alembic upgrade head
   ```

4. Verify the current position
   ```bash
   alembic current
   ```

5. Roll back the most recent migration
   ```bash
   alembic downgrade -1
   ```

Migrations are stored in `alembic/versions/` and should be committed so other developers can apply the same database changes.

### Working with the Database

Use the SQLAlchemy session from `app/database.py` to query, insert, update, or delete records.

```python
from app.database import get_db
from app.models import User
```

Use Pydantic schemas from `app/schemas.py` when defining API request and response formats.

```python
from app.schemas import MessageCreate
```

### Testing

Two tests were added to check database migrations and schema validation.

Run them from the `backend/` directory:

```bash
python -m pytest -v
```

### Notes

- PostgreSQL must be running before applying migrations.
- Database connection settings are stored in `.env`.
- Alembic changes the database structure; SQLAlchemy handles the actual data.
- The initial migration creates the tables needed for users, chats, messages, citations, and settings.