"""FastAPI routes for aranya-watch."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.schemas import FireAlertRead
from app.services.fire_alerts import (
    get_alerts_in_bbox,
    get_alerts_within_radius,
    get_recent_alerts,
)
from app.services.preview_alerts import (
    get_preview_alerts_in_bbox,
    get_preview_alerts_within_radius,
    get_recent_preview_alerts,
)

router = APIRouter()


@router.get("/health")
def healthcheck(request: Request) -> dict[str, str | bool]:
    """Return service health information."""

    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "preview_mode": bool(getattr(request.app.state, "preview_mode", False)),
    }


@router.get("/alerts/recent", response_model=list[FireAlertRead])
def recent_alerts(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    session: Session = Depends(get_db_session),
) -> list[FireAlertRead]:
    """Return the latest N fire alerts."""

    if getattr(request.app.state, "preview_mode", False):
        return get_recent_preview_alerts(limit=limit)

    alerts = get_recent_alerts(session=session, limit=limit)
    return [FireAlertRead.from_orm_with_risk(alert) for alert in alerts]


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    limit: int = Query(default=25, ge=1, le=100),
    session: Session = Depends(get_db_session),
) -> HTMLResponse:
    """Render a minimal dashboard with recent alerts."""

    preview_mode = getattr(request.app.state, "preview_mode", False)
    alerts = (
        get_recent_preview_alerts(limit=limit)
        if preview_mode
        else [FireAlertRead.from_orm_with_risk(alert) for alert in get_recent_alerts(session=session, limit=limit)]
    )
    rows = "\n".join(
        [
            (
                "<tr>"
                f"<td>{alert.acq_datetime.isoformat()}</td>"
                f"<td>{alert.latitude:.4f}</td>"
                f"<td>{alert.longitude:.4f}</td>"
                f"<td>{alert.brightness:.1f}</td>"
                f"<td>{alert.confidence}</td>"
                f"<td>{alert.risk_score:.2f}</td>"
                "</tr>"
            )
            for alert in alerts
        ]
    )
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>aranya-watch Dashboard</title>
      <style>
        :root {{
          color-scheme: light;
          --bg: #f7f3ea;
          --panel: #fffdf8;
          --ink: #17261d;
          --muted: #53645b;
          --accent: #b94f2d;
          --border: #d9cbb6;
        }}
        body {{
          margin: 0;
          font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
          background: linear-gradient(180deg, #efe2c5 0%, var(--bg) 30%, #f5f2eb 100%);
          color: var(--ink);
        }}
        main {{
          max-width: 1100px;
          margin: 0 auto;
          padding: 48px 20px 64px;
        }}
        .hero {{
          margin-bottom: 24px;
        }}
        h1 {{
          margin: 0 0 8px;
          font-size: 2.5rem;
        }}
        p {{
          margin: 0;
          color: var(--muted);
        }}
        .panel {{
          background: rgba(255, 253, 248, 0.92);
          border: 1px solid var(--border);
          border-radius: 20px;
          overflow: hidden;
          box-shadow: 0 12px 40px rgba(32, 38, 35, 0.08);
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
        }}
        th, td {{
          padding: 14px 16px;
          text-align: left;
          border-bottom: 1px solid #eee4d6;
          font-size: 0.95rem;
        }}
        th {{
          background: #f8efe0;
          color: var(--ink);
        }}
        .accent {{
          color: var(--accent);
          font-weight: 700;
        }}
      </style>
    </head>
    <body>
      <main>
        <section class="hero">
          <h1>aranya-watch</h1>
          <p>Recent NASA FIRMS fire alerts with a simple heuristic risk score.</p>
          {"<p class='accent'>Preview mode is active. Showing sample alerts because the database is unavailable.</p>" if preview_mode else ""}
        </section>
        <section class="panel">
          <table>
            <thead>
              <tr>
                <th>Acquired</th>
                <th>Latitude</th>
                <th>Longitude</th>
                <th>Brightness</th>
                <th>Confidence</th>
                <th>Risk</th>
              </tr>
            </thead>
            <tbody>{rows or '<tr><td colspan="6">No alerts available.</td></tr>'}</tbody>
          </table>
        </section>
      </main>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/alerts/bbox", response_model=list[FireAlertRead])
def bbox_alerts(
    request: Request,
    min_lat: float = Query(..., ge=-90, le=90),
    max_lat: float = Query(..., ge=-90, le=90),
    min_lon: float = Query(..., ge=-180, le=180),
    max_lon: float = Query(..., ge=-180, le=180),
    session: Session = Depends(get_db_session),
) -> list[FireAlertRead]:
    """Return fire alerts inside a bounding box."""

    if min_lat > max_lat or min_lon > max_lon:
        raise HTTPException(status_code=400, detail="Bounding box minimums must be less than maximums.")

    if getattr(request.app.state, "preview_mode", False):
        return get_preview_alerts_in_bbox(
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
        )

    alerts = get_alerts_in_bbox(
        session=session,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
    )
    return [FireAlertRead.from_orm_with_risk(alert) for alert in alerts]


@router.get("/alerts/fire", response_model=list[FireAlertRead])
def nearby_fire_alerts(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(..., gt=0, le=1000),
    session: Session = Depends(get_db_session),
) -> list[FireAlertRead]:
    """Return fire alerts near a location."""

    if getattr(request.app.state, "preview_mode", False):
        return get_preview_alerts_within_radius(lat=lat, lon=lon, radius_km=radius_km)

    alerts = get_alerts_within_radius(
        session=session,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
    )
    return [FireAlertRead.from_orm_with_risk(alert) for alert in alerts]
