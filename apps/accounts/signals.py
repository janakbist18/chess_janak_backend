from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import User, UserProfile, ThemePreference


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def create_user_theme_preference(sender, instance, created, **kwargs):
    if created:
        ThemePreference.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        instance.profile.save()