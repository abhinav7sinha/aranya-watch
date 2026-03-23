#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

cd "$ROOT_DIR"

if [ ! -f ".env" ]; then
  echo "Missing .env file in project root." >&2
  echo "Create .env with at least:" >&2
  echo "  PREVIEW_MODE=false" >&2
  echo "  DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/aranya_watch" >&2
  echo "  FIRMS_API_KEY=your_nasa_firms_api_key" >&2
  exit 1
fi

sh "$SCRIPT_DIR/docker_compose.sh" up --build -d

echo
echo "Waiting for aranya-watch to become healthy..."

HEALTH_URL="http://localhost:8000/health"
MAX_ATTEMPTS=60
ATTEMPT=1

while [ "$ATTEMPT" -le "$MAX_ATTEMPTS" ]; do
  if curl --silent --show-error --fail "$HEALTH_URL" >/dev/null 2>&1; then
    break
  fi
  sleep 1
  ATTEMPT=$((ATTEMPT + 1))
done

if [ "$ATTEMPT" -gt "$MAX_ATTEMPTS" ]; then
  echo "aranya-watch did not become healthy in time." >&2
  echo "Check backend logs with:" >&2
  echo "  sh scripts/docker_compose.sh logs backend" >&2
  exit 1
fi

echo "aranya-watch is ready."
echo "Open:"
echo "  http://localhost:8000/docs"
echo "  http://localhost:8000/dashboard"
echo "  http://localhost:8000/visualizer/india"
echo "  http://localhost:8000/health"
echo
echo "Quick API checks:"
echo "  curl http://localhost:8000/health"
echo "  curl \"http://localhost:8000/alerts/recent?limit=10\""
echo "  curl \"http://localhost:8000/alerts/fire?lat=34.05&lon=-118.25&radius_km=50\""
echo "  curl \"http://localhost:8000/alerts/bbox?min_lat=33.5&max_lat=34.5&min_lon=-119.0&max_lon=-117.5\""
echo "  sh scripts/test_firms_availability.sh --sensor VIIRS_SNPP_NRT"
echo "  sh scripts/test_firms_area.sh --source VIIRS_SNPP_NRT --area world --days 1"
echo
echo "Ingest real FIRMS data after setting FIRMS_API_KEY in .env:"
echo "  sh scripts/docker_compose.sh exec backend python -m ingestion.ingest_fire_alerts --area world --days 1 --source VIIRS_SNPP_NRT"
echo
echo "Stop the stack:"
echo "  sh scripts/dev_down.sh"
