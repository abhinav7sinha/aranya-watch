"""Live NASA FIRMS access for India-focused experiences."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from app.models.schemas import FireAlertRead
from app.services.risk import calculate_risk_score
from ingestion.firms_client import FirmsClient, FirmsFireRecord

INDIA_FETCH_BBOX = "67.5,6.0,98.5,37.7"
DEFAULT_LIVE_SOURCES = ("VIIRS_NOAA21_NRT", "VIIRS_NOAA20_NRT", "VIIRS_SNPP_NRT")

# These polygons are deliberately approximate. FIRMS gives us bbox queries, so
# we trim the results with a second pass to keep the India visualizer focused.
INDIA_MAINLAND_POLYGON: tuple[tuple[float, float], ...] = (
    (68.0, 24.0),
    (68.5, 17.0),
    (69.0, 8.2),
    (77.8, 6.0),
    (80.5, 8.0),
    (85.4, 14.0),
    (88.8, 20.5),
    (89.6, 22.5),
    (88.4, 26.9),
    (80.7, 33.8),
    (74.2, 37.3),
    (71.6, 35.0),
    (72.6, 29.0),
)
INDIA_NORTHEAST_POLYGON: tuple[tuple[float, float], ...] = (
    (88.0, 22.2),
    (89.3, 21.8),
    (92.6, 23.2),
    (97.4, 27.4),
    (95.4, 29.8),
    (91.0, 28.6),
    (88.4, 26.2),
)
ANDAMAN_NICOBAR_BBOX = (6.0, 14.8, 92.0, 94.6)
LAKSHADWEEP_BBOX = (8.0, 12.8, 71.0, 74.0)


def _point_in_polygon(lon: float, lat: float, polygon: Iterable[tuple[float, float]]) -> bool:
    """Return True when a point falls inside a polygon."""

    vertices = list(polygon)
    inside = False
    previous_lon, previous_lat = vertices[-1]
    for current_lon, current_lat in vertices:
        intersects = (current_lat > lat) != (previous_lat > lat)
        if intersects:
            intersect_lon = (previous_lon - current_lon) * (lat - current_lat) / (
                (previous_lat - current_lat) or 1e-12
            ) + current_lon
            if lon < intersect_lon:
                inside = not inside
        previous_lon, previous_lat = current_lon, current_lat
    return inside


def is_in_india_focus(latitude: float, longitude: float) -> bool:
    """Return True when a detection sits inside the India-focused product view."""

    if _point_in_polygon(longitude, latitude, INDIA_MAINLAND_POLYGON):
        return True
    if _point_in_polygon(longitude, latitude, INDIA_NORTHEAST_POLYGON):
        return True

    min_lat, max_lat, min_lon, max_lon = ANDAMAN_NICOBAR_BBOX
    if min_lat <= latitude <= max_lat and min_lon <= longitude <= max_lon:
        return True

    min_lat, max_lat, min_lon, max_lon = LAKSHADWEEP_BBOX
    return min_lat <= latitude <= max_lat and min_lon <= longitude <= max_lon


def _to_read_model(record: FirmsFireRecord) -> FireAlertRead:
    """Convert a FIRMS record to the public API shape."""

    return FireAlertRead.model_validate(
        {
            "id": uuid4(),
            "latitude": record.latitude,
            "longitude": record.longitude,
            "brightness": record.brightness,
            "confidence": record.confidence,
            "acq_datetime": record.acq_datetime,
            "created_at": datetime.now(timezone.utc),
            "risk_score": calculate_risk_score(
                brightness=record.brightness,
                confidence=record.confidence,
            ),
        }
    )


def fetch_india_live_alerts(
    *,
    day_range: int = 3,
    limit: int = 1500,
    source: str | None = None,
    query_date: date | None = None,
) -> dict[str, object]:
    """Fetch live NASA FIRMS detections for an India-shaped view."""

    client = FirmsClient()
    sources = (source,) if source else DEFAULT_LIVE_SOURCES
    candidate_dates = [query_date] if query_date else [date.today() - timedelta(days=offset) for offset in range(0, 7)]

    for dataset in sources:
        for candidate_date in candidate_dates:
            alerts = client.fetch_fire_alerts(
                area=INDIA_FETCH_BBOX,
                day_range=day_range,
                source=dataset,
                query_date=candidate_date,
            )
            filtered = [
                _to_read_model(record)
                for record in alerts
                if is_in_india_focus(latitude=record.latitude, longitude=record.longitude)
            ]
            filtered.sort(key=lambda alert: alert.acq_datetime, reverse=True)
            if filtered:
                return {
                    "mode": "live_nasa",
                    "source": dataset,
                    "day_range": day_range,
                    "date": candidate_date.isoformat(),
                    "filter": "india_focus_polygon",
                    "alert_count": len(filtered),
                    "alerts": filtered[:limit],
                }

    return {
        "mode": "live_nasa",
        "source": source or DEFAULT_LIVE_SOURCES[0],
        "day_range": day_range,
        "date": query_date.isoformat() if query_date else date.today().isoformat(),
        "filter": "india_focus_polygon",
        "alert_count": 0,
        "alerts": [],
    }
