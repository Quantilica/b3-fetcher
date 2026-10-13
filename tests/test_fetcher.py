"""Tests for the B3 COTAHIST source adapter (URL builders)."""

from __future__ import annotations

import pytest

from b3_fetcher.fetcher import (
    build_annual_url,
    build_daily_url,
    build_monthly_url,
    valid_year,
)


def test_build_annual_url():
    assert build_annual_url(2024).endswith("/COTAHIST_A2024.zip")


def test_build_monthly_url_zero_pads_month():
    assert build_monthly_url(2024, 1).endswith("/COTAHIST_M012024.zip")
    assert build_monthly_url(2024, 12).endswith("/COTAHIST_M122024.zip")


def test_build_daily_url_orders_day_month_year():
    assert build_daily_url(2024, 1, 2).endswith("/COTAHIST_D02012024.zip")
    assert build_daily_url(2024, 11, 25).endswith("/COTAHIST_D25112024.zip")


def test_valid_year_accepts_published_range():
    assert valid_year(1986, current_year=2026)
    assert valid_year(2026, current_year=2026)


@pytest.mark.parametrize("year", [1985, 2027])
def test_valid_year_rejects_out_of_range(year):
    assert not valid_year(year, current_year=2026)
