#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$ROOT_DIR"

: "${DATABASE_URL:=postgresql+psycopg2://user_user:user_pass@localhost:5432/user_db}"

alembic upgrade head
