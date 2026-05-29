# ai_engine/__init__.py
from .predictor_fixed import fixed_predictor as predictor

# Also export the fixed predictor directly
from .predictor_fixed import FixedDrugPredictor

__all__ = ['predictor', 'FixedDrugPredictor']