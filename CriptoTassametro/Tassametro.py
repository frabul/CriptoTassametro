from datetime import datetime as dt
from .PriceProvider import PriceProvider, Symbol
from .Components import *
from .Portfolio import Portfolio
import logging

# a class to calculate taxes for capital gain on cryptocurrencies in Italy


class dummy_logger:
    def info(self, text):
        pass


class Tassametro:
    def __init__(self,
                 startTime: dt,
                 endTime: dt,
                 pricesDb: PriceProvider,
                 portfolio: Portfolio,
                 include_fee_in_price: bool = True,
                 capital_gain_logger=dummy_logger(),
                 io_movements_logger=dummy_logger()):
        if not portfolio:
            portfolio = Portfolio()
        self.startTime = startTime
        self.endTime = endTime
        self.prices = pricesDb if pricesDb else PriceProvider(
            "./data/prices.db")
        self.currency = "EUR"  # reference currency
        self.portfolio = portfolio
        self.capital_gain = 0
        self.null_amount = AssetAmount(self.currency, 0)
        self.operations_count = 0
        self.include_fee_in_price = include_fee_in_price
        self.capital_gain_logger = capital_gain_logger
        self.io_movements_logger = io_movements_logger

    def print_state(self) -> None:
        self.portfolio.print()
        print(f"Capital gain: {self.capital_gain} {self.currency}")

    def process_deposit(self, dep: Deposit):
        # aggiungere amount di asset al portafoglio con pc = prezzo corrente
        sym = Symbol(dep.asset.symbol, self.currency)
        price = self.prices.get_price(sym, dep.time)
        if price is None:
            raise ValueError(f"Price not found for {sym} at {dep.time}")
        self.portfolio.add(
            dep.asset,
            price,
            dep.time)
        self.io_movements_logger.info(f'{dep} - price: {price}')

    def process_withdrawal(self, withdraw: Withdrawal, logIt: bool = True):
        initial_cap_gain = self.capital_gain
        # transaction is subejct to taxation if the asset is not EUR
        if withdraw.asset.symbol != self.currency:
            # first convert asset to 'currency' and then remove the amount
            sym = Symbol(withdraw.asset.symbol, self.currency)
            # create a synthetic trade
            asset_in_currency = self.prices.convert(withdraw.asset, self.currency, withdraw.time)
            if asset_in_currency is None:
                print(f"{withdraw.time} - Price not found for Withdrawal {withdraw.asset}")
                self.io_movements_logger.info(f"{withdraw.time} - Price not found for Withdrawal {withdraw.asset} ")
                self.portfolio.remove(withdraw.asset)
                return
            trade = ExchangeOperation(withdraw.asset, asset_in_currency, self.null_amount, withdraw.time)
            self.process_trade(trade, logIt=False)  # this trade will yield eventual capital gains
            self.process_withdrawal(Withdrawal(asset_in_currency.symbol, asset_in_currency.amount, withdraw.time), logIt=False)
        else:
            # just remove the amount from the portfolio
            self.portfolio.remove(withdraw.asset)
        if logIt:
            self.io_movements_logger.info(f'{withdraw} - capital gain: {self.capital_gain - initial_cap_gain}')

    def process_gift(self, gift: GiftOperation):
        # a gift is not subject to taxation
        # the amount is added to the portfolio
        # the load price is set to the current price in 'currency'
        # the capital gain is increased by the value in 'currency' of the asset ( amout * priceInCurrency )
        converted = self.prices.convert(gift.asset, self.currency, gift.time)
        if converted is None:
            print(f"{gift.time} - Price not found for Gift {gift.asset}   ")
            self.io_movements_logger.info(f"{gift.time} - Price not found for Gift {gift.asset}   ")
            self.portfolio.add(gift.asset, 0, gift.time)
        else:
            self.capital_gain += converted.amount
            self.portfolio.add(gift.asset, converted.amount / gift.asset.amount, gift.time)
            self.io_movements_logger.info(f"{gift} - price: {converted.amount / gift.asset.amount} - capital gain: {converted.amount}")

    def process_trade(self, trade: ExchangeOperation, logIt: bool = True):
        # a trade is subject to taxation if the asset bought is 'currency'
        # bought asset is added to portfolio
        # sold asset is removed from portfolio
        # fee is removed from portfolio
        sold_positions = self.portfolio.remove(trade.sold)
        if trade.bought.symbol == self.currency:
            # in this case the transaction is subject to taxation
            # then the we need to calculate capital gain
            if trade.fee.symbol == self.currency:
                # fee in 'currency', just subtract from capital gain and 'currency' position
                self.capital_gain -= trade.fee.amount
                # remove the fee from the portfolio
                self.portfolio.remove(trade.fee)
            elif trade.fee.amount > 0:
                # fee was paid using some other asset
                # convert to 'currency', process the trade ( that will eventually add some capital gain )
                # then subtract the fee from the capital gain
                fee_in_currency = self.prices.convert(trade.fee, self.currency, trade.time)
                # the fee is exchanged to 'currency'
                syntethicTrade = ExchangeOperation(trade.fee,  fee_in_currency, self.null_amount, trade.time)
                self.process_trade(syntethicTrade)
                # remove the fee from the portfolio (as currency)
                self.portfolio.remove(fee_in_currency)
                self.capital_gain -= fee_in_currency.amount
            # add the bought asset to the portfolio
            self.portfolio.add(trade.bought, 1, trade.time)
            # calculate the capital gain
            price_in_currency = trade.bought.amount / trade.sold.amount
            for soldPos in sold_positions:
                # calculate the load price in 'currency'
                self.capital_gain += soldPos.amount * (price_in_currency - soldPos.price)
        else:
            # we bought an asset so we need to calculate the load price in 'currency' ( which will include the fee )
            # and add the new position to the list
            # the fee is not instantly calculated as a loss but it is included in the load price
            if trade.fee.symbol == trade.bought.symbol or trade.fee.amount == 0:
                # simplified case, fee is paid in the same asset that we bought
                for soldPos in sold_positions:
                    fee_pertinent = trade.fee.amount * (soldPos.amount / trade.sold.amount)
                    # bought amount is reduced by the fee
                    bought_pertinent = trade.bought.amount * (soldPos.amount / trade.sold.amount) - fee_pertinent
                    price_in_currency = soldPos.amount * soldPos.price / bought_pertinent
                    # add the bought asset to the portfolio
                    self.portfolio.add(AssetAmount(trade.bought.symbol, bought_pertinent), price_in_currency, trade.time)
            else:
                # fee needs to be sold to 'currency' ( which will yield a capital gain )
                for soldPos in sold_positions:
                    # exchange the fee to 'currency' and remove from portfolio
                    fee_pertinent = AssetAmount(
                        trade.fee.symbol,
                        trade.fee.amount * (soldPos.amount / trade.sold.amount))
                    fee_in_currency = self.prices.convert(fee_pertinent, self.currency, trade.time)
                    syntethicTrade = ExchangeOperation(fee_pertinent, fee_in_currency, self.null_amount, trade.time)
                    self.process_trade(syntethicTrade)
                    # remove the fee from the portfolio
                    self.portfolio.remove(fee_in_currency)
                    if self.include_fee_in_price:
                        # calculate the load price in 'currency' ( which includes the fee )
                        spent_in_currency = soldPos.amount * soldPos.price + fee_in_currency.amount
                        bought_pertinent = trade.bought.amount * (soldPos.amount / trade.sold.amount)
                        price_in_currency = spent_in_currency / bought_pertinent
                    else:
                        # v2 calculate the price without considering the fee
                        self.capital_gain -= fee_in_currency.amount
                        spent_in_currency = soldPos.amount * soldPos.price
                        bought_pertinent = trade.bought.amount * (soldPos.amount / trade.sold.amount)
                        price_in_currency = spent_in_currency / bought_pertinent

                    # add the bought asset to the portfolio
                    self.portfolio.add(AssetAmount(trade.bought.symbol, bought_pertinent), price_in_currency, trade.time)

    def process_fee_payment(self, fee: FeePayment):
        # the amount converted to 'currency' and deducted from capital gains
        fee_in_currency = self.prices.convert(fee.asset, self.currency, fee.time)
        synthetic_trade = ExchangeOperation(fee.asset, fee_in_currency, self.null_amount, fee.time)
        self.process_trade(synthetic_trade)
        self.portfolio.remove(fee_in_currency)
        self.capital_gain -= fee_in_currency.amount

    def process_margin_loan(self, ml: MarginLoan):
        converted = self.prices.convert(ml.asset, self.currency, ml.time)
        price = converted.amount / ml.asset.amount
        self.portfolio.add(ml.asset, price, ml.time)

    def process_margin_repayment(self, mr: MarginRepayment):
        self.portfolio.remove(mr.asset)

    def process_operation(self, op: Operation):
        if isinstance(op, Deposit):
            self.process_deposit(op)
        elif isinstance(op, Withdrawal):
            self.process_withdrawal(op)
        elif isinstance(op, GiftOperation):
            self.process_gift(op)
        elif isinstance(op, ExchangeOperation):
            self.process_trade(op)
        elif isinstance(op, FeePayment):
            self.process_fee_payment(op)
        elif isinstance(op, MarginLoan):
            self.process_margin_loan(op)
        elif isinstance(op, MarginRepayment):
            self.process_margin_repayment(op)
        else:
            raise ValueError(f"Operation not recognized: {op}")
        self.operations_count += 1

    def process_operations(self, operations: list[Operation]):
        cnt = 0
        total = len(operations)
        operations = list(reversed(operations))
        while len(operations) > 0:
            # lod all the operations with the same time
            buffer = [operations.pop()]
            while len(operations) > 0 and operations[-1].time == buffer[0].time:
                buffer.append(operations.pop())
            # reorder the buffer
            # - loan first
            # - margin repayment last
            if len(buffer) > 1:
                buffer.sort(key=lambda x: 0 if isinstance(x, MarginLoan) else 2 if isinstance(x, MarginRepayment) else 1)
            for op in buffer:
                initial_capital_gain = self.capital_gain
                cnt += 1
                print(f'Processing {cnt}/{total}: {op}')
                self.process_operation(op)
                cap_gain_for_op = self.capital_gain - initial_capital_gain
                if cap_gain_for_op != 0:
                    self.capital_gain_logger.info(f'{op} - capital gain: {cap_gain_for_op}')
