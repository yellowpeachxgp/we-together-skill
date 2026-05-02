from enum import StrEnum


class ActivationState(StrEnum):
    INACTIVE = "inactive"
    LATENT = "latent"
    EXPLICIT = "explicit"


class ResponseMode(StrEnum):
    SINGLE_PRIMARY = "single_primary"
    PRIMARY_PLUS_SUPPORT = "primary_plus_support"
    MULTI_PARALLEL = "multi_parallel"
