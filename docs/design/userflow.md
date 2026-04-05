# User Flow

1. Client sends CRUD request to FastAPI route (e.g., `POST /api/v1/users`).
2. Route delegates to `UserService`, which validates business rules.
3. Service calls `UserRepository` to interact with PostgreSQL via SQLAlchemy.
4. Repository persists/fetches data; results map back into Pydantic schemas.
5. Response returns to client with consistent JSON contract.
6. Observability/logging captures key events for diagnostics.
