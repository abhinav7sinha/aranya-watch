#!/usr/bin/env python3
"""Command-line utilities for testing NASA FIRMS endpoints."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import get_settings


@dataclass(frozen=True)
class ResponsePreview:
    """Small response summary for terminal-friendly output."""

    url: str
    status_code: int
    content_type: str
    body: str


def redact_map_key(value: str, map_key: str) -> str:
    """Hide the FIRMS key in printed terminal output."""

    return value.replace(map_key, "[MAP_KEY]")


class FirmsApiHelper:
    """Build and fetch FIRMS API URLs for local testing."""

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def map_key(self) -> str:
        """Return the configured FIRMS key or fail clearly."""

        if not self.settings.firms_api_key:
            raise ValueError("FIRMS_API_KEY is required. Set it in .env before using FIRMS test utilities.")
        return self.settings.firms_api_key

    def build_area_url(
        self,
        *,
        source: str,
        area: str,
        day_range: int,
        date: str | None = None,
    ) -> str:
        """Build an area CSV URL."""

        parts = [
            self.settings.firms_base_url.rstrip("/"),
            self.map_key,
            source,
            area,
            str(day_range),
        ]
        if date:
            parts.append(date)
        return "/".join(parts)

    def build_data_availability_url(self, *, sensor: str) -> str:
        """Build a data-availability CSV URL."""

        return "/".join(
            [
                "https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv",
                self.map_key,
                sensor,
            ]
        )

    def build_kml_footprints_url(self, *, region: str, date_span: str, sensor: str) -> str:
        """Build a KML fire-footprints URL."""

        return "/".join(
            [
                "https://firms.modaps.eosdis.nasa.gov/api/kml_fire_footprints",
                region,
                date_span,
                sensor,
            ]
        )

    def fetch_preview(self, url: str, *, max_lines: int = 20) -> ResponsePreview:
        """Fetch a URL and return a compact response preview."""

        import httpx

        with httpx.Client(timeout=self.settings.request_timeout_seconds, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()

        lines = response.text.splitlines()
        preview = "\n".join(lines[:max_lines]) if lines else response.text[:1000]
        return ResponsePreview(
            url=str(response.url),
            status_code=response.status_code,
            content_type=response.headers.get("content-type", ""),
            body=preview,
        )

    def download(self, url: str, *, output_path: Path) -> ResponsePreview:
        """Fetch a URL and save it to disk."""

        import httpx

        with httpx.Client(timeout=self.settings.request_timeout_seconds, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)
        return ResponsePreview(
            url=str(response.url),
            status_code=response.status_code,
            content_type=response.headers.get("content-type", ""),
            body=f"Saved response to {output_path}",
        )


def build_parser() -> argparse.ArgumentParser:
    """Build the FIRMS utility CLI parser."""

    parser = argparse.ArgumentParser(description="Utilities for testing NASA FIRMS endpoints.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    area = subparsers.add_parser("area", help="Fetch area CSV data.")
    area.add_argument("--source", default="VIIRS_SNPP_NRT")
    area.add_argument("--area", default="world", help="Bounding box west,south,east,north or world.")
    area.add_argument("--days", type=int, default=1)
    area.add_argument("--date", default=None, help="Optional start date YYYY-MM-DD.")
    area.add_argument("--print-url-only", action="store_true")
    area.add_argument("--save", default=None, help="Optional file path to save the full response.")

    availability = subparsers.add_parser("availability", help="Fetch data availability CSV.")
    availability.add_argument("--sensor", default="VIIRS_SNPP_NRT")
    availability.add_argument("--print-url-only", action="store_true")
    availability.add_argument("--save", default=None, help="Optional file path to save the full response.")

    kml = subparsers.add_parser("kml", help="Fetch KML fire footprints.")
    kml.add_argument("--region", default="usa_contiguous_and_hawaii")
    kml.add_argument("--date-span", default="24h", choices=["24h", "48h", "72h", "7d"])
    kml.add_argument(
        "--sensor",
        default="suomi-npp-viirs-c2",
        choices=["c6.1", "landsat", "suomi-npp-viirs-c2", "noaa-20-viirs-c2", "noaa-21-viirs-c2"],
    )
    kml.add_argument("--print-url-only", action="store_true")
    kml.add_argument("--save", default="tmp/firms-fire-footprints.kml")

    return parser


def emit_preview(preview: ResponsePreview) -> None:
    """Print a human-readable response summary."""

    helper = FirmsApiHelper()
    print(f"URL: {redact_map_key(preview.url, helper.map_key)}")
    print(f"Status: {preview.status_code}")
    print(f"Content-Type: {preview.content_type}")
    print()
    print(preview.body)


def main() -> None:
    """CLI entrypoint."""

    args = build_parser().parse_args()
    helper = FirmsApiHelper()

    if args.command == "area":
        url = helper.build_area_url(source=args.source, area=args.area, day_range=args.days, date=args.date)
    elif args.command == "availability":
        url = helper.build_data_availability_url(sensor=args.sensor)
    else:
        url = helper.build_kml_footprints_url(region=args.region, date_span=args.date_span, sensor=args.sensor)

    if args.print_url_only:
        print(url)
        return

    save_path = getattr(args, "save", None)
    preview = (
        helper.download(url, output_path=Path(save_path))
        if save_path
        else helper.fetch_preview(url)
    )
    emit_preview(preview)


if __name__ == "__main__":
    main()
