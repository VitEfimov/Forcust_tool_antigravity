
from src.core.config import settings
print("Targets:", settings.TRAINING_TARGETS)
print("Using 30d?", "30" in str(settings.TRAINING_TARGETS) or "Run Logic" in "Check Code")
