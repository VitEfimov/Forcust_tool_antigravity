
from pathlib import Path
import os
from src.core.config import settings

class TaskController:
    def __init__(self):
        self.control_dir = Path(settings.LOCAL_DATA_DIR) / "control"
        self.control_dir.mkdir(parents=True, exist_ok=True)

    def request_stop(self, task_name: str):
        """Signal a task to stop by creating a flag file."""
        flag_file = self.control_dir / f"STOP_{task_name}"
        flag_file.touch()

    def should_stop(self, task_name: str, consume=False) -> bool:
        """
        Check if a stop signal exists.
        If consume=True, delete the flag after reading.
        """
        flag_file = self.control_dir / f"STOP_{task_name}"
        if flag_file.exists():
            if consume:
                try:
                    flag_file.unlink()
                except:
                    pass
            return True
        return False

    def clear_stop(self, task_name: str):
        """Clear the stop signal manually."""
        flag_file = self.control_dir / f"STOP_{task_name}"
        if flag_file.exists():
            try:
                flag_file.unlink()
            except:
                pass

# Global Instance
task_controller = TaskController()
