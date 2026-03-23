# NASA FIRMS API Guide

This guide turns the FIRMS web pages into a practical reference for `aranya-watch`.

It focuses on the parts we actually need for ingestion, testing, and debugging:

- getting a `MAP_KEY`
- fetching hotspot data with the `area` API
- checking date coverage with `data_availability`
- understanding optional KML footprint downloads
- watching for missing-data dates that can explain gaps

## What FIRMS Provides

NASA FIRMS exposes wildfire detection data from multiple satellite products. The main data delivery pattern is simple:

1. choose a sensor product
2. choose an area or region
3. choose a day range
4. optionally choose a start date
5. download CSV or KML

For `aranya-watch`, the primary endpoint is the CSV `area` API using:

- `VIIRS_SNPP_NRT`

That is the Suomi-NPP VIIRS near real-time feed and is the source currently used in the ingestion pipeline.

## Main FIRMS Services

| Service | What it does | Notes |
| --- | --- | --- |
| `area` | Fire hotspot detections for a bounding box or `world` in CSV | Primary service for `aranya-watch` |
| `data_availability` | Tells you what dates are available for each product | Useful before historical backfills |
| `kml_fire_footprints` | KML fire points and footprint downloads by region | Good for GIS/manual inspection |
| `map_key` | Request or manage a FIRMS API key | Required for API use |
| `missing_dates` | Shows dates where FIRMS knows data is missing | Useful when debugging gaps |
| `countries` / `country` | Country-based endpoints | Marked as not currently available in the FIRMS UI |

## Authentication

FIRMS uses a `MAP_KEY`.

You request it from the FIRMS site and it is sent to your email. In this codebase, we store that key as:

- `FIRMS_API_KEY`

Even though our env var is named `FIRMS_API_KEY`, the NASA pages call it `MAP_KEY`.

## 1. Area API

This is the most important endpoint for `aranya-watch`.

### URL Pattern

Most recent data:

```text
/api/area/csv/[MAP_KEY]/[SOURCE]/[AREA_COORDINATES]/[DAY_RANGE]
```

Date-based query:

```text
/api/area/csv/[MAP_KEY]/[SOURCE]/[AREA_COORDINATES]/[DAY_RANGE]/[DATE]
```

### What It Returns

CSV hotspot detections for:

- a bounding box, or
- the literal area value `world`

### Area Format

Use either:

- `world`
- `west,south,east,north`

Example:

```text
-85,-57,-32,14
```

Important:

- FIRMS expects a bounding box string, not named fields like `north=...`
- max world extent is `-180,-90,180,90`

### Day Range

Allowed values:

- `1` to `5`

Without a `DATE`, FIRMS returns the most recent data window:

- from today
- for `DAY_RANGE` days back/through the current availability window described by FIRMS

With a `DATE`, FIRMS returns:

- `[DATE]` through `[DATE + DAY_RANGE - 1]`

### Supported Sources Shown In FIRMS

- `LANDSAT_NRT`
- `MODIS_NRT`
- `MODIS_SP`
- `VIIRS_NOAA20_NRT`
- `VIIRS_NOAA20_SP`
- `VIIRS_NOAA21_NRT`
- `VIIRS_SNPP_NRT`
- `VIIRS_SNPP_SP`

For this project, the active source is:

- `VIIRS_SNPP_NRT`

### Example URLs

World, latest 1 day:

```text
/api/area/csv/[MAP_KEY]/VIIRS_SNPP_NRT/world/1
```

World, latest 3 days:

```text
/api/area/csv/[MAP_KEY]/VIIRS_SNPP_NRT/world/3
```

Specific bounding box, specific date:

```text
/api/area/csv/[MAP_KEY]/VIIRS_SNPP_NRT/-125,24,-66,49/1/2026-03-20
```

### Practical Notes For aranya-watch

- Use `world` for the simplest ingestion flow
- Use a bounding box for smaller regional tests
- Keep `DAY_RANGE` small to reduce duplicate ingest volume
- For scheduled MVP ingestion, `1` day is a good default

## 2. Data Availability API

This endpoint helps answer:

- is the product available yet?
- what date ranges can I safely query?

### URL Pattern

```text
/api/data_availability/csv/[MAP_KEY]/[SENSOR]
```

### Supported Sensor Values

- `ALL`
- `LANDSAT_NRT`
- `MODIS_NRT`
- `MODIS_SP`
- `VIIRS_NOAA20_NRT`
- `VIIRS_NOAA20_SP`
- `VIIRS_NOAA21_NRT`
- `VIIRS_SNPP_NRT`
- `VIIRS_SNPP_SP`

### Example

```text
/api/data_availability/csv/[MAP_KEY]/ALL
```

