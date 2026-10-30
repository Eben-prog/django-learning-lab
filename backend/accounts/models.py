from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    """
    Custom user model. We extend Django's AbstractUser so we keep its password hashing,
    `is_active`, groups/permissions, admin integration and login machinery, and add:

    * a unique email address
    * a `role` that drives role-based access control (customer / agent / admin)

    Java analogy: a JPA entity `User extends BaseUser`, where the base class is provided by the framework.
    """

    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        AGENT = "agent", "Support agent"
        ADMIN = "admin", "Administrator"

    email = models.EmailField("email address", unique=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.CUSTOMER)
    # Marks rows created by `manage.py seed_demo_data` so they can never be confused with real accounts.
    is_sample_data = models.BooleanField(default=False, help_text="Created by the development seed command.")

    class Meta(AbstractUser.Meta):
        constraints = [
            # The database itself rejects an invalid role, even if buggy code or a manual SQL statement tries it.
            models.CheckConstraint(
                condition=Q(role__in=["customer", "agent", "admin"]),
                name="user_role_valid",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()  # emails are unique case-insensitively in practice
        if self.is_superuser:
            self.role = self.Role.ADMIN  # `createsuperuser` should produce an admin-role user
        super().save(*args, **kwargs)

    @property
    def is_support_staff(self) -> bool:
        """True for agents and admins."""
        return self.role in (self.Role.AGENT, self.Role.ADMIN)

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.Role.ADMIN
