def score_candidates(left: dict, right: dict) -> float:
    if (
        left.get("platform") == right.get("platform")
        and left.get("external_id")
        and left.get("external_id") == right.get("external_id")
    ):
        return 1.0

    if left.get("display_name") and left.get("display_name") == right.get("display_name"):
        return 0.7

    return 0.1
