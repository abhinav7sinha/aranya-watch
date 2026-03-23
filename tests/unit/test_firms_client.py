from ingestion.firms_client import FirmsClient


def test_parse_csv_normalizes_expected_fields() -> None:
    content = """latitude,longitude,brightness,confidence,acq_date,acq_time
34.123,-118.456,345.5,high,2026-03-20,0315
"""
    client = FirmsClient()

    records = client._parse_csv(content)

    assert len(records) == 1
    record = records[0]
    assert record.latitude == 34.123
    assert record.longitude == -118.456
    assert record.brightness == 345.5
    assert record.confidence == "high"
    assert record.acq_datetime.isoformat() == "2026-03-20T03:15:00+00:00"
