"""Unit tests for Exit Manager module."""
import unittest
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multi_broker_phoenix.risk.exit_manager import (
    pip_size,
    current_profit_pips,
    get_config,
    ExitManager,
)


class TestExitManagerPipMath(unittest.TestCase):
    """Test pip calculations in exit manager."""
    
    def test_pip_size_standard(self):
        """Standard pairs have 0.0001 pip."""
        self.assertEqual(pip_size('EUR_USD'), 0.0001)
        self.assertEqual(pip_size('GBP_USD'), 0.0001)
        self.assertEqual(pip_size('AUD_USD'), 0.0001)
    
    def test_pip_size_jpy(self):
        """JPY pairs have 0.01 pip."""
        self.assertEqual(pip_size('USD_JPY'), 0.01)
        self.assertEqual(pip_size('EUR_JPY'), 0.01)
        self.assertEqual(pip_size('GBP_JPY'), 0.01)
    
    def test_pip_size_formats(self):
        """Various pair formats work."""
        self.assertEqual(pip_size('eur_usd'), 0.0001)
        self.assertEqual(pip_size('EUR-USD'), 0.0001)
        self.assertEqual(pip_size('EUR/USD'), 0.0001)


class TestCurrentProfitPips(unittest.TestCase):
    """Test profit calculation in pips."""
    
    def test_long_profit(self):
        """Long position in profit."""
        pos = {'instrument': 'EUR_USD', 'side': 'long', 'averagePrice': '1.1000'}
        profit = current_profit_pips(pos, 1.1030)  # 30 pips up
        self.assertAlmostEqual(profit, 30.0, places=1)
    
    def test_long_loss(self):
        """Long position at loss."""
        pos = {'instrument': 'EUR_USD', 'side': 'long', 'averagePrice': '1.1000'}
        profit = current_profit_pips(pos, 1.0970)  # 30 pips down
        self.assertAlmostEqual(profit, -30.0, places=1)
    
    def test_short_profit(self):
        """Short position in profit."""
        pos = {'instrument': 'EUR_USD', 'side': 'short', 'averagePrice': '1.1000'}
        profit = current_profit_pips(pos, 1.0970)  # 30 pips down = profit
        self.assertAlmostEqual(profit, 30.0, places=1)
    
    def test_short_loss(self):
        """Short position at loss."""
        pos = {'instrument': 'EUR_USD', 'side': 'short', 'averagePrice': '1.1000'}
        profit = current_profit_pips(pos, 1.1030)  # 30 pips up = loss
        self.assertAlmostEqual(profit, -30.0, places=1)
    
    def test_jpy_pair_profit(self):
        """JPY pair profit calculation."""
        pos = {'instrument': 'USD_JPY', 'side': 'long', 'averagePrice': '150.00'}
        profit = current_profit_pips(pos, 150.50)  # 50 pips up
        self.assertAlmostEqual(profit, 50.0, places=1)


class TestExitManagerConfig(unittest.TestCase):
    """Test configuration retrieval."""
    
    def test_default_config(self):
        """Default config has expected keys."""
        config = get_config()
        self.assertIn('PROFIT_LOCK_PIPS', config)
        self.assertIn('TRAILING_START_PIPS', config)
        self.assertIn('TRAILING_DISTANCE_PIPS', config)
        self.assertIn('MAX_TRADE_HOURS', config)
        self.assertIn('ENABLE_PROFIT_LOCK', config)
        self.assertIn('ENABLE_TRAILING', config)
    
    def test_default_values(self):
        """Default values are reasonable."""
        config = get_config()
        self.assertGreater(config['PROFIT_LOCK_PIPS'], 0)
        self.assertGreater(config['TRAILING_START_PIPS'], config['PROFIT_LOCK_PIPS'])
        self.assertGreater(config['MAX_TRADE_HOURS'], 0)


class TestExitManagerInit(unittest.TestCase):
    """Test Exit Manager initialization."""
    
    def test_init_with_mock_connector(self):
        """Can initialize with mock connector."""
        class MockConnector:
            account_id = 'test-account'
        
        em = ExitManager(MockConnector())
        self.assertIsNotNone(em)
        self.assertEqual(em.account_id, 'test-account')
        self.assertFalse(em._running)


if __name__ == '__main__':
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
