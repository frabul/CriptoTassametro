 
from CriptoTassametro.Tassametro import Tassametro, Portfolio
from CriptoTassametro.Components import AssetAmount as AM, ExchangeOperation
from CriptoTassametro.PriceProvider import PriceProvider
from datetime import datetime as dt
import unittest


pricesDb = PriceProvider("./data/prices.db")
fee = 0.001


class TestTassametro(unittest.TestCase):
    def setUp(self) -> None:
        self.currency = "EUR"
        self.portfolio = Portfolio()
        self.tassametro = Tassametro(dt(2021, 1, 1), dt(2021, 12, 31), pricesDb, self.portfolio)
        print("")

    def print_state(self) -> None:
        self.portfolio.print()
        print(f"Capital gain: {self.tassametro.capital_gain} EUR")

    def test_fee_paid_from_bought(self):
        opers = [
            ExchangeOperation(AM("EUR", 10000), AM("BTC", 1), AM("BTC", 0.001), dt(2023, 1, 1)),
            ExchangeOperation(AM("BTC", 0.989), AM("EUR", 20000), AM("BTC", 0.01), dt(2023, 12, 1))
        ]
        for oper in opers:
            
            self.tassametro.process_operation(oper)

        self.print_state()
        self.assertEqual(len(self.portfolio.get_positions(min_value=0.001)), 1)
        self.assertAlmostEqual(self.portfolio.get_total("EUR"), self.tassametro.capital_gain)

    def test_fee_paid_from_sold(self):
        opers = [
            ExchangeOperation(AM("EUR", 10000), AM("BTC", 1), AM("EUR", 100), dt(2023, 1, 1)),
            ExchangeOperation(AM("BTC", 1), AM("EUR", 20000), AM("EUR", 200), dt(2023, 12, 1))
        ]
        for oper in opers:
            self.tassametro.process_operation(oper)

        self.print_state()
        self.assertEqual(len(self.portfolio.get_positions(min_value=0.001)), 1)
        self.assertAlmostEqual(self.portfolio.get_total("EUR"), self.tassametro.capital_gain)

    def test_double_exchange_1(self):
        opers = [
            ExchangeOperation(AM("EUR", 10000), AM("BTC", 1),     AM("EUR", 100), dt(2023, 1, 1)),  # 1btc = 10000eur
            ExchangeOperation(AM("BTC", 0.1),   AM("BNB", 10),    AM("BNB", 0.1), dt(2023, 2, 1)),  # 1bnb = 100eur
            ExchangeOperation(AM("BTC", 0.9),   AM("ETH", 9),     AM("BNB", 0.9), dt(2023, 3, 1)),  # 1eth = 1000eur
            ExchangeOperation(AM("ETH", 9),     AM("EUR", 15000), AM("BNB", 1),   dt(2023, 3, 2)),
            ExchangeOperation(AM("BNB", 7.9),   AM("EUR", 700),   AM("BNB", 0.1), dt(2023, 3, 3))
        ]
        for oper in opers:
            self.tassametro.process_operation(oper)
        self.print_state()
        self.assertEqual(len(self.portfolio.get_positions(min_value=0.001)), 1)
        self.assertAlmostEqual(self.portfolio.get_total("EUR"), self.tassametro.capital_gain)

    def test_double_exchange_2(self):
        opers = [
            ExchangeOperation(AM("EUR", 5000),  AM("BTC", 0.5),   AM("EUR", 100), dt(2023, 1, 1)),  # 1btc = 10000eur
            ExchangeOperation(AM("EUR", 7500),  AM("BTC", 0.5),   AM("EUR", 100), dt(2023, 1, 2)),  # 1btc = 15000eur
            ExchangeOperation(AM("BTC", 0.1),   AM("BNB", 10),    AM("BNB", 0.1), dt(2023, 2, 1)),  # 1bnb = 100eur
            ExchangeOperation(AM("BTC", 0.9),   AM("ETH", 9),     AM("BNB", 0.9), dt(2023, 3, 1)),  # 1eth = 1000eur
            ExchangeOperation(AM("ETH", 9),     AM("EUR", 15000), AM("BNB", 1),   dt(2023, 3, 2)),
            ExchangeOperation(AM("BNB", 7.9),   AM("EUR", 700),   AM("BNB", 0.1), dt(2023, 3, 3))
        ]
        for oper in opers:
            self.tassametro.process_operation(oper)
        self.print_state()
        self.assertEqual(len(self.portfolio.get_positions(min_value=0.0001)), 1)
        self.assertAlmostEqual(self.portfolio.get_total("EUR"), self.tassametro.capital_gain)

    def test_double_exchange_3(self):
        opers = [
            ExchangeOperation(AM("EUR", 10000), AM("BTC", 0.5),   AM("EUR", 100),   dt(2023, 1, 1)),  # 1btc = 10000eur
            ExchangeOperation(AM("EUR", 15000), AM("BTC", 0.5),   AM("EUR", 100),    dt(2023, 1, 2)),  # 1btc = 20000eur
            ExchangeOperation(AM("BTC", 0.1),   AM("BNB", 10),    AM("BNB", 0.1),   dt(2023, 2, 1)),  # 1bnb = 100eur
            ExchangeOperation(AM("BTC", 0.9),   AM("ETH", 9),     AM("BNB", 0.9),   dt(2023, 3, 1)),  # 1eth = 1000eur
            ExchangeOperation(AM("ETH", 9),     AM("EUR", 15000), AM("BNB", 1),     dt(2023, 3, 2)),
            ExchangeOperation(AM("BNB", 7.9),   AM("EUR", 700),   AM("BNB", 0.1),   dt(2023, 3, 3))
        ]
        for oper in opers:
            self.tassametro.process_operation(oper)
        self.print_state()
        self.assertEqual(len(self.portfolio.get_positions(min_value=0.001)), 1)
        self.assertAlmostEqual(self.portfolio.get_total("EUR"), self.tassametro.capital_gain)

    def test_double_exchange_4(self):
        opers = [
            ExchangeOperation(AM("EUR", 10000),           AM("BTC", 0.5),   AM("EUR", 100),        dt(2023, 1, 1)),  # 1btc = 20200eur
            ExchangeOperation(AM("EUR", 15000),           AM("BTC", 0.5),   AM("EUR", 100),        dt(2023, 1, 2)),  # 1btc = 30200eur
            ExchangeOperation(AM("BTC", 0.1),             AM("BNB", 10),    AM("BTC", 0.1 * fee),  dt(2023, 2, 1)),  # 1bnb = 100eur
            ExchangeOperation(AM("BTC", 0.9 - 0.1 * fee), AM("ETH", 9),     AM("ETH", 9 * fee),    dt(2023, 3, 1)),  # 1eth = 1000eur
            ExchangeOperation(AM("ETH", 9 - 9 * fee),     AM("EUR", 15000), AM("BNB", 1),          dt(2023, 3, 2)),
            ExchangeOperation(AM("BNB", 8),               AM("EUR", 700),   AM("BNB", 1),          dt(2023, 3, 3))
        ]
        for oper in opers:
            self.tassametro.process_operation(oper)
        self.print_state()
        self.assertEqual(len(self.portfolio.get_positions(min_value=0.001)), 1)
        self.assertAlmostEqual(self.portfolio.get_total("EUR"), self.tassametro.capital_gain)
    
    #def test_double_exchange_5(self):
    #    opers = [
    #        ExchangeOperation(AM("EUR", 10000),         AM("BTC", 1),   AM("EUR", 0),        dt(2023, 1, 1)),  # 1btc = 10100eur
    #        ExchangeOperation(AM("BTC", 0.5),           AM("ETH", 10),   AM("EUR", 0),        dt(2023, 1, 1)),  # 1btc = 10100eur
    #        ExchangeOperation(AM("ETH", 10),            AM("BTC", 2),   AM("EUR", 0),        dt(2023, 1, 1)),  # 1btc = 10100eur
    #    ]
    #    for oper in opers:
    #        self.tassametro.process_operation(oper)
    #    self.print_state()
    #    #self.assertEqual(len(self.portfolio.get_positions(min_value=0.001)), 1)
    #    #self.assertAlmostEqual(self.portfolio.get_total("EUR"), self.tassametro.capital_gain)



if __name__ == '__main__':
    #t = TestTassametro()
    #t.setUp()
    #t.test_double_exchange_5()
    unittest.main(verbosity=2)
