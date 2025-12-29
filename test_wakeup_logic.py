from unittest.mock import patch, MagicMock
import sys
import os
from pathlib import Path

# Fix path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

from src.core.scheduler import wakeup_server

def test_wakeup_success():
    print("\n--- Test: Wakeup Success ---")
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        result = wakeup_server()
        assert result == True
        print("Success: wakeup_server returned True immediately.")

def test_wakeup_retry_fail():
    print("\n--- Test: Wakeup Retry & Fail ---")
    # We want to mock sleep to be fast
    with patch('requests.get') as mock_get, patch('time.sleep') as mock_sleep:
        # Simulate 5 failures
        mock_get.side_effect = Exception("Connection Refused")
        
        result = wakeup_server()
        assert result == False
        assert mock_get.call_count == 5
        print("Success: wakeup_server retried 5 times and returned False.")

def test_wakeup_retry_success():
    print("\n--- Test: Wakeup Retry then Success ---")
    with patch('requests.get') as mock_get, patch('time.sleep') as mock_sleep:
        # Fail 2 times, then succeed
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.side_effect = [Exception("Fail 1"), Exception("Fail 2"), mock_resp]
        
        result = wakeup_server()
        assert result == True
        assert mock_get.call_count == 3
        print("Success: wakeup_server succeeded on attempt 3.")

if __name__ == "__main__":
    try:
        test_wakeup_success()
        test_wakeup_retry_fail()
        test_wakeup_retry_success()
        print("\nAll Wakeup Logic Tests Passed!")
    except Exception as e:
        print(f"\nTest Failed: {e}")
