"""Dataset que só recebe 400 da B3 por vários dias úteis seguidos vira erro."""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

import pytest

from b3_fetcher.catalog import list_datasets
from b3_fetcher.constants import MAX_BUSINESS_DAYS_WITHOUT_FILE
from b3_fetcher.plugin import streak_without_file
from b3_fetcher.storage import DataRepository

from .test_a4_download import FakeB3, make_app

D = dt.date


def test_limit_is_five_business_days() -> None:
    assert MAX_BUSINESS_DAYS_WITHOUT_FILE == 5


def test_streak_ignores_weekends_and_needs_the_limit() -> None:
    # seg 2 a sex 6/11/2026: 5 dias úteis; o fim de semana no meio não conta
    week = {D(2026, 11, d) for d in (2, 3, 4, 5, 6)}
    assert streak_without_file(week, set()) == (D(2026, 11, 2), D(2026, 11, 6), 5)
    assert streak_without_file(set(list(sorted(week))[:4]), set()) is None
    # semana + sábado e domingo + segunda: fim de semana não soma dias
    assert streak_without_file({D(2026, 11, 2), D(2026, 11, 3)}, set()) is None
    gap = {D(2026, 11, 5), D(2026, 11, 6), D(2026, 11, 9), D(2026, 11, 10)}
    assert streak_without_file(gap, set()) is None  # 4 úteis (sáb/dom pulados)
    assert streak_without_file(gap | {D(2026, 11, 4)}, set()) == (
        D(2026, 11, 4),
        D(2026, 11, 10),
        5,
    )


def test_streak_counts_from_the_last_local_file() -> None:
    local = {D(2026, 10, 29)}  # quinta
    # sex 30, seg 2, ter 3, qua 4 = 4 úteis: ainda absorvido (feriado)
    assert streak_without_file({D(2026, 11, 4)}, local) is None
    # com a quinta 5: 5 úteis sem arquivo desde 30/10
    assert streak_without_file({D(2026, 11, 5)}, local) == (
        D(2026, 10, 30),
        D(2026, 11, 5),
        5,
    )


def test_streak_cleared_by_a_later_file() -> None:
    week = {D(2026, 11, d) for d in (2, 3, 4, 5, 6)}
    assert streak_without_file(week, {D(2026, 11, 9)}) is None
    assert streak_without_file(set(), set()) is None


def _sync(app, tmp_path: Path, today: dt.date):
    entries = list_datasets("derivativos_agro", today=today)
    return app.download_datasets(entries, tmp_path, workers=2)


def test_sync_one_holiday_is_not_an_error(tmp_path: Path) -> None:
    # 5 úteis até sex 6/11; só a quinta 5 sem arquivo (feriado)
    app = make_app(FakeB3({"2026-11-02", "2026-11-03", "2026-11-04", "2026-11-06"}))
    downloaded, total, errors = _sync(app, tmp_path, D(2026, 11, 6))
    # o 400 isolado conta como entrada concluída (sem arquivo), sem erro
    assert (downloaded, total, errors) == (5, 5, [])
    assert len(list((tmp_path / "derivativos_agro").rglob("*.csv"))) == 4


def test_sync_all_400_for_five_business_days_is_an_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    app = make_app(FakeB3(set()))
    with caplog.at_level(logging.ERROR):
        downloaded, total, errors = _sync(app, tmp_path, D(2026, 11, 6))
    assert total == 5
    assert len(errors) == 1
    group, message = errors[0]
    assert group == "derivativos_agro"
    assert "derivativos_agro" in message
    assert "desde 2026-11-02" in message
    assert "5 dias úteis" in message
    assert any("derivativos_agro" in r.getMessage() for r in caplog.records)
    stats = app.last_download_stats
    assert stats is not None and stats.failed_count == 1
    assert stats.succeeded_count == 4


def test_sync_old_file_plus_new_400s_is_an_error(tmp_path: Path) -> None:
    # janela curta (1 dia): o último arquivo local é de 29/10, hoje é 5/11
    repo = DataRepository(tmp_path)
    old = repo.path_for_daily_entry(
        {"group": "derivativos_agro", "date": "2026-10-29", "year": 2026}
    )
    old.parent.mkdir(parents=True)
    old.write_bytes(b"x")
    old.with_name(old.name + ".manifest.json").write_text("{}")  # não conta
    app = make_app(FakeB3(set()))
    entries = list_datasets("derivativos_agro", today=D(2026, 11, 5))[-1:]
    _, _, errors = app.download_datasets(entries, tmp_path, workers=1)
    assert len(errors) == 1
    assert "desde 2026-10-30" in errors[0][1]


def test_sync_downloads_in_the_same_run_clear_the_streak(tmp_path: Path) -> None:
    # só hoje (6/11) sem arquivo, mas os 4 dias anteriores baixam na mesma rodada
    app = make_app(FakeB3({"2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05"}))
    downloaded, total, errors = _sync(app, tmp_path, D(2026, 11, 6))
    assert (downloaded, total, errors) == (5, 5, [])
