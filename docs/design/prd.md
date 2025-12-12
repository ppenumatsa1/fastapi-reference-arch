# Product Requirements Document – TODO API

## Goal

Provide a reference-grade TODO management API that demonstrates FastAPI best practices, CRUD workflows, and operational readiness for Azure deployments.

## Users

- Developers cloning the template for greenfield projects.
- DevOps teams validating infrastructure automation scripts.

## Functional Requirements

1. Create, read, update, delete TODO items.
2. Persist data in PostgreSQL using SQLAlchemy ORM models.
3. Provide health-check endpoint for monitoring.
4. Support environment-based configuration via `.env`.

## Non-Functional Requirements

- 99% of requests respond under 200 ms in local/dev environments.
- Codebase must pass linting (ruff) and formatting (black/isort) gates.
- Automated tests
- Bicep templates

## Out of Scope

- Authentication/Authorization (reserved for Entra integration later).
- Private Network Setup for IAC
- Multi-tenant partitioning.
