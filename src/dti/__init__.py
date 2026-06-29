"""Drug-target interaction (DTI) prediction module."""
from src.dti.targets import TARGETS, list_targets, get_target_info
from src.dti.predictor import predict_binding_affinity, predict_multi_target_activity

__all__ = [
    "predict_binding_affinity",
    "predict_multi_target_activity",
    "list_targets",
    "get_target_info",
    "TARGETS",
]
