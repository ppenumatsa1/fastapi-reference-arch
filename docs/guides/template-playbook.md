# Template Playbook

Use this repo as a reference starter by following these rules.

## Feature Layout

1. Add a feature module under `app/modules/<feature>/`.
2. Include internal files as needed:
   - `model.py`
   - `repository.py`
   - `service.py`
   - `schemas.py`
   - `mapper.py` (optional)

## API Boundary

1. Expose HTTP endpoints under `app/api/v1/`.
2. Add request/response DTOs in `app/api/v1/schemas/<feature>.py`.
3. Add routers in `app/api/v1/routers/<feature>.py`.

## Error Handling Rule

1. Keep domain faults in services.
2. Raise `AppError` subclasses from service code.
3. Let global handlers in `app/main.py` convert app errors into API responses.

## Versioning Rule

1. Add `app/api/v2/` only for breaking API contract changes.
2. Reuse module services/repositories across versions whenever possible.
