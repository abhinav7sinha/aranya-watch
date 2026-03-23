from app.core.config import get_settings
from scripts.firms_api import FirmsApiHelper


def test_build_area_url_uses_expected_pattern(monkeypatch) -> None:
    monkeypatch.setenv("FIRMS_API_KEY", "test-map-key")
    get_settings.cache_clear()
    helper = FirmsApiHelper()
    settings = get_settings()

    url = helper.build_area_url(
        source="VIIRS_SNPP_NRT",
        area="world",
        day_range=1,
        date="2026-03-20",
    )

    assert url == (
        f"{settings.firms_base_url}/{settings.firms_api_key}/VIIRS_SNPP_NRT/world/1/2026-03-20"
    )
    get_settings.cache_clear()


def test_build_data_availability_url_uses_expected_pattern(monkeypatch) -> None:
    monkeypatch.setenv("FIRMS_API_KEY", "test-map-key")
    get_settings.cache_clear()
    helper = FirmsApiHelper()
    settings = get_settings()

    url = helper.build_data_availability_url(sensor="ALL")

    assert url == f"https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/{settings.firms_api_key}/ALL"
    get_settings.cache_clear()
