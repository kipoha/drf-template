# from channels.generic.websocket import AsyncWebsocketConsumer
# from asgiref.sync import sync_to_async

# class ChatConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.room_id = self.scope['url_route']['kwargs']['room_id']
#         self.room_group_name = f'chat_{self.room_id}'

#         await self.channel_layer.group_add(
#             self.room_group_name,
#             self.channel_name
#         )

#         await self.accept()

#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name
#         )

#     async def receive(self, text_data):
#         data: dict = json.loads(text_data)
#         message: Message = data['message']
#         user: User = self.scope['user']

#         room: Room = await self.get_room(self.room_id)
#         await self.save_message(room, user, message)

#         await self.channel_layer.group_send(
#             self.room_group_name,
#             {
#                 'type': 'chat_message',
#                 'message': message,
#                 'user': user.username,
#             }
#         )

#     async def chat_message(self, event):
#         message: Message = event['message']
#         user: User = event['user']

#         await self.send(text_data=json.dumps({
#             'message': message,
#             'user': user,
#         }))

#     @sync_to_async
#     def get_room(self, room_id):
#         return Room.objects.get(id=room_id)

#     @sync_to_async
#     def save_message(self, room, user, message):
#         Message.objects.create(room=room, user=user, content=message)

import json
from channels.db import database_sync_to_async
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework.observer import model_observer
from djangochannelsrestframework.observer.generics import ObserverModelInstanceMixin, action
from .models import Room, Message
from apps.users.models import User
from .serializers import RoomSerializer, MessageSerializer, UserSerializer

class ChatAPIConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    lookup_field = 'pk'

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'room__{self.room_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'room_subscribe'):
            await self.remove_user_from_room(self.room_subscribe)
            await self.notify_users()

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        await super().disconnect(code)

    @action()
    async def join_room(self, pk, **kwargs):
        room = await self.get_room(pk)
        self.room_subscribe = room
        await self.add_user_to_room(room)
        await self.notify_users()

    @action()
    async def leave_room(self, pk, **kwargs):
        room = await self.get_room(pk)
        await self.remove_user_from_room(room)
        await self.notify_users()

    @action()
    async def create_message(self, message, **kwargs):
        room: Room = self.room_subscribe
        new_message = await database_sync_to_async(Message.objects.create)(
            room=room,
            user=self.scope['user'],
            content=message
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': new_message.content,
                'user': self.scope['user'].username,
                'user_id': str(self.scope['user'].id),
            }
        )

    @model_observer(Message)
    async def message_activity(self, message, onserver=None, **kwargs):
        await self.send_json(message)

    @message_activity.groups_for_signal
    def message_activity(self, instance: Message, **kwargs):
        yield f'room__{instance.room_id}'

    @message_activity.groups_for_consumer
    def message_activity(self, room=None, **kwargs):
        if room:
            yield f'room__{room}'

    @message_activity.serializer
    def message_activity(self, instance: Message, action, **kwargs):
        return dict(data=MessageSerializer(instance).data, action=action.value, pk=instance.pk, **kwargs)

    async def notify_users(self):
        room: Room = self.room_subscribe
        for group in self.groups:
            await self.channel_layer.group_send(
                group,
                {
                    'type': 'update_users',
                    'usuarios': await self.current_users(room)
                }
            )

    async def update_users(self, event: dict):
        await self.send(text_data=json.dumps({'usuarios': event["usuarios"]}))

    @database_sync_to_async
    def get_room(self, pk: int) -> Room:
        return Room.objects.get(pk=pk)

    @database_sync_to_async
    def current_users(self, room: Room):
        return [UserSerializer(user).data for user in room.current_users.all()]

    @database_sync_to_async
    def remove_user_from_room(self, room):
        user: User = self.scope["user"]
        room.current_users.remove(user)

    @database_sync_to_async
    def add_user_to_room(self, room):
        user: User = self.scope["user"]
        if not user.rooms.filter(pk=room.pk).exists():
            user.rooms.add(room)

    async def chat_message(self, event):
        message = event['message']
        user = event['user']
        user_id = event['user_id']

        await self.send(text_data=json.dumps({
            'message': message,
            'user': user,
            'user_id': user_id,
        }))
