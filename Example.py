import logging
from CriptoTassametro.BinanceHistoryParser import BinanceHistoryParser, parse_files
from CriptoTassametro.PriceProvider import PriceProvider
from CriptoTassametro.OperationsDatabase import OperationsDatabase
from CriptoTassametro.Portfolio import Portfolio, Position
from CriptoTassametro.Tassametro import Tassametro, setup_logger
import os
from datetime import datetime


# assure that data directory exists
if not os.path.exists('./data'):
    os.makedirs('./data')
# create loggers
capital_gain_logger = setup_logger('capital_gain_logger', './data/example_capital_gain.log')
io_movements_logger = setup_logger('io', './data/example_IO_movements.log')


# create price provider
prices = PriceProvider('./data/prices.sqlite')
# first parse binance csv files
# if the file is huge thuis is a long process, it can be interrupted and resumed later
# as everything is saved in a database
operationsDb = OperationsDatabase('./data/example_operations.sqlite')
opParser = BinanceHistoryParser(prices, operationsDb)
historyEntries = parse_files(["./binance_history_example.csv"])
opParser.parse_operations(historyEntries, "binance_history_example.csv")
operationsDb.save()

# then use the data to calculate the capital gain
initialPortfolio = Portfolio(
    currency='EUR',
    initalAssets=[
        Position('EUR', 10000, 1, datetime(2023, 1, 1))
    ]
)
tassametro = Tassametro(datetime(2023, 1, 1),
                        datetime(2024, 1, 1),
                        prices, portfolio=initialPortfolio,
                        capital_gain_logger=capital_gain_logger,
                        io_movements_logger=io_movements_logger,
                        deduce_fee=True)
operations = operationsDb.get_operations()
tassametro.process_operations(operations)
tassametro.print_state()
