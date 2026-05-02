from we_together.services.onboarding_flow import (
    PROMPTS,
    STEP_ORDER,
    OnboardingState,
    next_step,
    run_all,
)


def test_full_happy_path():
    st = run_all([None, "1", None, "family", "你们最近好吗"])
    assert st.step == "DONE"
    assert st.data["import_mode"] == "narration"
    assert st.data["scene_name"] == "family"
    assert st.data["first_input"] == "你们最近好吗"


def test_default_answers():
    st = run_all([None, None, None, None, None])
    assert st.step == "DONE"
    assert st.data["import_mode"] == "skip"
    assert st.data["scene_name"] == "my-first-scene"
    assert st.data["first_input"] == "hi"


def test_step_order_covered():
    visited: list[str] = []
    state = OnboardingState()
    while state.step != "DONE":
        visited.append(state.step)
        state = next_step(state, None)
    visited.append(state.step)
    assert visited == STEP_ORDER


def test_prompts_present_for_every_step():
    for step in STEP_ORDER:
        assert step in PROMPTS
