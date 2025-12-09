
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
from datetime import datetime
from src.api import routes

def test_persistent_cache_hit(tmp_path):
    """Test that _compute_market_overview loads from file if present."""
    
    # Patch attributes on the routes module directly
    with patch.object(routes, 'settings') as mock_settings, \
         patch.object(routes, 'get_market_overview_logic') as mock_logic, \
         patch.object(routes, '_compute_advanced_simulation') as mock_sim:

        # Setup mock directory
        mock_settings.LOCAL_DATA_DIR = str(tmp_path)
        save_dir = tmp_path / "market_overviews"
        save_dir.mkdir()
        
        # Create a "today" file
        today_str = datetime.now().strftime("%Y%m%d")
        fake_data = {"overview": [{"symbol": "TEST", "price": 100, "source": "cache"}]}
        
        # Make a file with a timestamp
        filename = f"overview_{today_str}_100000.json"
        with open(save_dir / filename, "w") as f:
            json.dump(fake_data, f)
            
        # Call function
        result = routes._compute_market_overview(["TEST"])
        
        # Verify
        assert result == fake_data
        assert result["overview"][0]["source"] == "cache"
        
        # Ensure logic/sim were NOT called
        mock_logic.assert_not_called()
        mock_sim.assert_not_called()
def test_persistent_cache_miss(tmp_path):
    """Test that it falls back to fetch if no file exists."""
    
    with patch.object(routes, 'settings') as mock_settings, \
         patch.object(routes, 'get_market_overview_logic') as mock_logic, \
         patch.object(routes, '_compute_advanced_simulation') as mock_sim:
    
        mock_settings.LOCAL_DATA_DIR = str(tmp_path)
        # No file created
        
        # Setup fallback mocks
        mock_logic.return_value = {"overview": [{"symbol": "FALLBACK", "price": 50}]}
        mock_sim.return_value = {
            "analysis": {
                30: {"risk_label": "Low", "volatility_outlook": "Stable", "median_change_pct": 0.01},
                10: {"median_change_pct": 0.01},
                100: {"median_change_pct": 0.01},
                365: {"median_change_pct": 0.01},
                547: {"median_change_pct": 0.01},
                730: {"median_change_pct": 0.01}
            },
            "current_regime": {"label": "Bull"}
        }
        
        # Call function
        result = routes._compute_market_overview(["FALLBACK"])
        
        # Verify
        assert result["overview"][0]["symbol"] == "FALLBACK"
        assert result["overview"][0]["risk_label"] == "Low"
        
        # Ensure logic WAS called
        mock_logic.assert_called_once()
