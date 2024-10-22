import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Room, Message
from django.contrib.auth.models import User
from asgiref.sync import sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data: dict = json.loads(text_data)
        message: Message = data['message']
        user: User = self.scope['user']

        room: Room = await self.get_room(self.room_id)
        await self.save_message(room, user, message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'user': user.username,
            }
        )

    async def chat_message(self, event):
        message: Message = event['message']
        user: User = event['user']

        await self.send(text_data=json.dumps({
            'message': message,
            'user': user,
        }))

    @sync_to_async
    def get_room(self, room_id):
        return Room.objects.get(id=room_id)

    @sync_to_async
    def save_message(self, room, user, message):
        Message.objects.create(room=room, user=user, content=message)
