"""CLI for ingesting NASA FIRMS fire alerts into PostGIS."""

from __future__ import annotations

import argparse
import logging

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.fire_alert import FireAlert
from ingestion.firms_client import FirmsClient, FirmsFireRecord

logger = logging.getLogger("aranya_watch.ingestion")


def configure_logging() -> None:
    """Configure logging for the ingestion CLI."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Ingest NASA FIRMS fire alerts.")
    parser.add_argument("--area", default="world", help="FIRMS area identifier, for example world.")
    parser.add_argument("--days", type=int, default=1, help="Number of trailing days to fetch.")
    parser.add_argument(
        "--source",
        default="VIIRS_SNPP_NRT",
        help="NASA FIRMS dataset, for example VIIRS_SNPP_NRT.",
    )
    return parser.parse_args()


def alert_exists(session, record: FirmsFireRecord) -> bool:
    """Check whether an alert already exists for the same location and acquisition time."""

    statement = select(FireAlert.id).where(
        FireAlert.latitude == record.latitude,
        FireAlert.longitude == record.longitude,
        FireAlert.acq_datetime == record.acq_datetime,
    )
    return session.execute(statement).scalar_one_or_none() is not None


def build_fire_alert(record: FirmsFireRecord) -> FireAlert:
    """Create an ORM object from a normalized FIRMS record."""

    return FireAlert(
        latitude=record.latitude,
        longitude=record.longitude,
        brightness=record.brightness,
        confidence=record.confidence,
        acq_datetime=record.acq_datetime,
        geom=WKTElement(f"POINT({record.longitude} {record.latitude})", srid=4326),
    )


def ingest_fire_alerts(*, area: str, days: int, source: str) -> tuple[int, int]:
    """Fetch, deduplicate, and insert NASA FIRMS fire alerts."""

    init_db()
    client = FirmsClient()
    records = client.fetch_fire_alerts(area=area, day_range=days, source=source)
    inserted = 0
    skipped = 0

    with SessionLocal() as session:
        for record in records:
            if alert_exists(session, record):
                skipped += 1
                continue

            session.add(build_fire_alert(record))
            try:
                session.commit()
                inserted += 1
            except IntegrityError:
                session.rollback()
                skipped += 1

    logger.info("Ingestion complete. inserted=%s skipped=%s total=%s", inserted, skipped, len(records))
    return inserted, skipped


def main() -> None:
    """CLI entrypoint."""

    configure_logging()
    args = parse_args()
    ingest_fire_alerts(area=args.area, days=args.days, source=args.source)


if __name__ == "__main__":
    main()
