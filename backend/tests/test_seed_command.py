from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from accounts.models import User
from tickets.models import Comment, Ticket


def run(**options):
    call_command("seed_demo_data", stdout=StringIO(), **options)


@pytest.mark.django_db
class TestSeedCommand:
    def test_creates_marked_sample_data_with_hashed_passwords(self):
        run(password="seed-test-pw-1", force=True)
        assert User.objects.filter(is_sample_data=True).count() == 6
        assert not User.objects.filter(is_sample_data=False).exists()
        user = User.objects.get(username="dave.agent")
        assert user.email.endswith("@example.test") and user.check_password("seed-test-pw-1")
        assert Ticket.objects.count() >= 10 and Comment.objects.exists()

    def test_is_repeatable_without_duplicates(self):
        run(password="seed-test-pw-1", force=True)
        counts = (User.objects.count(), Ticket.objects.count(), Comment.objects.count())
        run(password="seed-test-pw-1", force=True)
        assert (User.objects.count(), Ticket.objects.count(), Comment.objects.count()) == counts

    def test_requires_a_password(self, monkeypatch):
        monkeypatch.delenv("SEED_PASSWORD", raising=False)
        with pytest.raises(CommandError):
            run(force=True)

    def test_refuses_when_debug_is_off_without_force(self, settings):
        settings.DEBUG = False
        with pytest.raises(CommandError):
            run(password="seed-test-pw-1")
