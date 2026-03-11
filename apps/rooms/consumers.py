import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db import models

from apps.chessplay.services.chess_engine_service import (
    ChessMoveError,
    apply_move,
    offer_draw,
    respond_draw,
    resign_match,
)
from apps.rooms.models import GameRoom, RoomParticipant
from apps.rooms.ws_serializers import serialize_room_state


class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"room_{self.room_id}"

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.room = await self.get_room()
        if not self.room:
            await self.close(code=4004)
            return

        is_participant = await self.is_user_room_participant()
        if not is_participant:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.mark_participant_joined()

        await self.send_json(
            {
                "type": "connection.established",
                "message": "WebSocket connected successfully.",
                "room_id": self.room_id,
                "user_id": self.user.id,
            }
        )

        await self.broadcast_room_state(event_name="presence.joined")

    async def disconnect(self, close_code):
        user = getattr(self, "user", None)
        room_id = getattr(self, "room_id", None)

        if user and getattr(user, "is_authenticated", False) and room_id:
            await self.mark_participant_left()
            await self.broadcast_room_state(event_name="presence.left")

        room_group_name = getattr(self, "room_group_name", None)
        if room_group_name:
            await self.channel_layer.group_discard(room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON payload.")
            return

        event_type = payload.get("type")
        if not event_type:
            await self.send_error("Missing event type.")
            return

        handlers = {
            "presence.ping": self.handle_presence_ping,
            "chat.message": self.handle_chat_message,
            "chat.typing": self.handle_chat_typing,
            "chess.move": self.handle_chess_move,
            "chess.resign": self.handle_chess_resign,
            "chess.draw_offer": self.handle_chess_draw_offer,
            "chess.draw_response": self.handle_chess_draw_response,
            "call.offer": self.handle_call_offer,
            "call.answer": self.handle_call_answer,
            "call.ice_candidate": self.handle_call_ice_candidate,
            "call.end": self.handle_call_end,
        }

        handler = handlers.get(event_type)
        if not handler:
            await self.send_error(f"Unsupported event type: {event_type}")
            return

        await handler(payload)

    async def handle_presence_ping(self, payload):
        await self.mark_participant_ping()
        await self.send_json(
            {
                "type": "presence.pong",
                "message": "Presence updated.",
            }
        )
        await self.broadcast_room_state(event_name="presence.updated")

    async def handle_chat_message(self, payload):
        message = str(payload.get("message", "")).strip()
        if not message:
            await self.send_error("Message cannot be empty.")
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "room.event",
                "payload": {
                    "type": "chat.message",
                    "message": message,
                    "sender": await self.get_safe_user_payload(),
                    "room_id": self.room_id,
                },
            },
        )

    async def handle_chat_typing(self, payload):
        is_typing = bool(payload.get("is_typing", False))
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "room.event",
                "payload": {
                    "type": "chat.typing",
                    "is_typing": is_typing,
                    "sender": await self.get_safe_user_payload(),
                    "room_id": self.room_id,
                },
            },
        )

    async def handle_chess_move(self, payload):
        move_from = payload.get("from")
        move_to = payload.get("to")
        promotion = payload.get("promotion")

        if not move_from or not move_to:
            await self.send_error("Both 'from' and 'to' are required for a move.")
            return

        try:
            result = await self.apply_move_sync(move_from, move_to, promotion)
        except ChessMoveError as exc:
            await self.send_error(str(exc))
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "room.event",
                "payload": {
                    "type": "chess.move.applied",
                    "move": result["move"],
                    "match": result["match"],
                    "room_id": self.room_id,
                    "sender": await self.get_safe_user_payload(),
                },
            },
        )

        await self.broadcast_room_state(event_name="chess.state.updated")

    async def handle_chess_resign(self, payload):
        try:
            result = await self.resign_match_sync()
        except ChessMoveError as exc:
            await self.send_error(str(exc))
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "room.event",
                "payload": {
                    "type": "chess.resigned",
                    "match": result["match"],
                    "winner_id": result["winner_id"],
                    "room_id": self.room_id,
                    "sender": await self.get_safe_user_payload(),
                },
            },
        )

        await self.broadcast_room_state(event_name="chess.state.updated")

    async def handle_chess_draw_offer(self, payload):
        try:
            result = await self.offer_draw_sync()
        except ChessMoveError as exc:
            await self.send_error(str(exc))
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "room.event",
                "payload": {
                    "type": "chess.draw_offer",
                    "match": result["match"],
                    "offered_by_id": result["offered_by_id"],
                    "room_id": self.room_id,
                    "sender": await self.get_safe_user_payload(),
                },
            },
        )

    async def handle_chess_draw_response(self, payload):
        accepted = bool(payload.get("accepted", False))

        try:
            result = await self.respond_draw_sync(accepted)
        except ChessMoveError as exc:
            await self.send_error(str(exc))
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "room.event",
                "payload": {
                    "type": "chess.draw_response",
                    "accepted": result["accepted"],
                    "match": result["match"],
                    "room_id": self.room_id,
                    "sender": await self.get_safe_user_payload(),
                },
            },
        )

        await self.broadcast_room_state(event_name="chess.state.updated")

    async def handle_call_offer(self, payload):
        sdp = payload.get("sdp")
        if not sdp:
            await self.send_error("Missing SDP offer.")
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "room.event",
                "payload": {
                    "type": "call.offer",
                    "sdp": sdp,
                    "sender": await self.get_safe_user_payload(),
                    "room_id": self.room_id,
                },
            },
        )

    async def handle_call_answer(self, payload):
        sdp = payload.get("sdp")
        if not sdp:
            await self.send_error("Missing SDP answer.")
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "room.event",
                "payload": {
                    "type": "call.answer",
                    "sdp": sdp,
                    "sender": await self.get_safe_user_payload(),
                    "room_id": self.room_id,
                },
            },
        )

    async def handle_call_ice_candidate(self, payload):
        candidate = payload.get("candidate")
        if not candidate:
            await self.send_error("Missing ICE candidate.")
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "room.event",
                "payload": {
                    "type": "call.ice_candidate",
                    "candidate": candidate,
                    "sender": await self.get_safe_user_payload(),
                    "room_id": self.room_id,
                },
            },
        )

    async def handle_call_end(self, payload):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "room.event",
                "payload": {
                    "type": "call.end",
                    "sender": await self.get_safe_user_payload(),
                    "room_id": self.room_id,
                },
            },
        )

    async def room_event(self, event):
        await self.send_json(event["payload"])

    async def room_state_event(self, event):
        await self.send_json(event["payload"])

    async def send_error(self, message: str):
        await self.send_json(
            {
                "type": "error",
                "message": message,
            }
        )

    async def send_json(self, payload: dict):
        await self.send(text_data=json.dumps(payload))

    @sync_to_async
    def get_room(self):
        return (
            GameRoom.objects.select_related("host", "player_white", "player_black", "winner")
            .prefetch_related("participants", "participants__user", "participants__user__profile")
            .filter(id=self.room_id, is_active=True)
            .first()
        )

    @sync_to_async
    def is_user_room_participant(self):
        room = (
            GameRoom.objects.filter(id=self.room_id, is_active=True)
            .filter(
                models.Q(host=self.user)
                | models.Q(player_white=self.user)
                | models.Q(player_black=self.user)
            )
            .first()
        )
        if room:
            return True
        return RoomParticipant.objects.filter(room_id=self.room_id, user=self.user).exists()

    @sync_to_async
    def mark_participant_joined(self):
        participant = RoomParticipant.objects.filter(room_id=self.room_id, user=self.user).first()
        if participant:
            participant.mark_joined()

    @sync_to_async
    def mark_participant_left(self):
        participant = RoomParticipant.objects.filter(room_id=self.room_id, user=self.user).first()
        if participant:
            participant.mark_left()

    @sync_to_async
    def mark_participant_ping(self):
        participant = RoomParticipant.objects.filter(room_id=self.room_id, user=self.user).first()
        if participant:
            participant.mark_ping()

    @sync_to_async
    def get_safe_user_payload(self):
        profile_image_url = None
        if self.user.profile_image:
            try:
                profile_image_url = self.user.profile_image.url
            except Exception:
                profile_image_url = None

        return {
            "id": self.user.id,
            "email": self.user.email,
            "username": self.user.username,
            "name": self.user.name,
            "profile_image_url": profile_image_url,
        }

    @sync_to_async
    def get_serialized_room_state(self):
        room = (
            GameRoom.objects.select_related("host", "player_white", "player_black", "winner")
            .prefetch_related("participants", "participants__user", "participants__user__profile")
            .get(id=self.room_id)
        )
        return serialize_room_state(room)

    @sync_to_async
    def apply_move_sync(self, move_from, move_to, promotion):
        room = GameRoom.objects.get(id=self.room_id)
        return apply_move(room, self.user, move_from, move_to, promotion)

    @sync_to_async
    def resign_match_sync(self):
        room = GameRoom.objects.get(id=self.room_id)
        return resign_match(room, self.user)

    @sync_to_async
    def offer_draw_sync(self):
        room = GameRoom.objects.get(id=self.room_id)
        return offer_draw(room, self.user)

    @sync_to_async
    def respond_draw_sync(self, accepted):
        room = GameRoom.objects.get(id=self.room_id)
        return respond_draw(room, self.user, accepted)

    async def broadcast_room_state(self, event_name: str):
        room_state = await self.get_serialized_room_state()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "room.state.event",
                "payload": {
                    "type": event_name,
                    "room": room_state,
                },
            },
        )