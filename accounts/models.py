from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.utils.crypto import get_random_string


class UserManager(BaseUserManager):
    """Custom user manager using email as the username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("email_verified_at", timezone.now())

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """User model with email-based login, user types, and disable/verify flags."""

    BASIC = "basic"
    PRO = "pro"
    USER_TYPE_CHOICES = [(BASIC, "Basic"), (PRO, "Pro")]

    username = None
    email = models.EmailField(unique=True)
    user_type = models.CharField(
        max_length=10, choices=USER_TYPE_CHOICES, default=BASIC
    )
    is_disabled = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    @property
    def is_verified(self):
        return self.email_verified_at is not None

    def verify_email(self):
        self.email_verified_at = timezone.now()
        self.save(update_fields=["email_verified_at"])


class VerificationCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verification_codes")
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=["user", "code"])]

    @property
    def is_valid(self):
        return self.expires_at >= timezone.now()


class PendingRegistration(models.Model):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    password = models.CharField(max_length=128)  # already hashed
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["code"]),
        ]

    @property
    def is_valid(self):
        return self.expires_at >= timezone.now()


# Create your models here.
