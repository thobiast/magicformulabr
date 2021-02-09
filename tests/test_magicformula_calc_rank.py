# -*- coding: utf-8 -*-
"""Test calc_rank method."""

import pytest
from unittest.mock import patch
import pandas as pd
from src import magicformulabr


@pytest.fixture
def pd_df():
    d = {"EV/EBIT": [0.2, 8, 4, 2], "ROIC": [10, 60, 40, 90]}
    df = pd.DataFrame(data=d, index=["AAAA3", "BBBB3", "CCCC3", "DDDD4"])
    return df


def test_calc_rank_metod_2(pd_df):
    expected_result = """\
       EV/EBIT  ROIC  Rank_earnings_yield  Rank_return_on_capital  Rank_Final
DDDD4      2.0    90                  2.0                     1.0         3.0
AAAA3      0.2    10                  1.0                     4.0         5.0
BBBB3      8.0    60                  4.0                     2.0         6.0
CCCC3      4.0    40                  3.0                     3.0         6.0"""

    magic_formula = magicformulabr.MagicFormula(magic_method="2")
    with patch.object(magic_formula, "pd_df", pd_df):
        magic_formula.calc_rank()
        assert magic_formula.pd_df.to_string() == expected_result
