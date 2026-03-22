"""Risk scoring heuristics for fire alerts."""


CONFIDENCE_WEIGHTS = {
    "low": 0.4,
    "nominal": 0.7,
    "high": 1.0,
    "l": 0.4,
    "n": 0.7,
    "h": 1.0,
}


def normalize_brightness(brightness: float) -> float:
    """Normalize brightness onto a 0-1 scale with simple clipping."""

    min_brightness = 300.0
    max_brightness = 500.0
    normalized = (brightness - min_brightness) / (max_brightness - min_brightness)
    return max(0.0, min(1.0, normalized))


def confidence_weight(confidence: str) -> float:
    """Map confidence labels into a numeric weight."""

    return CONFIDENCE_WEIGHTS.get(confidence.strip().lower(), 0.5)


def calculate_risk_score(brightness: float, confidence: str) -> float:
    """Compute a simple 0-100 risk score."""

    score = (normalize_brightness(brightness) * 0.6) + (confidence_weight(confidence) * 0.4)
    return round(score * 100, 2)
