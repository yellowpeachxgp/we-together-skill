def mark_latent(participants: list[dict]) -> list[dict]:
    result = []
    for item in participants:
        copied = dict(item)
        copied.setdefault("activation_state", "latent")
        result.append(copied)
    return result
