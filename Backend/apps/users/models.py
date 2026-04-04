"""
Custom User model with RBAC (Role-Based Access Control).

Design decisions:
- Extend AbstractBaseUser for full control (not AbstractUser which forces username)
- Use email as primary identifier (more user-friendly than username)
- Roles are first-class objects, not just groups (enables fine-grained permissions)
- Multi-tenancy ready: Organization FK on User (add in Phase 10)
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str = None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Platform user. Roles determine what APIs they can call.
    """

    class Role(models.TextChoices):
        ADMIN    = "ADMIN",    "Administrator"   # Full access
        ANALYST  = "ANALYST",  "Analyst"         # View + create rules/alerts
        VIEWER   = "VIEWER",   "Viewer"          # Read-only access
        API_USER = "API_USER", "API User"        # Service accounts (log shippers)

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email      = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name  = models.CharField(max_length=100, blank=True)
    role       = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)

    # API key for programmatic access (log shippers use this)
    api_key    = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)

    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Future: organization = models.ForeignKey("Organization", ...)

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "users"
        indexes  = [models.Index(fields=["email", "is_active"])]

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def generate_api_key(self) -> str:
        """Generate and store a new API key. Returns the plain-text key."""
        import secrets
        key = secrets.token_urlsafe(48)
        self.api_key = key
        self.save(update_fields=["api_key"])
        return key