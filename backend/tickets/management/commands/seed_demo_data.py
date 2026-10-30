"""
Populate a LOCAL development database with clearly-marked sample data.

    python manage.py seed_demo_data                # password from SEED_PASSWORD in .env
    python manage.py seed_demo_data --password '...'

Safe to run repeatedly: every record is looked up first (get_or_create), so nothing is duplicated.
Safety rules: refuses to run when DEBUG is off (unless --force), requires you to choose the password
(no default credentials exist anywhere in this repo), and flags every account is_sample_data=True with an
@example.test email so sample rows can never be mistaken for real ones.
"""
import os
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from tickets.models import Comment, Ticket

USERS = [
    # (username, role, first, last)
    ("alice.customer", "customer", "Alice", "Nguyen"),
    ("bob.customer", "customer", "Bob", "Okafor"),
    ("carol.customer", "customer", "Carol", "Mendes"),
    ("dave.agent", "agent", "Dave", "Kimani"),
    ("erin.agent", "agent", "Erin", "Larsen"),
    ("frank.admin", "admin", "Frank", "Osei"),
]

# (title, description, priority, status, creator, assignee, days_ago, [(author, body, internal), ...])
TICKETS = [
    ("Cannot log in after password reset", "I reset my password but the new one is rejected on the login page.", "high", "open", "alice.customer", None, 1, []),
    ("Invoice PDF is blank", "Downloading invoice #1042 gives an empty PDF file every time.", "medium", "in_progress", "alice.customer", "dave.agent", 3,
        [("dave.agent", "Reproduced. Looking into the PDF renderer.", False), ("dave.agent", "Likely the font cache; checking logs.", True)]),
    ("Export to CSV times out", "Exporting more than 5,000 rows fails with a gateway timeout.", "high", "in_progress", "bob.customer", "erin.agent", 5,
        [("erin.agent", "Can you tell me roughly how many rows you export?", False), ("bob.customer", "About 8,000 rows.", False)]),
    ("Typo on pricing page", "The word 'Enterprize' is misspelled on the pricing page.", "low", "resolved", "bob.customer", "dave.agent", 9,
        [("dave.agent", "Fixed and deployed. Please confirm.", False)]),
    ("Request: dark mode", "It would be great to have a dark theme for night shifts.", "low", "open", "carol.customer", None, 2, []),
    ("Two-factor codes never arrive", "SMS codes do not arrive on my phone, so I am locked out.", "urgent", "open", "carol.customer", None, 0, []),
    ("Billing address won't save", "Saving my billing address shows a spinner forever.", "medium", "closed", "alice.customer", "erin.agent", 14,
        [("erin.agent", "Cleared a corrupted profile record. Works now.", False), ("alice.customer", "Confirmed, thanks!", False)]),
    ("Email notifications duplicated", "I get every notification email twice.", "medium", "in_progress", "carol.customer", "dave.agent", 6,
        [("dave.agent", "Found two webhooks registered for your account.", False)]),
    ("Mobile layout overlaps buttons", "On my phone the Save and Cancel buttons overlap.", "low", "open", "bob.customer", None, 4, []),
    ("Cannot delete old attachments", "The delete icon does nothing on attachments older than 2025.", "medium", "resolved", "alice.customer", "erin.agent", 11,
        [("erin.agent", "Permissions bug on legacy files, patched.", False)]),
    ("Search returns no results", "Searching for 'refund' returns nothing even though I have refund tickets.", "high", "open", "bob.customer", None, 1, []),
    ("Account shows wrong timezone", "My dashboard times are 5 hours off.", "low", "closed", "carol.customer", "dave.agent", 18,
        [("dave.agent", "Timezone setting was UTC; changed to your region.", False)]),
]


class Command(BaseCommand):
    help = "Create repeatable sample users, tickets and comments for local development."

    def add_arguments(self, parser):
        parser.add_argument("--password", help="Password for ALL sample accounts (default: $SEED_PASSWORD).")
        parser.add_argument("--force", action="store_true", help="Allow running when DEBUG is False (not recommended).")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Refusing to seed data while DEBUG is off. This command is for local development only.")
        password = options.get("password") or os.environ.get("SEED_PASSWORD")
        if not password:
            raise CommandError("Provide --password or set SEED_PASSWORD in .env. No default password exists on purpose.")

        users = {}
        created_users = 0
        for username, role, first, last in USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.test",
                    "first_name": first,
                    "last_name": last,
                    "role": role,
                    "is_staff": role == "admin",  # may log into /admin/
                    "is_sample_data": True,
                },
            )
            if created:
                user.set_password(password)  # hashed; the plain text is never stored
                user.save()
                created_users += 1
            users[username] = user

        created_tickets = created_comments = 0
        now = timezone.now()
        for title, description, priority, status, creator, assignee, days_ago, comments in TICKETS:
            ticket, created = Ticket.objects.get_or_create(
                title=title,
                created_by=users[creator],
                defaults={
                    "description": description,
                    "priority": priority,
                    "status": status,
                    "assigned_to": users[assignee] if assignee else None,
                    "updated_by": users[assignee or creator],
                    "closed_at": now - timedelta(days=max(days_ago - 1, 0)) if status == "closed" else None,
                },
            )
            if created:
                created_tickets += 1
                # created_at is auto_now_add, so backdate with a queryset update (skips auto fields).
                Ticket.objects.filter(pk=ticket.pk).update(created_at=now - timedelta(days=days_ago))
            for author, body, internal in comments:
                _, made = Comment.objects.get_or_create(
                    ticket=ticket, author=users[author], body=body, defaults={"is_internal": internal}
                )
                created_comments += int(made)

        self.stdout.write(self.style.SUCCESS(
            f"Sample data ready: +{created_users} users, +{created_tickets} tickets, +{created_comments} comments "
            f"(existing rows were left untouched)."
        ))
        self.stdout.write("Sample logins: alice.customer, dave.agent, frank.admin (password = the one you supplied).")
