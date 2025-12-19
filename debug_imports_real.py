
import sys
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

print("--- Debugging Imports ---")

print("\n1. Importing src.models.walk_forward...")
try:
    from src.models.walk_forward import WalkForwardForecaster
    print("✅ Success")
except ImportError:
    print("❌ Failed:")
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error: {e}")
    traceback.print_exc()

print("\n2. Importing src.models.advanced_simulation...")
try:
    from src.models.advanced_simulation import AdvancedSimulator
    print("✅ Success")
except ImportError:
    print("❌ Failed:")
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error: {e}")
    traceback.print_exc()
