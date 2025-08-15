# -*- coding: utf-8 -*-
"""Test calc_rank method."""

import pandas as pd
import pytest

from magicformulabr.main import MagicFormula


@pytest.fixture(name="sample_df", scope="function")
def _sample_df():
    """Create fake dataframe."""
    dic_com = {"EV/EBIT": [0.2, 8, 4, 2], "ROIC": [10, 60, 40, 90]}
    my_df = pd.DataFrame(data=dic_com, index=["AAAA3", "BBBB3", "CCCC3", "DDDD4"])
    return my_df


def test_calc_rank_method_2(sample_df):
    """Test calc_rank method."""
    expected_result = """\
       EV/EBIT  ROIC  Rank_earnings_yield  Rank_return_on_capital  Rank_Final
DDDD4      2.0    90                  2.0                     1.0         3.0
AAAA3      0.2    10                  1.0                     4.0         5.0
BBBB3      8.0    60                  4.0                     2.0         6.0
CCCC3      4.0    40                  3.0                     3.0         6.0"""

    magic_formula = MagicFormula(sample_df, magic_method=2)
    pd_df = magic_formula._calculate_rank()  # pylint: disable=protected-access
    assert pd_df.to_string() == expected_result
