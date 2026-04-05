from enum import Enum


class ActivationState(str, Enum):
    INACTIVE = "inactive"
    LATENT = "latent"
    EXPLICIT = "explicit"


class ResponseMode(str, Enum):
    SINGLE_PRIMARY = "single_primary"
    PRIMARY_PLUS_SUPPORT = "primary_plus_support"
    MULTI_PARALLEL = "multi_parallel"
