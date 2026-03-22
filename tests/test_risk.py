from app.services.risk import calculate_risk_score, confidence_weight, normalize_brightness


def test_normalize_brightness_clips_range() -> None:
    assert normalize_brightness(250.0) == 0.0
    assert normalize_brightness(550.0) == 1.0


def test_confidence_weight_defaults_when_unknown() -> None:
    assert confidence_weight("high") == 1.0
    assert confidence_weight("unknown") == 0.5


def test_calculate_risk_score_combines_inputs() -> None:
    assert calculate_risk_score(brightness=400.0, confidence="high") == 70.0
