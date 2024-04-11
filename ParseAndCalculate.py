import logging
from CriptoTassametro.BinanceHistoryParser import BinanceHistoryParser, parse_files
from CriptoTassametro.PriceProvider import PriceProvider
from CriptoTassametro.OperationsDatabase import OperationsDatabase
from CriptoTassametro.Portfolio import Portfolio, Position
from CriptoTassametro.Tassametro import Tassametro, setup_logger
import os
from datetime import datetime

# this program needs two aruments
# 1. a name for the session
# 2. the path to the binance history csv file


if __name__ == "__main__":
    # parse arguments using argparse
    import argparse
    import sys 
    parser = argparse.ArgumentParser(description='Calculate capital gain from binance history')
    parser.add_argument('session_name', type=str, help='name of the session')
    parser.add_argument('binance_history_file', type=str, help='path to the binance history csv file')
    args = parser.parse_args()
    
    session_name = args.session_name
    binance_history_file = args.binance_history_file
    
    # assure that data directory exists
    if not os.path.exists('./data'):
        os.makedirs('./data')
        
    # create loggers
    capital_gain_logger = setup_logger('capital_gain_logger', f'./data/{session_name}_capital_gain.log')
    io_movements_logger = setup_logger('io', f'./data/{session_name}_IO_movements.log')


    # create price provider
    prices = PriceProvider('./data/prices.sqlite')
    # first parse binance csv files
    # if the file is huge thuis is a long process, it can be interrupted and resumed later
    # as everything is saved in a database
    operationsDb = OperationsDatabase(f'./data/{session_name}_operations.sqlite')
    opParser = BinanceHistoryParser(prices, operationsDb)
    historyEntries = parse_files([binance_history_file])
    opParser.parse_operations(historyEntries, binance_history_file)
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
                            io_movements_logger=io_movements_logger)
    operations = operationsDb.get_operations()
    tassametro.process_operations(operations)
    tassametro.print_state()