### When To Use It

Use this before:

- historical backfills
- date-specific test runs
- investigating an unexpectedly empty result set

## 3. KML Fire Footprints API

This endpoint is useful for visualization or GIS workflows rather than backend ingestion.

### URL Patterns

Path style:

```text
/api/kml_fire_footprints/[REGION]/[DATE_SPAN]/[SENSOR]
```

Query-string style:

```text
/api/kml_fire_footprints/?region=[REGION]&date_span=[DATE_SPAN]&sensor=[SENSOR]
```

### Regions

- `canada`
- `alaska`
- `usa_contiguous_and_hawaii`
- `central_america`
- `south_america`
- `europe`
- `northern_and_central_africa`
- `southern_africa`
- `russia_asia`
- `south_asia`
- `southeast_asia`
- `australia_newzealand`

### Date Spans

- `24h`
- `48h`
- `72h`
- `7d`

### Sensors

- `c6.1`
- `landsat`
- `suomi-npp-viirs-c2`
- `noaa-20-viirs-c2`
- `noaa-21-viirs-c2`

### Best Use

Use this when you want:

- a map-ready file
- a manual visual QA layer
- quick comparison against the API data you ingested

## 4. Missing Dates Reference

The FIRMS `missing_dates` page lists dates where data is missing from their database.

This is extremely useful when you see:

- no detections for a date you expected
- strange gaps in one sensor but not another
- differences between standard processing and near-real-time data

### Why It Matters

Before assuming your ingestion job or database is broken, check whether FIRMS itself lists that date as missing.

## 5. Real-Time, Ultra Real-Time, and NRT

The FIRMS pages make an important distinction:

- `URT` = Ultra Real-Time
- `RT` = Real-Time
- `NRT` = Near Real-Time

NASA says:

- real-time data is typically available within 60 minutes of overpass
- ultra real-time can be much faster

FIRMS also notes:

- RT and URT data are removed once corresponding NRT detections are processed
- RT/URT data older than 6 hours may be removed

### Practical Meaning

If counts shift slightly over time, that can be normal. Near-real-time feeds may stabilize after the first release window.

## 6. Recommended Testing Workflow For aranya-watch

### Basic Connectivity Test

1. confirm your `MAP_KEY` works
2. call `data_availability`
3. call `area` for `world/1`
4. inspect the CSV

### Suggested Sequence

1. Check availability:

```text
/api/data_availability/csv/[MAP_KEY]/VIIRS_SNPP_NRT
```

2. Pull latest sample data:

```text
/api/area/csv/[MAP_KEY]/VIIRS_SNPP_NRT/world/1
```

3. Test a bounded region:

```text
/api/area/csv/[MAP_KEY]/VIIRS_SNPP_NRT/-125,24,-66,49/1
```

4. If a date looks empty, inspect FIRMS missing-date information

## 7. How This Maps To The Current Codebase

Current ingestion code:

- [firms_client.py](/Users/abhinavsinha/Documents/github-projects/aranya-watch/ingestion/firms_client.py)
- [ingest_fire_alerts.py](/Users/abhinavsinha/Documents/github-projects/aranya-watch/ingestion/ingest_fire_alerts.py)

Current assumptions in `aranya-watch`:

- source: `VIIRS_SNPP_NRT`
- area default: `world`
- day range default: `1`
- format: CSV

Normalized fields used by the MVP:

- `latitude`
- `longitude`
- `brightness`
- `confidence`
- `acq_datetime`

## 8. Common Gotchas

- `MAP_KEY` is required for the API
- `DAY_RANGE` is limited to `1..5`
- `world` is valid, but named directions are not
- some country-based features are currently unavailable
- empty responses can be caused by date availability, not just code bugs
- NRT data can shift as RT/URT detections are replaced
- KML endpoints are useful for QA, but the CSV `area` API is the ingestion workhorse

## 9. Recommended Future Utilities

Useful test helpers we can add next:

- `scripts/test_firms_area.sh`
  to hit the `area` API with your `MAP_KEY`
- `scripts/test_firms_availability.sh`
  to check product availability quickly
- `scripts/test_firms_bbox.sh`
  to test a known bounding box
- `scripts/ingest_smoke_test.sh`
  to fetch a small payload and validate parsing before database insert

## 10. aranya-watch Test Utilities

This repository now includes simple live-test wrappers:

- `scripts/test_firms_availability.sh`
- `scripts/test_firms_area.sh`
- `scripts/test_firms_bbox.sh`
- `scripts/test_firms_kml.sh`

These utilities:

- read `FIRMS_API_KEY` from `.env`
- print a terminal-friendly response preview
- redact the real key in printed URLs as `[MAP_KEY]`
