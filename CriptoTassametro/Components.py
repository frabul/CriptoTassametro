from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta


@dataclass
class AssetAmount:
    symbol: str
    amount: float

    def __str__(self) -> str:
        return f"{self.amount} {self.symbol}"


class Symbol:
    def __init__(self, baseAsset: str, quoteAsset: str):
        self.baseAsset = baseAsset
        self.quoteAsset = quoteAsset
        self.key = f"{baseAsset}{quoteAsset}"

    def reverse(self):
        return Symbol(self.quoteAsset, self.baseAsset)

    def __str__(self) -> str:
        return self.key


class Operation:
    def __init__(self, time: datetime):
        self.time = time


class OperationWithSymbolAmount(Operation):
    def __init__(self, symbol: str, amount: float, time: datetime):
        super().__init__(time)
        self.asset = AssetAmount(symbol, amount)

    def __str__(self) -> str:
        return f"{self.time} {self.__class__.__name__} {self.asset}"


@dataclass
class ExchangeOperation(Operation):
    sold: AssetAmount
    bought: AssetAmount
    fee: AssetAmount
    time: datetime

    def price(self) -> float:
        ''' price of the bought asset [ sold.symbol / asset.symbol ]'''
        return self.sold.amount / self.bought.amount

    def price_plus_fee(self) -> float:
        if self.bought.symbol == self.fee.symbol:
            return self.sold.amount / (self.bought.amount - self.fee.amount)
        elif self.sold.symbol == self.fee.symbol:
            return (self.sold.amount + self.fee.amount) / self.bought.amount
        else:
            raise ValueError("fee symbol not found in operation")

    def __str__(self) -> str:
        return f"{self.time} Traded {self.sold} for {self.bought} ({self.fee} fee)"


class FeePayment(OperationWithSymbolAmount):
    pass


class Withdrawal(OperationWithSymbolAmount):
    """Withdrawal of asset from exchange (subject to taxation)"""
    pass


class Deposit(OperationWithSymbolAmount):
    """Deposit of asset to exchange (not subject to taxation), sets the load price of the asset to the current market price"""
    pass


class GiftOperation(OperationWithSymbolAmount):
    ''' Soggetta a tassazione se no imposta solo il prezzo di carico '''
    pass


class MarginLoan(OperationWithSymbolAmount):
    pass


class MarginRepayment(OperationWithSymbolAmount):
    pass


@dataclass
class Position:
    symbol: str  # asset symbol
    amount: float  # asset amount
    price: float
    creationTime: datetime
    '''price of the position [ eur / asset ]'''

    def value(self) -> float:
        return self.amount * self.price

    def __str__(self) -> str:
        return f"{self.symbol}: {self.amount} @ {self.price}  ({self.value()}  EUR)"

    def take(self, amount: float) -> "Position":
        '''returns a new position with the given amount and the same price'''
        if self.amount < amount:
            raise ValueError("Amount to take is greater than the position amount")
        self.amount -= amount
        return Position(self.symbol, amount, self.price, self.creationTime)

    def merge(self, amount: float, price: float):
        self.amount += amount
        # price is weighted average
        self.price = (self.price * self.amount + price * amount) / (self.amount + amount)
