import uuid
from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email=None, username=None, password=None, device_id=None, is_anonymous=False, **extra_fields):
        """Create a user with either email/username (authenticated) or device_id (anonymous)"""
        # Anonymous users require device_id
        if is_anonymous:
            if not device_id:
                device_id = str(uuid.uuid4())
            # Auto-generate email and username for anonymous users
            if not email:
                email = f"anonymous_{device_id[:8]}@anonymous.local"
            if not username:
                username = f"anon_{device_id[:8]}"
        else:
            # Authenticated users require email and username
            if not email:
                raise ValueError("The email field must be set for authenticated users.")
            if not username:
                raise ValueError("The username field must be set for authenticated users.")

        email = self.normalize_email(email) if email else email
        user = self.model(email=email, username=username, device_id=device_id, is_anonymous=is_anonymous, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_user(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", False)
        return self._create_user(email=email, username=username, password=password, **extra_fields)

    def create_anonymous_user(self, device_id=None, **extra_fields):
        """Create an anonymous user linked to a device_id"""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)  # Anonymous users are active by default
        extra_fields.setdefault("is_verified", True)  # Anonymous users don't need verification
        extra_fields.setdefault("is_anonymous", True)
        return self._create_user(device_id=device_id, is_anonymous=True, **extra_fields)

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email=email, username=username, password=password, **extra_fields)