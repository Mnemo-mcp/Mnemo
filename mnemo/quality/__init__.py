"""Code quality analysis modules."""

from .security import check_security, add_security_pattern
from .conventions import check_conventions, detect_conventions
from .drift import detect_drift
from .health import calculate_health, system_health
from .dead_code import detect_dead_code
from .breaking import detect_breaking_changes, save_baseline
from .regressions import add_regression, check_regressions, list_regressions

__all__ = [
    "check_security", "add_security_pattern",
    "check_conventions", "detect_conventions",
    "detect_drift",
    "calculate_health", "system_health",
    "detect_dead_code",
    "detect_breaking_changes", "save_baseline",
    "add_regression", "check_regressions", "list_regressions",
]
