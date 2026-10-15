def test_db_roundtrip(user):
    from users.models import User

    assert User.objects.filter(pk=user.pk).exists()
