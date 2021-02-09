#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script que implementa a magic formula de Joel Greenblatt para empresas na Bovespa.

Dados baixados do site http://fundamentus.com.br
"""

import argparse
import logging

import pandas as pd

import requests

URL = "http://fundamentus.com.br/resultado.php"

MAGIC_METHOD_FIELD = {
    "1": {"earnings yield": "P/L", "return on capital": "ROE"},
    "2": {"earnings yield": "EV/EBIT", "return on capital": "ROIC"},
    "3": {"earnings yield": "EV/EBITDA", "return on capital": "ROIC"},
}


##############################################################################
# Parse da linha de comando
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


class MagicFormula:
    """Magic Formula class."""

    def __init__(self, magic_method):
        """Initialize MagicFormula class."""
        self.pd_df = None
        self.earnings_yield = MAGIC_METHOD_FIELD[magic_method]["earnings yield"]
        self.ret_on_capital = MAGIC_METHOD_FIELD[magic_method]["return on capital"]

    def get_data(self):
        """Download data from fundamentus e create DataFrame."""
        headers = {
            "User-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:85.0)"
            "Gecko/20100101 Firefox/85.0",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
        }
        response = requests.get(URL, headers=headers)
        self.pd_df = pd.read_html(
            response.text,
            thousands=".",
            decimal=",",
            index_col="Papel",
            encoding="utf-8",
            converters={self.ret_on_capital: self.pct_to_float},
        )[0]

    def filter_data(self):
        """
        Cleanup data.

        Remove rows with negative earnings yield, return on capital and Liq.2meses
        """
        self.remove_rows(self.earnings_yield, 0)
        self.remove_rows(self.ret_on_capital, 0)
        self.remove_rows("Liq.2meses", 0)

    def remove_rows(self, col_name, min_value):
        """
        Remove rows based on criteria.

        Parameters:
            col_name  (str): Column name
            min_value (int): Minimum value
        """
        log.debug("Removing companies with %s less than %s", col_name, min_value)
        tickers = self.pd_df.loc[self.pd_df[col_name] <= min_value].index
        log.debug(self.pd_df.loc[tickers])
        self.pd_df.drop(tickers, inplace=True)

    def drop_unneeded_columns(self, level):
        """Remove columns."""
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
        """Create magic formula rank."""
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
        """Show magic formula rank."""
        self.pd_df.reset_index(inplace=True)
        self.pd_df.index = self.pd_df.index + 1
        print(self.pd_df.head(top).to_string())

    @staticmethod
    def pct_to_float(number):
        """Convert string to float, remove % char and set decimal point to '.'."""
        return float(number.strip("%").replace(".", "").replace(",", "."))


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

    magicformula = MagicFormula(str(args.method))
    magicformula.get_data()
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
