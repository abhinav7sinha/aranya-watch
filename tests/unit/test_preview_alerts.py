from app.services.preview_alerts import (
    get_preview_alerts_in_bbox,
    get_preview_alerts_within_radius,
    get_recent_preview_alerts,
)


def test_recent_preview_alerts_respects_limit() -> None:
    alerts = get_recent_preview_alerts(limit=2)

    assert len(alerts) == 2
    assert alerts[0].acq_datetime >= alerts[1].acq_datetime


def test_preview_bbox_filtering() -> None:
    alerts = get_preview_alerts_in_bbox(
        min_lat=33.0,
        max_lat=35.0,
        min_lon=-119.0,
        max_lon=-117.0,
    )

    assert len(alerts) == 1
    assert alerts[0].latitude == 34.0522


def test_preview_radius_filtering() -> None:
    alerts = get_preview_alerts_within_radius(lat=39.7392, lon=-104.9903, radius_km=10)

    assert len(alerts) == 1
    assert alerts[0].longitude == -104.9903
