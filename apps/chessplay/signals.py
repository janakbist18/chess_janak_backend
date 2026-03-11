from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.chessplay.services.match_service import get_or_create_match_for_room
from apps.rooms.models import GameRoom


@receiver(post_save, sender=GameRoom)
def ensure_match_for_ready_room(sender, instance, **kwargs):
    if instance.player_white and instance.player_black:
        get_or_create_match_for_room(instance)