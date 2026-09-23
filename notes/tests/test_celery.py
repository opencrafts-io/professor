from notes.tasks import health_check


def test_health_check_runs_eagerly():
    result = health_check.delay()
    assert result.get(timeout=5) == "ok"
