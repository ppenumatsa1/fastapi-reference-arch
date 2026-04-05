#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$ROOT_DIR"

: "${DATABASE_URL:=postgresql+psycopg2://todo_user:todo_pass@localhost:5432/todo_db}"

alembic upgrade head
