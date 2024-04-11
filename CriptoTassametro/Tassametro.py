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
                 deduce_fee: bool = True,
                 end_of_day_prices_for_fees: bool = True,  # use closing price from last day for fees (speeds up calculation)
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
        self.capital_gain_logger = capital_gain_logger
        self.io_movements_logger = io_movements_logger
        self.deduce_fee = deduce_fee
        self.end_of_day_prices_for_fees = end_of_day_prices_for_fees
        self.include_fee_in_price = include_fee_in_price
        self.fee_paid = 0

    def print_state(self) -> None:
        self.portfolio.print()
        print(f"Capital gain: {self.capital_gain} {self.currency}")
        print(f"Fee paid: {self.fee_paid} {self.currency}")

    def process_deposit(self, dep: Deposit):
        # aggiungere amount di asset al portafoglio con pc = prezzo corrente
        sym = Symbol(dep.asset.symbol, self.currency)
        price = self.prices.get_price(sym, dep.time)
        if price is None:
            print(f"Price not found for {sym} at {dep.time}")
            self.io_movements_logger.info(f"Price not found for {sym} at {dep.time}, considering 0")
            price = 0
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
            asset_in_currency = self.prices.convert(withdraw.asset, self.currency, withdraw.time)
            if asset_in_currency is None or asset_in_currency.amount is None:
                print(f"{withdraw.time} - Price not found for Withdrawal {withdraw.asset}")
                self.io_movements_logger.info(f"{withdraw.time} - Price not found for Withdrawal {withdraw.asset} ")
                self.portfolio.remove(withdraw.asset)
                return
            if asset_in_currency.amount == 0:
                print(f"Unable to remove {withdraw.asset} from portfolio")
                return
            # create a synthetic trade
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
        # if fee is payd troguh some asset it always needs to be converted to 'currency'
        #   process the trade ( that will eventually add some capital gain )
        # then subtract the fee from the capital gain
        syntethicTrade = None
        if trade.fee.amount == 0:
            fee_in_currency = AssetAmount(self.currency, 0)
        elif trade.fee.symbol == self.currency:
            fee_in_currency = trade.fee
            self.portfolio.remove(fee_in_currency)
        else:
            conversion_time = trade.time
            if self.end_of_day_prices_for_fees:
                conversion_time = trade.time.replace(hour=0, minute=0, second=0, microsecond=0)  # speed up conversion by taking a price approximated by hour
            fee_in_currency = self.prices.convert(trade.fee, self.currency, conversion_time)
            # the fee must be exchanged to 'currency' end the expense is subject to taxation like any other
            # we will pocess the syntethic trade after adding the bought asset ( as sometimes the fee is payed in the bought asset )
            syntethicTrade = ExchangeOperation(trade.fee,  fee_in_currency, self.null_amount, trade.time)
        self.fee_paid += fee_in_currency.amount

        # a trade is subject to taxation if the asset bought is 'currency'
        # bought asset is added to portfolio
        # sold asset is removed from portfolio
        # fee is removed from portfolio
        sold_positions = self.portfolio.remove(trade.sold)
        if trade.bought.symbol in ["EUR", "USD", "USDT", "USDC", "BUSD", "DAI"]:
            # in this case the transaction is subject to taxation
            # then the we need to calculate capital gain
            if self.deduce_fee:
                self.capital_gain -= fee_in_currency.amount
            # add the bought asset to the portfolio
            bought_in_currency = self.prices.convert(trade.bought, self.currency, trade.time)
            # the bought asset is added with its actual price in 'currency'
            self.portfolio.add(trade.bought, bought_in_currency.amount / trade.bought.amount, trade.time)
            # calculate the capital gain
            price_in_currency = bought_in_currency.amount / trade.sold.amount
            for soldPos in sold_positions:
                # calculate the load price in 'currency'
                self.capital_gain += soldPos.amount * (price_in_currency - soldPos.price)
        else:
            for soldPos in sold_positions:
                if soldPos.amount == 0:
                    continue
                # exchange the fee to 'currency' and remove from portfolio
                fee_pertinent = AssetAmount(
                    fee_in_currency.symbol,
                    fee_in_currency.amount * (soldPos.amount / trade.sold.amount))

                spent_in_currency = soldPos.amount * soldPos.price
                if self.deduce_fee:
                    if self.include_fee_in_price:
                        # calculate the load price in 'currency' ( which includes the fee )
                        spent_in_currency += fee_pertinent.amount
                    else:
                        self.capital_gain -= fee_pertinent.amount
                bought_pertinent = trade.bought.amount * (soldPos.amount / trade.sold.amount)
                price_in_currency = spent_in_currency / bought_pertinent

                # add the bought asset to the portfolio
                self.portfolio.add(AssetAmount(trade.bought.symbol, bought_pertinent), price_in_currency, trade.time)
        # finally process the syntethic trade
        if syntethicTrade is not None:
            self.process_trade(syntethicTrade)
            self.portfolio.remove(fee_in_currency)

    def process_fee_payment(self, fee: FeePayment):
        # the amount converted to 'currency' and deducted from capital gains
        fee_in_currency = self.prices.convert(fee.asset, self.currency, fee.time)
        synthetic_trade = ExchangeOperation(fee.asset, fee_in_currency, self.null_amount, fee.time)
        self.process_trade(synthetic_trade)
        self.portfolio.remove(fee_in_currency)
        self.fee_paid += fee_in_currency.amount
        if self.deduce_fee:
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
                try:
                    initial_capital_gain = self.capital_gain
                    cnt += 1
                    print(f'Processing {cnt}/{total}: {op}')
                    self.process_operation(op)
                    cap_gain_for_op = self.capital_gain - initial_capital_gain
                    if cap_gain_for_op != 0:
                        self.capital_gain_logger.info(f'{op} - capital gain: {cap_gain_for_op}')
                except Exception as e:
                    raise Exception(f"Error processing operation {op}:\n   {e}")


# create loggers
formatter = logging.Formatter('%(message)s')


def setup_logger(name, log_file, level=logging.INFO):
    """To setup as many loggers as you want"""
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger
