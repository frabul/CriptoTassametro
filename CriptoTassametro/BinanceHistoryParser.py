import os.path
import json
from binance.spot import Spot
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta, timezone
from .Components import *
from .PriceProvider import PriceProvider
from .OperationsDatabase import OperationsDatabase

PRICE_ERROR_LIMIT = 0.2


class HistoryEntryType(Enum):
    Deposit = "Deposit"
    Withdraw = "Withdraw"
    Sell = "Sell"
    Buy = "Buy"
    Fee = "Fee"
    Transaction_Sold = "Transaction Sold"
    Transaction_Revenue = "Transaction Revenue"
    Transaction_Fee = "Transaction Fee"
    Transaction_Buy = "Transaction Buy"
    Transaction_Spend = "Transaction Spend"
    Small_Assets_Exchange_BNB = "Small Assets Exchange BNB"
    Binance_Card_Cashback = "Binance Card Cashback"
    Binance_Card_Spending = "Binance Card Spending"
    NFT_Transaction = "NFT Transaction"
    Distribution = "Distribution"
    Swap_Farming_Rewards = "Swap Farming Rewards"
    Liquid_Swap_Add_Sell = "Liquid Swap Add/Sell"
    Liquidity_Farming_Remove = "Liquidity Farming Remove"
    Binance_Convert = "Binance Convert"
    Mission_Reward_Distribution = "Mission Reward Distribution"
    Asset_Recovery = "Asset Recovery"
    Sub_account_Transfer = "Sub-account Transfer"
    Transfer_Between_Main_and_Funding_Wallet = "Transfer Between Main and Funding Wallet"
    Transfer_Between_Spot_Account_and_UM_Futures_Account = "Transfer Between Spot Account and UM Futures Account"
    Transfer_Between_Main_Account_and_Futures_Account = "Transfer Between Main Account and Futures Account"
    Transfer_Between_Spot_Account_and_C2C_Account = "Transfer Between Spot Account and C2C Account"
    Transfer_Between_Main_Account_and_Margin_Account = "Transfer Between Main Account/Futures and Margin Account"
    Funding_Fee = "Funding Fee"
    Margin_Repayment = "Margin Repayment"
    Simple_Earn_Flexible_Subscription = "Simple Earn Flexible Subscription"
    Realized_Profit_and_Loss = "Realized Profit and Loss"
    Small_Assets_Conversion_for_Liquidation = "Small Assets Conversion for Liquidation"
    Simple_Earn_Flexible_Redemption = "Simple Earn Flexible Redemption"
    Simple_Earn_Flexible_Interest = "Simple Earn Flexible Interest"
    Airdrop_Assets = "Airdrop Assets"
    Margin_Loan = 'Margin Loan'
    Transaction_Related = 'Transaction Related'
    Staking_Rewards = 'Staking Rewards'
    Token_Swap_Rebranding = 'Token Swap - Redenomination/Rebranding'

    @staticmethod
    def contains(value):
        return value in HistoryEntryType.__members__.keys()


class HistoryEntry:
    TransactionTypeValues = set([member.value for member in HistoryEntryType])

    def __init__(self, line: str) -> None:
        parts = line.split(",")
        self.user_id = parts[0][1:-1]
        # parse datetime from format 2022-01-01 00:00:31
        self.utc_time = datetime.strptime(parts[1][1:-1], "%Y-%m-%d %H:%M:%S")
        self.utc_time = self.utc_time.replace(tzinfo=timezone.utc)
        self.account = parts[2][1:-1]
        if parts[3][1:-1] not in HistoryEntry.TransactionTypeValues:
            raise ValueError(f"Unknown transaction type: {parts[3][1:-1]}")
            self.operation = parts[3][1:-1]
        else:
            self.operation = HistoryEntryType(parts[3][1:-1])
        self.coin = parts[4][1:-1]
        self.change = float(parts[5][1:-1])
        self.remark = parts[6][1:-1]
        pass

    def __repr__(self) -> str:
        return f"{self.operation} {self.coin} {self.change}"


class ExchangeEntryCombination:
    def __init__(self, buy: HistoryEntry, sell: HistoryEntry, fee: HistoryEntry = None, error=None) -> None:
        self.buy = buy
        self.sell = sell
        self.fee = fee
        self._error = error
        pass

    def is_valid(self):
        buy_and_sell = self.buy is not None and self.sell is not None
        user_id_ok = self.buy.user_id == self.sell.user_id
        if self.fee is not None and self.fee.user_id is not None:
            user_id_ok &= (self.fee.user_id == self.buy.user_id)
        buy_and_sell_different = self.buy.coin != self.sell.coin
        return buy_and_sell and user_id_ok and buy_and_sell_different

    def error(self, priceProvider: PriceProvider) -> float:
        if self._error is not None:
            return self._error

        if not self.is_valid():
            self._error = 1e10
            return self._error

        price = abs(self.sell.change / self.buy.change)
        price_expected = priceProvider.get_price(
            Symbol(self.buy.coin, self.sell.coin), self.buy.utc_time)
        if price_expected is None:
            self._error = 1e10
            return self._error
        # finish early if error is too high
        if abs(price - price_expected) / price_expected > PRICE_ERROR_LIMIT:
            self._error = 1e10
            return self._error

        if self.fee is not None and self.fee.change != 0:
            fee_ratio_expected = 0.00075 if self.fee.coin == "BNB" else 0.001
            fee_expected = self.buy.change * fee_ratio_expected
            fee_expected_converted = priceProvider.convert(
                AssetAmount(self.buy.coin, fee_expected), self.fee.coin, self.fee.utc_time)

            if fee_expected_converted.symbol == 'BNB' and fee_expected_converted.amount < 1.07e-06:
                fee_expected_converted = AssetAmount('BNB', 1.07e-06)
            elif fee_expected_converted.symbol == 'BTC' and fee_expected_converted.amount < 1e-08:
                fee_expected_converted = AssetAmount('BTC', 1e-08)
            fee_error = abs(fee_expected_converted.amount -
                            abs(self.fee.change)) / fee_expected_converted.amount
        else:
            fee_error = 0

        self._error = (
            fee_error * 0.2 +
            abs(price - price_expected) / price_expected
        )
        return self._error

    def to_operation(self) -> ExchangeOperation:
        if self.error(None) > 2:
            raise ValueError("Cannot convert to operation, error too high")
        fee = AssetAmount(self.buy.coin, 0)
        if self.fee is not None:
            fee = AssetAmount(self.fee.coin, abs(self.fee.change))
        op = ExchangeOperation(
            AssetAmount(self.sell.coin, abs(self.sell.change)),
            AssetAmount(self.buy.coin, abs(self.buy.change)),
            fee,
            self.buy.utc_time
        )
        return op


# gnerate all possible combination n of items contained in nums
def generate_combinations(itemsCount, n):
    indexes = [0 for x in range(0, n)]  # indexes of last group
    i = 0
    while True:
        if indexes[i] < itemsCount:
            if i == n - 1:
                yield indexes
                indexes[i] += 1
            else:
                indexes[i + 1] = indexes[i] + 1
                i += 1
        else:
            i -= 1
            if i < 0:
                break
            indexes[i] += 1


def generate_buy_sell_fee_combinations(n):
    for i in range(0, n):
        for j in range(0, n):
            for k in range(0, n):
                yield (i, j, k)


def generate_buy_sell_combinations(n):
    for i in range(0, n):
        for j in range(0, n):
            yield (i, j)


class BinanceHistoryParser:
    exchange_sell_types = [HistoryEntryType.Sell,
                           HistoryEntryType.Transaction_Sold,
                           HistoryEntryType.Transaction_Spend]
    exchange_buy_types = [HistoryEntryType.Buy,
                          HistoryEntryType.Transaction_Buy,
                          HistoryEntryType.Transaction_Revenue]
    exchange_fee_types = [HistoryEntryType.Fee,
                          HistoryEntryType.Transaction_Fee]
    gift_operation_types = [HistoryEntryType.Binance_Card_Cashback,
                            HistoryEntryType.Distribution,
                            HistoryEntryType.Swap_Farming_Rewards,
                            HistoryEntryType.Mission_Reward_Distribution,
                            HistoryEntryType.Realized_Profit_and_Loss,
                            HistoryEntryType.Simple_Earn_Flexible_Interest,
                            HistoryEntryType.Airdrop_Assets
                            ]
    ignore_types = [HistoryEntryType.Asset_Recovery,
                    HistoryEntryType.Sub_account_Transfer,
                    HistoryEntryType.Transfer_Between_Main_and_Funding_Wallet,
                    HistoryEntryType.Transfer_Between_Spot_Account_and_UM_Futures_Account,
                    HistoryEntryType.Transfer_Between_Main_Account_and_Futures_Account,
                    HistoryEntryType.Transfer_Between_Spot_Account_and_C2C_Account,
                    HistoryEntryType.Transfer_Between_Main_Account_and_Margin_Account,
                    HistoryEntryType.Small_Assets_Conversion_for_Liquidation
                    ]
    exchange_entries_types = exchange_buy_types + \
        exchange_sell_types + exchange_fee_types
    combinations_cache = {}

    def __init__(self, price_provider: PriceProvider, operationsDb: OperationsDatabase) -> None:
        self.price_provider = price_provider
        self.new_operations: list[Operation] = []
        self.current_entry = -1
        self.operations_db = operationsDb

    def parse_operations(self, hist_entries: list[HistoryEntry], fileName: str) -> list[Operation]:
        self.buffer: list[HistoryEntry] = []
        self.entries: list[HistoryEntry] = list(hist_entries)
        self.entries.reverse()
        self.completed = False
        self.history_file = fileName
        while len(self.entries) > 0 or len(self.buffer) > 0:
            self.load_buffer()
            self.process_exchange_operations()
            self.process_small_assets_exchange_operations()
            self.process_simple_operations()
            if len(self.buffer) > 0:
                raise ValueError("Buffer not empty")

            print(f"Processed {self.current_entry} of {fileName}")
            self.operations_db.add_operations(self.new_operations)
            self.operations_db.set_parsed(fileName, self.current_entry)
            self.operations_db.save()
            # add operations to db
            self.new_operations.clear()

    def load_buffer(self):
        if len(self.entries) < 1:
            return
        entry = self.pop_entry()
        if entry is None:
            return
        while entry is not None and entry.operation in BinanceHistoryParser.ignore_types:
            entry = self.pop_entry()

        self.buffer.append(entry)
        must_load_more_with_same_time = \
            entry.operation in BinanceHistoryParser.exchange_entries_types or \
            entry.operation == HistoryEntryType.Binance_Convert or \
            entry.operation == HistoryEntryType.Small_Assets_Exchange_BNB
        if must_load_more_with_same_time:
            # loads in the buffer all the entries that should be processed together
            def more():
                if len(self.entries) < 1:
                    return False
                same_time = self.entries[-1].utc_time == entry.utc_time
                time_diff_small = abs(
                    entry.utc_time - self.entries[-1].utc_time) < timedelta(seconds=1.5)
                same_group = self.entries[-1].operation == HistoryEntryType.Binance_Convert or \
                    self.entries[-1].operation == HistoryEntryType.Small_Assets_Exchange_BNB
                return (same_time or (time_diff_small and same_group))

            while more():
                self.buffer.append(self.pop_entry())

    def pop_entry(self):
        if (len(self.entries) < 1):
            return None
        entry = self.entries.pop()
        self.current_entry += 1
        while self.operations_db.check_parsed(self.history_file, self.current_entry) and len(self.entries) > 0:
            entry = self.entries.pop()
            self.current_entry += 1

        return entry if not self.operations_db.check_parsed(self.history_file, self.current_entry) else None

    def process_exchange_operations(self):
        # tries to create operations by matching entries in the buffer
        buys = [entry for entry in self.buffer
                if entry.operation in BinanceHistoryParser.exchange_buy_types
                or (entry.operation == HistoryEntryType.Binance_Convert and entry.change > 0)]
        sells = [entry for entry in self.buffer
                 if entry.operation in BinanceHistoryParser.exchange_sell_types
                 or (entry.operation == HistoryEntryType.Binance_Convert and entry.change < 0)]
        fees = [entry for entry in self.buffer
                if entry.operation in BinanceHistoryParser.exchange_fee_types]

        # fill fees with zero entries if there are not enough
        while len(fees) < len(buys):
            tstr = buys[0].utc_time.strftime("%Y-%m-%d %H:%M:%S")
            dummyFee = HistoryEntry(f"'0','{tstr}',ignore,'Fee','BNB','0',ignore")
            dummyFee.user_id = None
            fees.append(dummyFee)

        if len(buys) != len(sells) or len(fees) != len(buys):
            raise ValueError("Buys and sells do not match")
        if len(buys) == 0:
            return
        if len(buys) == 1:
            # set error 0 because we are sure
            comb = ExchangeEntryCombination(buys[0], sells[0], fees[0], 0)
            self.emit_operation(comb.to_operation())
            self.buffer.remove(buys[0])
            self.buffer.remove(sells[0])
            if fees[0] in self.buffer:
                self.buffer.remove(fees[0])
            return

        # produce all possible combinations of (buys, sells, fees)
        combinations: list[ExchangeEntryCombination] = []
        n = len(buys)
        for comb_indexes in generate_buy_sell_fee_combinations(n):
            buy = buys[comb_indexes[0]]
            sell = sells[comb_indexes[1]]
            fee = fees[comb_indexes[2]]
            comb = ExchangeEntryCombination(buy, sell, fee)
            combinations.append(comb)
        combinations.sort(key=lambda comb: comb.error(self.price_provider))

        # pick the best n compatibles combinations
        # they are compatible if they do not share the same buy, sell or fee
        chosen: list[ExchangeEntryCombination] = []
        buysTaken = []
        sellsTaken = []
        feesTaken = []
        for comb in combinations:
            if not (comb.buy in buysTaken or comb.sell in sellsTaken or comb.fee in feesTaken):
                chosen.append(comb)
                buysTaken.append(comb.buy)
                sellsTaken.append(comb.sell)
                feesTaken.append(comb.fee)
                if len(chosen) == n:
                    break
        # create operations from chosen combinations
        for comb in chosen:
            self.emit_operation(comb.to_operation())
        # remove from the buffer the entries that were used
        self.buffer = [
            entry for entry in self.buffer if entry not in buysTaken and entry not in sellsTaken and entry not in feesTaken]

    def process_small_assets_exchange_operations(self):
        buys = [
            entry for entry in self.buffer
            if entry.operation == HistoryEntryType.Small_Assets_Exchange_BNB and entry.coin == "BNB"]
        sells = [
            entry for entry in self.buffer
            if entry.operation == HistoryEntryType.Small_Assets_Exchange_BNB and entry.coin != "BNB"]

        chosen = []
        buysTaken = []
        sellsTaken = []

        if len(buys) != len(sells):
            raise ValueError("Buys and sells do not match")
        if len(buys) == 0:
            return
        if len(buys) == 1:
            self.emit_operation(
                ExchangeEntryCombination(buys[0], sells[0], None, 0).to_operation())
            self.buffer.remove(buys[0])
            self.buffer.remove(sells[0])
            return
        # try to use remarks field to match buys and sells
        # in remarks field of the buys it tells which coin was spent to buy BNB (example 'OAX to BNB' )
        for buy in list(buys):
            for sell in list(sells):
                if buy.remark.split(" ")[0] == sell.coin:
                    self.emit_operation(
                        ExchangeEntryCombination(buy, sell, None, 0).to_operation())
                    sells.remove(sell)
                    buys.remove(buy)
                    buysTaken.append(buy)
                    sellsTaken.append(sell)
                    break

        # if there are still buys and sells, try to match them by price
        # produce all possible combinations of (buys, sells)
        combinations: list[ExchangeEntryCombination] = []
        n = len(buys)
        for comb_indexes in generate_buy_sell_fee_combinations(n):
            buy = buys[comb_indexes[0]]
            sell = sells[comb_indexes[1]]
            comb = ExchangeEntryCombination(buy, sell)
            combinations.append(comb)
        combinations.sort(key=lambda comb: comb.error(self.price_provider))

        # pick the best n compatibles combinations
        # they are compatible if they do not share the same buy, sell or fee
        for comb in combinations:
            if not (comb.buy in buysTaken or comb.sell in sellsTaken):
                chosen.append(comb)
                buysTaken.append(comb.buy)
                sellsTaken.append(comb.sell)
                if len(chosen) == n:
                    break
        # create operations from chosen combinations
        for comb in chosen:
            self.emit_operation(comb.to_operation())

        # remove from the buffer the entries that were used
        self.buffer = [entry for entry in self.buffer
                       if entry not in buysTaken and entry not in sellsTaken]

    def process_simple_operations(self):
        buffer = list(self.buffer)
        self.buffer.clear()
        for e in buffer:
            if e.operation == HistoryEntryType.Withdraw:
                assert e.change < 0
                self.emit_operation(
                    Withdrawal(e.coin, -e.change, e.utc_time))
            elif e.operation == HistoryEntryType.Deposit:
                self.emit_operation(
                    Deposit(e.coin, e.change, e.utc_time))
            elif e.operation in BinanceHistoryParser.gift_operation_types:
                self.emit_operation(
                    GiftOperation(e.coin, e.change, e.utc_time))
            elif e.operation == HistoryEntryType.Binance_Card_Spending:
                if e.change < 0:
                    op = Withdrawal(e.coin, -e.change, e.utc_time)
                else:
                    op = Deposit(e.coin, e.change, e.utc_time)
                self.emit_operation(op)
            elif e.operation == HistoryEntryType.NFT_Transaction:
                if e.change > 0:
                    op = GiftOperation(e.coin, e.change, e.utc_time)
                else:
                    op = Withdrawal(e.coin, -e.change, e.utc_time)
                self.emit_operation(op)
            elif e.operation == HistoryEntryType.Margin_Loan:
                self.emit_operation(
                    MarginLoan(e.coin, e.change, e.utc_time))
            elif e.operation == HistoryEntryType.Margin_Repayment:
                assert e.change < 0
                self.emit_operation(
                    MarginRepayment(e.coin, -e.change, e.utc_time))
            else:
                self.buffer.append(e)  # reinsert the entry in the buffer

    def emit_operation(self, op: Operation):
        self.new_operations.append(op)
        pass


def parse_files(files: list[str], max_lines=None) -> list[HistoryEntry]:
    movements: list[HistoryEntry] = []
    for file_path in files:
        with open(file_path, encoding="utf8") as fileStream:
            fileStream.readline()  # skip header
            for li in fileStream.readlines():
                li = li.strip("\n")
                if li != "":
                    mov = HistoryEntry(li)
                    movements.append(mov)
                    if max_lines is not None and len(movements) >= max_lines:
                        return movements
    return movements
