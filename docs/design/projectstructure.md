# Project Structure

```
fastapi-reference-arch/
├── app/
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── exceptions/
│   │   ├── logging/
│   │   └── utils/
│   ├── repo/
│   ├── routes/
│   ├── services/
│   └── main.py
├── infra/
│   └── scripts/
├── scripts/
├── tests/
├── docs/
│   └── design/
├── Dockerfile
└── docker-compose.yml
```

- Files/directories use `snake_case`; classes use `PascalCase`.
- Routes expose plural nouns (`/todos`).
- Services/repositories mirror entity names (`TodoService`, `TodoRepository`).
- Docker assets remain at the repository root for clarity during deployment builds.
