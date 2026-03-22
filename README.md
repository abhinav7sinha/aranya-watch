# AranyaCore

AranyaCore is a forest intelligence MVP that ingests near real-time NASA FIRMS fire alerts, stores them in PostgreSQL/PostGIS, and exposes a developer-first REST API with simple geospatial search and risk scoring.

Built for teams that want a clean starting point for wildfire monitoring infrastructure, AranyaCore focuses on a small, production-minded core:

- reliable FIRMS ingestion
- PostGIS-backed geospatial queries
- a minimal FastAPI surface
- a lightweight dashboard for quick inspection

## Architecture

```text
NASA FIRMS API
    -> ingestion/firms_client.py
    -> ingestion/ingest_fire_alerts.py
    -> PostgreSQL + PostGIS
    -> FastAPI
    -> REST API + Dashboard
```

## Features

- NASA FIRMS ingestion for `VIIRS_SNPP_NRT`
- PostGIS-backed `fire_alerts` storage with geospatial index
- Radius and bounding-box search using PostGIS functions
- Simple heuristic `risk_score` based on brightness and confidence
- Minimal HTML dashboard for recent alerts
- Dockerized local development setup

## Quick Start

1. Copy the env file:

```bash
cp .env.example .env
```

2. In `.env`, set:

```bash
PREVIEW_MODE=false
FIRMS_API_KEY=your_nasa_firms_api_key
```

3. Start everything with one command:

```bash
sh scripts/dev_up.sh
```

4. Open:

- API docs: `http://localhost:8000/docs`
- Dashboard: `http://localhost:8000/dashboard`
- Health: `http://localhost:8000/health`

5. Verify the real backend is active:

```bash
curl http://localhost:8000/health
```

The response should include `"preview_mode": false`.

The app may start with no alerts in the database. That is expected until you ingest FIRMS data.

## One-Command Lifecycle

Start the full local stack:

```bash
sh scripts/dev_up.sh
```

The start script prints:

- the local URLs
- a health-checked "ready" message after the backend responds
- sample `curl` commands for the API
- the ingestion command for FIRMS data
- the one-command shutdown command

Stop the full local stack:

```bash
sh scripts/dev_down.sh
```

Stop and remove the Postgres volume too:

```bash
sh scripts/dev_down.sh --volumes
```

## Ingest Real Fire Data

Run ingestion inside the backend container:

```bash
sh scripts/docker_compose.sh exec backend python -m ingestion.ingest_fire_alerts --area world --days 1 --source VIIRS_SNPP_NRT
```

Example API calls after ingestion:

```bash
curl "http://localhost:8000/alerts/recent?limit=10"
curl "http://localhost:8000/alerts/fire?lat=34.05&lon=-118.25&radius_km=50"
curl "http://localhost:8000/alerts/bbox?min_lat=33.5&max_lat=34.5&min_lon=-119.0&max_lon=-117.5"
```

This ingestion step is designed to run every 10 to 15 minutes from cron, a scheduled container job, or another lightweight scheduler.

## API Reference

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Service health and preview-mode status |
| `GET /alerts/recent?limit=N` | Latest `N` fire alerts |
| `GET /alerts/fire?lat=...&lon=...&radius_km=...` | Nearby alerts using a radius query |
| `GET /alerts/bbox?min_lat=...&max_lat=...&min_lon=...&max_lon=...` | Alerts inside a bounding box |
| `GET /dashboard` | Minimal HTML dashboard for recent alerts |

## Preview Mode

If you want to inspect the API before Postgres/PostGIS is available:

```bash
PREVIEW_MODE=true
```

Then run locally:

```bash
python3.13 -m venv .venv
. .venv/bin/activate
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/dashboard`
- `http://127.0.0.1:8000/health`

Stop with:

```bash
Ctrl+C
```

## Local PostgreSQL/PostGIS Setup

If you want to run the backend directly on your machine instead of Docker:

```bash
brew install postgis
brew services start postgresql@18
createdb aranyacore
psql -d aranyacore -c 'CREATE EXTENSION IF NOT EXISTS postgis;'
cp .env.example .env
python3.13 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Set in `.env`:

```bash
PREVIEW_MODE=false
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/aranyacore
```

Stop with `Ctrl+C`, then optionally:

```bash
brew services stop postgresql@18
```

## Troubleshooting

If `docker compose` is not available on macOS, add Docker Desktop's plugin path to `~/.docker/config.json`:

```json
{
  "cliPluginsExtraDirs": [
    "/Applications/Docker.app/Contents/Resources/cli-plugins"
  ]
}
```

If Docker Desktop is running but your shell cannot connect to the daemon, this socket may work:

```bash
export DOCKER_HOST=unix://$HOME/.docker/run/docker.sock
```

The helper scripts in `scripts/` already handle this fallback automatically for local Docker usage.

## Project Structure

```text
app/
  main.py
  api/
  services/
  models/
  db/
  core/
ingestion/
  firms_client.py
  ingest_fire_alerts.py
scripts/
docker/
tests/
requirements.txt
docker-compose.yml
README.md
```

## Development Notes

- Python 3.11+
- FastAPI + SQLAlchemy 2.x
- PostgreSQL 16 + PostGIS
- `httpx` for FIRMS API calls
- `pytest` for lightweight unit tests

## Testing

```bash
pytest
```
