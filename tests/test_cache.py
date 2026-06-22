import sys
import os
import unittest
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.cache import PredictionCache

class TestPredictionCache(unittest.TestCase):

    def setUp(self):
        PredictionCache.clear()

    def test_cache_set_and_get(self):
        key = PredictionCache.make_key(28.61, 77.20, 2030, 6, temp_delta=1.5)
        mock_pred = {"temperature": 32.5, "rainfall": 15.0}
        
        # Test cache miss
        self.assertIsNone(PredictionCache.get(key))
        
        # Set cache
        PredictionCache.set(key, mock_pred, ttl=5)
        
        # Test cache hit
        cached_val = PredictionCache.get(key)
        self.assertEqual(cached_val, mock_pred)

    def test_cache_ttl_expiration(self):
        key = PredictionCache.make_key(28.61, 77.20, 2030, 6)
        mock_pred = {"drought": "High"}
        
        # Set cache with 1-second TTL
        PredictionCache.set(key, mock_pred, ttl=1)
        
        # Immediate check (hit)
        self.assertEqual(PredictionCache.get(key), mock_pred)
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Check (expired miss)
        self.assertIsNone(PredictionCache.get(key))

    def test_cache_key_uniqueness(self):
        # Different coords
        key1 = PredictionCache.make_key(28.61, 77.20, 2030, 6)
        key2 = PredictionCache.make_key(28.62, 77.20, 2030, 6)
        self.assertNotEqual(key1, key2)

        # Different deltas
        key3 = PredictionCache.make_key(28.61, 77.20, 2030, 6, temp_delta=0.0)
        key4 = PredictionCache.make_key(28.61, 77.20, 2030, 6, temp_delta=1.0)
        self.assertNotEqual(key3, key4)

if __name__ == "__main__":
    unittest.main()
