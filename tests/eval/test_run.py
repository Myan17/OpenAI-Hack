from eval.run import run_eval


def test_golden_eval_passes() -> None:
    scorecard = run_eval()
    assert scorecard["pass"] is True
    assert scorecard["halted_bad"] == 15
    assert scorecard["allowed_good"] == 10
