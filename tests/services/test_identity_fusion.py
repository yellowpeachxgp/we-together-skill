from we_together.services.identity_fusion_service import score_candidates


def test_score_candidates_prefers_strong_match():
    score = score_candidates(
        left={"platform": "email", "external_id": "a@example.com", "display_name": "Alice"},
        right={
            "platform": "email",
            "external_id": "a@example.com",
            "display_name": "Alice Zhang",
        },
    )
    assert score >= 0.9
