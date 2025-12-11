#!/bin/sh
set -e

# Ensure IMAGE param is set from the packaged image name so azd deploy uses the pushed image automatically.
# azd writes SERVICE_API_IMAGE_NAME into the environment (.azure/<env>/.env) after packaging.

if ! command -v azd >/dev/null 2>&1; then
  echo "azd CLI is required" >&2
  exit 1
fi

ENV_NAME="${AZURE_ENV_NAME:-dev}"
VALUES=$(azd env get-values --output json)
IMAGE_NAME=$(echo "$VALUES" | jq -r '.SERVICE_API_IMAGE_NAME // ""')

if [ -z "$IMAGE_NAME" ] || [ "$IMAGE_NAME" = "null" ]; then
  echo "No SERVICE_API_IMAGE_NAME found; ensure azd package ran." >&2
  exit 1
fi

# Also tag and push as :latest for convenience
LATEST_IMAGE="${IMAGE_NAME%:*}:latest"
echo "Tagging image as latest: $LATEST_IMAGE"
docker tag "$IMAGE_NAME" "$LATEST_IMAGE"
docker push "$LATEST_IMAGE"

echo "Setting IMAGE parameter to packaged image: $IMAGE_NAME"
azd env set IMAGE "$IMAGE_NAME"
