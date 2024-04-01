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
import json
import logging
import os
import time

import pandas as pd
import requests

URL = "http://fundamentus.com.br/resultado.php"


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


def setup_logging(logfile=None, *, filemode="a", date_format=None, log_level="DEBUG"):
    """
    Configure logging.

    Arguments (opt):
        logfile     (str): log file to write the log messages
                               If not specified, it shows log messages
                               on screen (stderr)
    Keyword arguments (opt):
        filemode    (a/w): a - log messages are appended to the file (default)
                           w - log messages overwrite the file
        date_format (str): date format in strftime format
                           default is %m/%d/%Y %H:%M:%S
        log_level   (str): specifies the lowest-severity log message
                           DEBUG, INFO, WARNING, ERROR or CRITICAL
                           default is DEBUG
    """
    dict_level = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    if log_level not in dict_level:
        raise ValueError("Invalid log_level")
    if filemode not in ["a", "w"]:
        raise ValueError("Invalid filemode")

    if not date_format:
        date_format = "%m/%d/%Y %H:%M:%S"

    log_fmt = "%(asctime)s %(module)s %(funcName)s %(levelname)s %(message)s"

    logging.basicConfig(
        level=dict_level[log_level],
        format=log_fmt,
        datefmt=date_format,
        filemode=filemode,
        filename=logfile,
    )

    return logging.getLogger(__name__)


class DataSourceHandler:
    """
    Class to handle data fetching and caching from the 'fundamentus.com.br' website.
    """

    def __init__(
        self,
        url,
        cache_file="data_cache.json",
        cache_duration=86400,
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
        response = requests.get(URL, headers=headers, timeout=60)
        return pd.read_html(
            response.text,
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
            log.debug("Cache file '%s' does not exist.", self.cache_file)
            return False

        cache_age = time.time() - os.path.getmtime(self.cache_file)

        if cache_age > self.cache_duration:
            log.debug("Cache is outdated (age: %.2f seconds).", cache_age)
            return False

        log.debug("Cache is valid (age: %.2f seconds).", cache_age)
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
            log.debug("Force updating or cache is invalid. Downloading new data.")
            pd_df = self.fetch_data()
            self.save_to_cache(pd_df)
            return pd_df

        log.debug("Loading data from cache.")
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
    #   - "1": Uses 'P/L' for earnings yield and 'ROE' for return on capital.
    #   - "2": Uses 'EV/EBIT' for earnings yield and 'ROIC' for return on capital.
    #   - "3": Uses 'EV/EBITDA' for earnings yield and 'ROIC' for return on capital.
    # These mappings allow for flexibility in defining which financial metrics are used in
    # the calculationof the Magic Formula, accommodating different variations of the formula.
    MAGIC_METHOD_FIELD = {
        "1": {"earnings yield": "P/L", "return on capital": "ROE"},
        "2": {"earnings yield": "EV/EBIT", "return on capital": "ROIC"},
        "3": {"earnings yield": "EV/EBITDA", "return on capital": "ROIC"},
    }

    def __init__(self, pd_df, magic_method):
        """
        Initializes the MagicFormula class with financial data and the chosen method
        for calculation.

        Parameters:
            pd_df (pandas.DataFrame): The financial data of companies.
            magic_method (str): Specifies the method used for calculating the Magic Formula ranking.
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

    def apply_converters(self):
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
        log.debug("Removing companies with %s less than %s", col_name, min_value)
        tickers = self.pd_df.loc[self.pd_df[col_name] <= min_value].index
        log.debug(self.pd_df.loc[tickers])
        self.pd_df.drop(tickers, inplace=True)

    def filter_data(self):
        """
        Removes rows in `pd_df` with negative or undesirable values for key financial metrics.

        Filters out companies with non-positive earnings yield, return on capital, and Liq.2meses.
        """
        self._remove_rows(self.earnings_yield, 0)
        self._remove_rows(self.ret_on_capital, 0)
        self._remove_rows("Liq.2meses", 0)

    def drop_unneeded_columns(self, level):
        """
        Removes unnecessary columns from `pd_df` based on the specified verbosity level.

        Parameters:
            level (int): The verbosity level that determines which columns are retained.
                        Higher levels retain more columns.
        """
        df_columns = self.pd_df.columns.tolist()
        if level == 0:
            keep_cols = [self.earnings_yield, self.ret_on_capital]
        elif level == 1:
            keep_cols = [
                "Cotação",
                "Div.Yield",
                "ROIC",
                "ROE",
                "P/L",
                "EV/EBIT",
                "EV/EBITDA",
                self.earnings_yield,
                self.ret_on_capital,
            ]
        else:
            return

        remove_cols = [x for x in df_columns if x not in keep_cols]
        self.pd_df.drop(remove_cols, axis="columns", inplace=True)

    def calc_rank(self):
        """
        Calculates the Magic Formula ranking for companies in `pd_df`.

        Adds ranking columns to `pd_df` based on the earnings yield and return on capital,
        then calculates a final rank.
        """
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

    def show_rank(self, top):
        """
        Displays the top-ranked companies.

        Parameters:
            top (int): The number of top-ranked companies to display.
        """
        self.pd_df.reset_index(inplace=True)
        self.pd_df.index = self.pd_df.index + 1
        print(self.pd_df.head(top).to_string())


##############################################################################
# Main function
##############################################################################
def main():
    """Command line execution."""
    global log

    # Parser the command line
    args = parse_parameters()
    # Configura log --debug
    log = setup_logging() if args.debug else logging
    log.debug("CMD line args: %s", vars(args))

    data_handler = DataSourceHandler(URL, force_update=args.force_update)
    pd_df = data_handler.get_data()

    magicformula = MagicFormula(pd_df, str(args.method))
    magicformula.apply_converters()
    magicformula.filter_data()
    magicformula.drop_unneeded_columns(level=args.verbose)
    magicformula.calc_rank()
    magicformula.show_rank(args.top)


##############################################################################
# Run from command line
##############################################################################
if __name__ == "__main__":
    main()

# vim: ts=4
