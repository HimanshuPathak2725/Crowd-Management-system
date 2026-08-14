"""Hugging Face powered crowd density forecasting."""
from __future__ import annotations

from typing import List
import logging

logger = logging.getLogger(__name__)


class HFForecaster:
    """HF Time-series forecaster with statistical fallback."""

    def __init__(self, model_id: str | None = None):
        self.model_id = model_id
        self._pipe = None
        if model_id:
            try:
                from transformers import pipeline
                self._pipe = pipeline("time-series-forecasting", model=model_id)
                logger.info(f"Loaded HF model: {model_id}")
            except Exception as exc:
                logger.warning(f"HF model load failed: {exc}. Using statistical fallback.")

    def predict(self, history: List[float], horizon: int = 15) -> List[float]:
        if self._pipe is not None and len(history) >= 8:
            try:
                # HF prediction placeholder — extend with actual inference
                return self._statistical_predict(history, horizon)
            except Exception as exc:
                logger.error(f"HF inference failed: {exc}")
                return self._statistical_predict(history, horizon)
        return self._statistical_predict(history, horizon)

    @staticmethod
    def _statistical_predict(history: List[float], horizon: int) -> List[float]:
        if not history:
            return [0.0] * horizon
        recent = history[-min(8, len(history)):]
        level = recent[-1]
        slope = (recent[-1] - recent[0]) / max(len(recent) - 1, 1)
        return [max(0.0, level + slope * t * 0.75) for t in range(1, horizon + 1)]
