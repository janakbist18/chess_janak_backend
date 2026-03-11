from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.rooms.models import GameRoom, RoomParticipant


@receiver(post_save, sender=RoomParticipant)
def sync_room_status_on_participant_save(sender, instance, **kwargs):
    room = instance.room

    if room.player_white and room.player_black:
        if room.status == GameRoom.STATUS_WAITING:
            room.status = GameRoom.STATUS_READY
            room.save(update_fields=["status", "updated_at"])
    else:
        if room.status == GameRoom.STATUS_READY:
            room.status = GameRoom.STATUS_WAITING
            room.save(update_fields=["status", "updated_at"])


@receiver(post_delete, sender=RoomParticipant)
def sync_room_status_on_participant_delete(sender, instance, **kwargs):
    room = instance.room
    if not room.participants.exists():
        room.is_active = False
        room.status = GameRoom.STATUS_CANCELLED
        room.save(update_fields=["is_active", "status", "updated_at"])