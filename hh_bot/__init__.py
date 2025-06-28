__version__ = "2.0.0"
__author__ = "HH Bot Team"

from .core.job_application_manager import JobApplicationManager
from .config.settings import settings

__all__ = ["JobApplicationManager", "settings"]
