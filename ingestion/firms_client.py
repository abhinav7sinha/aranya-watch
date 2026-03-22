"""NASA FIRMS client utilities."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from io import StringIO

import httpx

from app.core.config import get_settings


@dataclass(slots=True)
class FirmsFireRecord:
    """Normalized NASA FIRMS fire alert record."""

    latitude: float
    longitude: float
    brightness: float
    confidence: str
    acq_datetime: datetime


class FirmsClient:
    """HTTP client for NASA FIRMS area CSV endpoints."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def fetch_fire_alerts(
        self,
        *,
        area: str = "world",
        day_range: int | None = None,
        source: str | None = None,
    ) -> list[FirmsFireRecord]:
        """Fetch and normalize fire alerts from NASA FIRMS."""

        if not self.settings.firms_api_key:
            raise ValueError("FIRMS_API_KEY is required to fetch NASA FIRMS data.")

        dataset = source or self.settings.firms_source
        days = day_range or self.settings.firms_day_range
        url = "/".join(
            [
                self.settings.firms_base_url.rstrip("/"),
                self.settings.firms_api_key,
                dataset,
                area,
                str(days),
            ]
        )

        with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
            response = client.get(url)
            response.raise_for_status()

        return self._parse_csv(response.text)

    def _parse_csv(self, content: str) -> list[FirmsFireRecord]:
        """Parse NASA FIRMS CSV text into normalized records."""

        reader = csv.DictReader(StringIO(content))
        records: list[FirmsFireRecord] = []

        for row in reader:
            acq_date = row.get("acq_date", "")
            acq_time = row.get("acq_time", "")
            if not acq_date or not acq_time:
                continue

            timestamp = self._parse_acq_datetime(acq_date=acq_date, acq_time=acq_time)
            records.append(
                FirmsFireRecord(
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    brightness=float(row.get("brightness", row.get("bright_ti4", 0.0))),
                    confidence=str(row.get("confidence", "nominal")).strip() or "nominal",
                    acq_datetime=timestamp,
                )
            )

        return records

    @staticmethod
    def _parse_acq_datetime(*, acq_date: str, acq_time: str) -> datetime:
        """Convert FIRMS acquisition date and time fields to UTC datetime."""

        padded_time = acq_time.zfill(4)
        parsed = datetime.strptime(f"{acq_date} {padded_time}", "%Y-%m-%d %H%M")
        return parsed.replace(tzinfo=timezone.utc)
