from notes.tasks import health_check, run_generation
from professor.celery import app


def test_health_check_runs_eagerly():
    result = health_check.delay()
    assert result.get(timeout=5) == "ok"


def test_generation_tasks_route_to_professor_queue():
    route = app.amqp.router.route({}, run_generation.name, args=(1,), kwargs={})
    assert route["queue"].name == "professor"
