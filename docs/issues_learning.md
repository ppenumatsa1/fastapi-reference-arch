# Issues and Learnings

## 1) Entra app registration automation in Bicep was not feasible

- Symptom:
  - Need repeatable API/client app registrations with role assignment during `azd` provisioning.
- Root cause:
  - Current IaC path uses Bicep, and app registration lifecycle is not managed as a first-class Bicep resource in this template.
- Fix:
  - Implemented idempotent app registration + role + secret automation in `infra/hooks/preprovision.sh` using `az ad` and Graph (`az rest`) operations.
- Learning:
  - Keep identity bootstrap in preprovision hooks when IaC provider does not cleanly cover Entra object lifecycle.

## 2) Single role model was too coarse for API authorization

- Symptom:
  - A single `Todos.ReadWrite` role prevented least-privilege access for read-only clients.
- Root cause:
  - Route authorization originally used one global router dependency.
- Fix:
  - Split to `Todos.Read` and `Todos.Write` route-level checks and retained write-implies-read behavior in dependency logic.
- Learning:
  - Define read/write roles early so access boundaries map directly to endpoint behavior.

## 3) Auth smoke tests required better env handoff

- Symptom:
  - `verify_deployment.sh --base-url ...` required manual token arguments in every run.
- Root cause:
  - Script only read in-process shell env variables.
- Fix:
  - Added azd env fallback loading for `ENTRA_*` values when auth mode is enabled.
- Learning:
  - Deployment smoke scripts should consume active deployment state (`azd env`) by default.

## 4) Token issuance failed after first automation run (`invalid_client`)

- Symptom:
  - Remote smoke test failed to get token with `AADSTS7000215: Invalid client secret provided`.
- Root cause:
  - Existing stored secret in azd env was stale/invalid for current client app credentials.
- Fix:
  - Rotated client secret with `az ad app credential reset --append` and updated `ENTRA_CLIENT_SECRET` in azd env.
- Learning:
  - Add secret-rotation fallback guidance to runbooks for first-time or drifted tenant states.

## Current Snapshot (validated)

- `make lint` and `make test` passed (`28` tests).
- `azd provision --preview` completed successfully.
- `azd up` completed successfully and deployed endpoint:
  - `https://azacat4e7cr2gwaes2.greenisland-c16ef19f.canadacentral.azurecontainerapps.io`
- Post-deploy checks passed in requested order:
  - `sleep 10` -> `verify_deployment.sh --base-url ...`
  - `sleep 10` -> `scripts/kusto/run-observability-suite.sh`
