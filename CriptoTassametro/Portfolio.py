from datetime import datetime as dt
from .Components import *


class Portfolio:
    ''' The fist position in the portfolio is always the reference currency and has always price 1'''

    def __init__(self, currency='EUR', initalAssets: list[Position] = []):
        self.position_small_threshold = 1e-4
        self.price_difference_small_threshold = 1e-3
        self.positions: dict[str, list[Position]] = {}
        self.currency = Position(currency, 0, 1, dt(1970, 1, 1))
        for pos in initalAssets:
            self.add(AssetAmount(pos.symbol, pos.amount), pos.price, pos.creationTime)

    def rebuild(self, symbol: str):
        # remove empty positions ( never remove first position which holds the reference currency )
        symList = self.positions.get(symbol, [])
        self.positions[symbol] = [pos for pos in symList if (abs(pos.amount) > 1e-10)]

    def remove(self, asset: AssetAmount) -> list[Position]:
        """remove an amount of asset from the portfolio, returns a list of positions that have been removed to satisfy the request."""
        # if the asset is the reference currency, just remove the amount ( the position can go negative )
        if asset.symbol == self.currency.symbol:
            self.currency.amount -= asset.amount
            return [Position(asset.symbol, asset.amount, 1, dt(1970, 1, 1))]

        # the amount is remove in a LIFO manner, so from last position first
        asset = AssetAmount(asset.symbol, asset.amount)
        retVal = []

        symbolPositions = self.positions.get(asset.symbol, [])
        while len(symbolPositions) > 0:
            pos = symbolPositions[-1]
            if pos.symbol == asset.symbol and pos.amount > 0:
                amountToTake = min(asset.amount, pos.amount)
                asset.amount -= amountToTake
                retVal.append(pos.take(amountToTake))
            if pos.amount == 0:
                symbolPositions.pop()
            if asset.amount <= 0:
                break

        if abs(asset.amount) > 1e-7:
            raise ValueError(f"Not enough {asset.symbol} in the portfolio, remaining {asset.amount}")

        return retVal

    def add(self, asset: AssetAmount, price: float, time: dt):
        '''add an amount of asset to the portfolio'''
        if asset.symbol == self.currency.symbol:
            if price != 1:
                raise ValueError("Price of the reference currency must be 1")
            self.currency.amount += asset.amount
        else:
            if not asset.symbol in self.positions:
                self.positions[asset.symbol] = []
            symPosList = self.positions[asset.symbol]
            # check if we can merge the asset with the last position
            lastPos = symPosList[-1] if len(symPosList) > 0 else None
            if lastPos is not None:
                if price == lastPos.price:  # covers the case when both prices are 0
                    lastPos.amount += asset.amount
                elif abs(lastPos.price - price) * 2 / (lastPos.price + price) < self.price_difference_small_threshold:
                    lastPos.merge(asset.amount, price)  # prices are close enough, merge the position
                elif abs(asset.amount) < self.position_small_threshold:
                    lastPos.merge(asset.amount, price)  # very small amount merge it
                else:  # create a new position
                    symPosList.append(Position(asset.symbol, asset.amount, price, time))
            else:
                # create a new position
                symPosList.append(Position(asset.symbol, asset.amount, price, time))

    def get_total(self, symbol: str) -> AssetAmount:
        '''returns the total amount of the asset in the portfolio'''
        if symbol == self.currency.symbol:
            return self.currency.amount
        amount = 0
        for symPosList in self.positions.values():
            for pos in symPosList:
                if pos.symbol == symbol:
                    amount += pos.amount
        return amount

    def get_positions(self, min_value: float = 0) -> list[Position]:
        '''returns the list of positions that have a value greater than min_value'''
        result = [pos for posList in self.positions.values() for pos in posList if abs(pos.value()) >= min_value]
        if abs(self.currency.amount) >= min_value:
            result.append(self.currency)
        return result

    def print(self):
        print("Portfolio:")
        print("   " + str(self.currency))
        for li in self.positions.values():
            for p in li:
                if abs(p.amount) > 1e-3:
                    print("   " + str(p))
