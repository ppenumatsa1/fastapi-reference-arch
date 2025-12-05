# User Flow

1. Client sends CRUD request to FastAPI route (e.g., `POST /api/v1/todos`).
2. Route delegates to `TodoService`, which validates business rules.
3. Service calls `TodoRepository` to interact with PostgreSQL via SQLAlchemy.
4. Repository persists/fetches data; results map back into Pydantic schemas.
5. Response returns to client with consistent JSON contract.
6. Observability/logging captures key events for diagnostics.
