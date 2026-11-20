"""V11: amounts on the Reports chart axis use thousands separators."""

from __future__ import annotations

import pytest

from ui.formatting import format_axis_amount


@pytest.mark.parametrize(
    "value, language, expected",
    [
        (350000, "es", "350.000"),
        (350000, "en", "350,000"),
        (0, "es", "0"),
        (999.6, "es", "1.000"),
        (1234567, "en", "1,234,567"),
        (-50000, "es", "-50.000"),
        (-0.2, "es", "0"),
        (None, "es", ""),
        ("abc", "en", ""),
    ],
)
def test_format_axis_amount(value, language, expected):
    assert format_axis_amount(value, language) == expected
