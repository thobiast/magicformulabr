#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script implements Joel Greenblatt's Magic Formula investing strategy for ranking companies
listed on the Bovespa (Brazilian Stock Exchange).

The script fetches financial data from the 'fundamentus.com.br' website, processes
this data to calculate the Magic Formula rankings, and then displays the top-ranked
companies based on the user's selection.
"""

import argparse
import io
import json
import logging
import os
import sys
import time

import pandas as pd
import requests

URL = "http://fundamentus.com.br/resultado.php"
CACHE_FILE = "data_cache.json"
CACHE_DURATION_SECONDS = 86400  # 24 hours


##############################################################################
# Command line parser
##############################################################################
def parse_parameters():
    """Command line parser."""
    epilog = """
    Methods disponiveis:
        1 - P/L e ROE
        2 - EV/EBIT e ROIC
        3 - EV/EBITDA e ROIC

    Exemplos de uso:
        %(prog)s -h
        %(prog)s -m 1
        %(prog)s -v
        %(prog)s -vv
        %(prog)s -m 3 -vv
        %(prog)s -m 3 --top 30 --force-update
    """
    parser = argparse.ArgumentParser(
        description="Gera rank de acoes usando a magic formula",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", dest="debug", help="debug flag"
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="verbosity level"
    )
    parser.add_argument(
        "-m",
        "--method",
        type=int,
        choices=range(1, 4),
        default=2,
        help="Campos usados para o calculo da magic formula",
    )
    parser.add_argument(
        "-t",
        "--top",
        type=int,
        default=20,
        help="Numero de empresas para mostrar no rank",
    )
    parser.add_argument(
        "--force-update",
        action="store_true",
        help="Forca a atualizacao do cache com dados recentes",
    )

    return parser.parse_args()


def setup_logging(log_level=logging.INFO):
    """Setup logging configuration."""
    datefmt = "%Y-%m-%d %H:%M:%S"
    msg_fmt = "%(asctime)s %(module)s - %(funcName)s [%(levelname)s] %(message)s"

    formatter = logging.Formatter(
        fmt=msg_fmt,
        datefmt=datefmt,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)


class DataSourceHandler:
    """
    Class to handle data fetching and caching from the 'fundamentus.com.br' website.
    """

    def __init__(
        self,
        url,
        cache_file=CACHE_FILE,
        cache_duration=CACHE_DURATION_SECONDS,
        force_update=False,
    ):
        """
        Initializes the DataSourceHandler class.

        Parameters:
            url (str): The URL from which to fetch data.
            cache_file (str): Path to the cache file used to store the fetched data.
            cache_duration (int): The duration (in seconds) for which the cache is considered valid.
                                  Defaults to 86400 seconds (24 hours).
            force_update (bool): If True, the cache will be bypassed and data will be fetched
                                 from the URL, updating the existing cache. Defaults to False.
        """
        self.url = url
        self.cache_file = cache_file
        self.cache_duration = cache_duration
        self.force_update = force_update

    def fetch_data(self):
        """
        Downloads data from the specified URL and returns it as a pandas DataFrame.

        Returns:
            pd.DataFrame: The data retrieved from the URL
        """
        headers = {
            "User-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:85.0)"
            "Gecko/20100101 Firefox/85.0",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
        }
        try:
            response = requests.get(self.url, headers=headers, timeout=60)
            response.raise_for_status()
        except requests.RequestException as e:
            logging.error("Failed to fetch data from %s: %s", self.url, e)
            sys.exit(1)

        # Wrap the HTML string in StringIO to avoid deprecation warning.
        html_data = io.StringIO(response.text)
        return pd.read_html(
            html_data,
            thousands=".",
            decimal=",",
            index_col="Papel",
            encoding="utf-8",
        )[0]

    def is_cache_valid(self):
        """
        Checks if the existing cache file is valid based on its age.

        Returns:
            bool: True if the cache is valid, False otherwise.
        """
        if not os.path.exists(self.cache_file):
            logging.debug("Cache file '%s' does not exist.", self.cache_file)
            return False

        cache_age = time.time() - os.path.getmtime(self.cache_file)

        if cache_age > self.cache_duration:
            logging.debug("Cache is outdated (age: %.2f seconds).", cache_age)
            return False

        logging.debug("Cache is valid (age: %.2f seconds).", cache_age)
        return True

    def load_from_cache(self):
        """
        Loads data from the cache file into a pandas DataFrame.

        Returns:
            pd.DataFrame: The data loaded from the cache file
        """
        with open(self.cache_file, "r", encoding="utf-8") as file:
            data = json.load(file)
        return pd.DataFrame.from_dict(data)

    def save_to_cache(self, pd_df):
        """
        Saves the provided DataFrame to the cache file.

        Serializes the given DataFrame and writes it to the cache file.

        Parameters:
            pd_df (pd.DataFrame): The DataFrame to be cached.
        """
        with open(self.cache_file, "w", encoding="utf-8") as file:
            json.dump(pd_df.to_dict(), file)

    def get_data(self):
        """
        Retrieves data from the cache if valid, or fetches from the URL and updates the cache.

        Returns:
            pd.DataFrame: The data retrieved from the cache or downloaded from the URL.
        """
        if self.force_update or not self.is_cache_valid():
            logging.debug("Force updating or cache is invalid. Downloading new data.")
            pd_df = self.fetch_data()
            if pd_df.empty:
                logging.error("Fetched data is empty. Exiting.")
                sys.exit(1)
            self.save_to_cache(pd_df)
            return pd_df

        logging.debug("Loading data from cache.")
        return self.load_from_cache()


class MagicFormula:
    """
    A class that implements Joel Greenblatt's Magic Formula for ranking companies.

    The Magic Formula ranks companies by combining their earnings yield and return on capital.
    This class processes a DataFrame containing financial data of companies, applies the formula,
    and ranks the companies.
    """

    # MAGIC_METHOD_FIELD is a dictionary mapping method identifiers to their respective
    # financial metrics used in the Magic Formula calculation. Each method identifier
    # corresponds to a different set of financial metrics:
    #   - 1: Uses 'P/L' for earnings yield and 'ROE' for return on capital.
    #   - 2: Uses 'EV/EBIT' for earnings yield and 'ROIC' for return on capital.
    #   - 3: Uses 'EV/EBITDA' for earnings yield and 'ROIC' for return on capital.
    # These mappings allow for flexibility in defining which financial metrics are used in
    # the calculationof the Magic Formula, accommodating different variations of the formula.
    MAGIC_METHOD_FIELD = {
        1: {"earnings yield": "P/L", "return on capital": "ROE"},
        2: {"earnings yield": "EV/EBIT", "return on capital": "ROIC"},
        3: {"earnings yield": "EV/EBITDA", "return on capital": "ROIC"},
    }

    def __init__(self, pd_df, magic_method):
        """
        Initializes the MagicFormula class with financial data and the chosen method
        for calculation.

        Parameters:
            pd_df (pandas.DataFrame): The financial data of companies.
            magic_method (int): Specifies the method used for calculating the Magic Formula ranking.
                                 It determines which financial metrics are used for earnings yield
                                 and return on capital calculations.
        """
        self.pd_df = pd_df
        self.earnings_yield = self.MAGIC_METHOD_FIELD[magic_method]["earnings yield"]
        self.ret_on_capital = self.MAGIC_METHOD_FIELD[magic_method]["return on capital"]

    @staticmethod
    def pct_to_float(number):
        """
        Converts a percentage string to a float value.

        Convert string to float, remove % char and set decimal point to '.'.
        """
        return float(number.strip("%").replace(".", "").replace(",", "."))

    def _apply_converters(self):
        """
        Converts specific columns in `pd_df` to the necessary data type or format.
        """
        converters = {self.ret_on_capital: self.pct_to_float}
        for column, converter in converters.items():
            if column in self.pd_df.columns:
                self.pd_df[column] = self.pd_df[column].apply(converter)

    def _remove_rows(self, col_name, min_value):
        """
        Removes rows from `pd_df` where the value in the specified column is
        below the given minimum value.

        Parameters:
            col_name (str): The name of the column to evaluate for removal.
            min_value (int or float): The threshold below which rows will be removed.
        """
        logging.debug("Removing companies with %s less than %s", col_name, min_value)
        tickers = self.pd_df.loc[self.pd_df[col_name] <= min_value].index
        logging.debug(self.pd_df.loc[tickers])
        self.pd_df.drop(tickers, inplace=True)

    def _filter_data(self):
        """
        Removes rows in `pd_df` with negative or undesirable values for key financial metrics.

        Filters out companies with non-positive earnings yield, return on capital, and Liq.2meses.
        """
        self._remove_rows(self.earnings_yield, 0)
        self._remove_rows(self.ret_on_capital, 0)
        self._remove_rows("Liq.2meses", 0)

    def _calculate_rank(self):
        """
        Calculates the Magic Formula ranking for companies in `pd_df`.

        Adds ranking columns to `pd_df` based on the earnings yield and return on capital,
        then calculates a final rank.
        """
        if self.pd_df.empty:
            return self.pd_df

        self.pd_df["Rank_earnings_yield"] = self.pd_df[self.earnings_yield].rank(
            ascending=True, method="min"
        )
        self.pd_df["Rank_return_on_capital"] = self.pd_df[self.ret_on_capital].rank(
            ascending=False, method="min"
        )
        self.pd_df["Rank_Final"] = (
            self.pd_df["Rank_earnings_yield"] + self.pd_df["Rank_return_on_capital"]
        )
        self.pd_df.sort_values(by="Rank_Final", ascending=True, inplace=True)

        return self.pd_df

    def process(self):
        """
        Executes the full Magic Formula process: conversion, filtering, and ranking.
        """
        self._apply_converters()
        self._filter_data()
        df_ranked = self._calculate_rank()
        return df_ranked


def display_results(df, args):
    """
    Displays the top-ranked companies according to verbosity.

    Parameters:
        df (pd.DataFrame):
            The ranked DataFrame produced by `MagicFormula.calc_rank()`.
        args (argparse.Namespace):
            Parsed command-line arguments containing:
                - method (int): Magic Formula method (1, 2, or 3) to determine key columns.
                - verbose (int): Verbosity level (0, 1, or >=2) to control displayed columns.
                - top (int): Number of companies to display.
    """
    df_display = df.copy()

    base_cols = ["Rank_earnings_yield", "Rank_return_on_capital", "Rank_Final"]

    magic_method_cols = MagicFormula.MAGIC_METHOD_FIELD[args.method]
    earnings_yield_col = magic_method_cols["earnings yield"]
    return_on_capital_col = magic_method_cols["return on capital"]

    if args.verbose == 0:
        keep_cols = [earnings_yield_col, return_on_capital_col] + base_cols
    elif args.verbose == 1:
        keep_cols = [
            "Cotação",
            "Div.Yield",
            "ROIC",
            "ROE",
            "P/L",
            "EV/EBIT",
            "EV/EBITDA",
            earnings_yield_col,
            return_on_capital_col,
        ] + base_cols
    else:
        keep_cols = df_display.columns.tolist()

    # Remove duplicates preserving order
    keep_cols = list(dict.fromkeys(keep_cols))

    df_display.reset_index(inplace=True, names="Ticker")
    df_display.index = df_display.index + 1
    print(df_display.head(args.top).to_string(columns=["Ticker"] + keep_cols))


##############################################################################
# Main function
##############################################################################
def main():
    """Command line execution."""

    # Parser the command line
    args = parse_parameters()

    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)

    logging.debug("CMD line args: %s", vars(args))

    data_handler = DataSourceHandler(URL, force_update=args.force_update)
    pd_df = data_handler.get_data()

    magicformula = MagicFormula(pd_df, args.method)
    ranked_df = magicformula.process()
    if ranked_df.empty:
        print("No companies passed the filtering criteria. The ranking is empty.")
    else:
        display_results(ranked_df, args)


##############################################################################
# Run from command line
##############################################################################
if __name__ == "__main__":
    main()

# vim: ts=4
