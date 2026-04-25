from typing import Final


VALID_SCENARIOS: Final = ("steady", "burst", "elephant", "ramp")


def extra_offered_load(t: float, scenario: str, capacity: float) -> float:
    """Return extra background load in Mbps for the selected scenario."""

    if scenario == "steady":
        return 0.0
    if scenario == "burst":
        return 0.8 * capacity if 25.0 <= t <= 35.0 else 0.0
    if scenario == "elephant":
        return 1.2 * capacity if t >= 15.0 else 0.0
    if scenario == "ramp":
        return min(t / 40.0, 1.5) * capacity
    raise ValueError(f"Unknown scenario: {scenario}")
