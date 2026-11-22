"""Unit tests for the A/B test functions, using small made-up data (no download needed).

Run with: pytest
"""
import pandas as pd

from ab_test import (bootstrap_difference, clean, engagement_segments,
                     sample_ratio_check, two_proportion_ztest)


def make_df(n_a=1000, n_b=1000, ret_a=0.20, ret_b=0.20):
    rows = []
    for i in range(n_a):
        rows.append({"userid": i, "version": "gate_30", "sum_gamerounds": i % 150,
                     "retention_1": i < n_a * 0.45, "retention_7": i < n_a * ret_a})
    for i in range(n_b):
        rows.append({"userid": n_a + i, "version": "gate_40", "sum_gamerounds": i % 150,
                     "retention_1": i < n_b * 0.45, "retention_7": i < n_b * ret_b})
    return pd.DataFrame(rows)


def test_clean_removes_impossible_outlier():
    df = make_df(10, 10)
    df.loc[0, "sum_gamerounds"] = 49_854
    cleaned, notes = clean(df)
    assert len(cleaned) == 19
    assert "Removed 1 player" in notes[1]


def test_even_split_passes_sample_ratio_check():
    _, p = sample_ratio_check(make_df(1000, 1000))
    assert p > 0.9


def test_uneven_split_fails_sample_ratio_check():
    _, p = sample_ratio_check(make_df(1000, 1300))
    assert p < 0.01


def test_ztest_finds_no_difference_when_rates_are_equal():
    diff, _, p = two_proportion_ztest(make_df(), "retention_7")
    assert diff == 0
    assert p > 0.99


def test_ztest_finds_a_clear_difference():
    diff, _, p = two_proportion_ztest(make_df(ret_a=0.30, ret_b=0.20), "retention_7")
    assert round(diff, 2) == 0.10
    assert p < 0.001


def test_bootstrap_is_repeatable_and_centred_on_the_difference():
    df = make_df(ret_a=0.30, ret_b=0.20)
    first = bootstrap_difference(df, "retention_7", n_boot=200, seed=1)
    second = bootstrap_difference(df, "retention_7", n_boot=200, seed=1)
    assert (first == second).all()
    assert abs(first.mean() - 0.10) < 0.01


def test_segments_cover_every_engagement_group():
    table = engagement_segments(make_df())
    assert list(table.index) == ["0 rounds", "1-10", "11-30", "31-100", "100+"]
    assert list(table.columns) == ["gate_30", "gate_40"]