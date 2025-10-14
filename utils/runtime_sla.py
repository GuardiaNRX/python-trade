"""
Moduł runtime SLA: budżet czasu + degradacja przy przekroczeniu.
"""
import time
from typing import Dict


class RuntimeBudget:
    """Zarządzanie budżetem czasu wykonania pipeline."""

    def __init__(self, max_total_sec: int = 1200, degrade_threshold: float = 0.9):
        """
        Inicjalizacja.

        Args:
            max_total_sec: Maksymalny czas total (sekundy)
            degrade_threshold: Próg degradacji (frakcja max_total_sec)
        """
        self.t0 = time.time()
        self.max_total = max_total_sec
        self.degrade_threshold = degrade_threshold
        self.steps: Dict[str, float] = {}

    def start(self, name: str) -> None:
        """Rozpoczyna pomiar kroku."""
        self.steps[name] = time.time()

    def end(self, name: str) -> None:
        """Kończy pomiar kroku."""
        self.steps[name] = time.time() - self.steps.get(name, time.time())

    @property
    def elapsed(self) -> float:
        """Zwraca upłynięty czas (sekundy)."""
        return time.time() - self.t0

    def should_degrade(self) -> bool:
        """Sprawdza czy przekroczono próg degradacji."""
        return self.elapsed >= self.max_total * self.degrade_threshold

    def left(self) -> float:
        """Zwraca pozostały czas (sekundy)."""
        return max(0.0, self.max_total - self.elapsed)
