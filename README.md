# magicformulabr - Script que implementa a magic formula de Joel Greenblatt para classificar empresas listadas na Bovespa.

[![Build and Test](https://github.com/thobiast/magicformulabr/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/thobiast/magicformulabr/actions/workflows/build.yml)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/magicformulabr)
[![GitHub License](https://img.shields.io/github/license/thobiast/magicformulabr)](https://github.com/thobiast/magicformulabr/blob/main/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Detalhes sobre a estratégia Magic Formula pode ser encontrado no livro "*The Little Book That Still Beats the Market*" escrito por Joel Greenblatt.

O script consulta os dados das empresas no site http://fundamentus.com.br

O *magicformulabr* foi feito apenas para estudo, não é recomendação de investimento.

## Instalação

```bash
pip install magicformulabr
```

## Uso

O magicformulabr armazena os dados baixados em um arquivo local "*data_cache.json*" por 24 horas
para evitar requisições desnecessárias. Use `--force-update` para atualizar os dados.

```bash
$ magicformulabr -h
usage: magicformulabr [-h] [-d] [-v] [-m {1,2,3}] [-t TOP] [--force-update]

Gera rank de acoes usando a magic formula

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           debug flag
  -v, --verbose         verbosity level
  -m {1,2,3}, --method {1,2,3}
                        Campos usados para o calculo da magic formula
  -t TOP, --top TOP     Numero de empresas para mostrar no rank
  --force-update        Forca a atualizacao do cache

    Methods disponiveis:
        1 - P/L e ROE
        2 - EV/EBIT e ROIC
        3 - EV/EBITDA e ROIC

    Exemplos de uso:
        magicformulabr -h
        magicformulabr -m 1
        magicformulabr -v
        magicformulabr -vv
        magicformulabr -m 3 -vv


$ magicformulabr -t 10 -v
    Papel  Cotação    P/L Div.Yield  EV/EBIT  EV/EBITDA   ROIC      ROE  Rank_earnings_yield  Rank_return_on_capital  Rank_Final
1   PSSA3    47.71   9.14     4,49%     0.33       0.33  56.48   18,83%                  1.0                     3.0         4.0
2   WIZS3     6.61   4.95    10,12%     1.92       1.71  80.94   60,60%                  4.0                     2.0         6.0
3   MRFG3    14.82   4.89     0,00%     3.64       3.11  29.77  223,61%                  5.0                     8.0        13.0
4   MNPR3     6.84  -3.39     0,00%     0.95       0.85  22.68    3,89%                  2.0                    18.0        20.0
5   BEEF3     9.63   6.40     3,11%     5.53       4.74  21.10   67,81%                 13.0                    21.0        34.0
6   GEPA4    38.49  15.04     4,90%     6.35       4.59  27.52   13,64%                 26.0                     9.0        35.0
7   GEPA3    39.00  15.24     4,84%     6.43       4.65  27.52   13,64%                 28.0                     9.0        37.0
8   BOBR4     2.24  15.17     0,00%     6.50       5.52  24.58  -15,94%                 30.0                    14.0        44.0
9   ATOM3     4.16   7.17     0,00%     7.46       7.43  84.60   73,56%                 47.0                     1.0        48.0
10  EQTL3    22.99   8.05     1,39%     6.14       5.47  16.32   29,69%                 18.0                    36.0        54.0
```
