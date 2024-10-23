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

from .models import Room, Message
from django.contrib.auth.models import User

from .serializers import RoomSerializer, MessageSerializer, UserSerializer

from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework.observer import model_observer
from djangochannelsrestframework.observer.generics import ObserverModelInstanceMixin, action
from channels.db import database_sync_to_async


class ChatAPIConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    lookup_field = 'pk'

    async def disconnect(self, code):
        if hasattr(self, 'room_subsribe'):
            await self.room_subsribe.remove(self.room_subsribe)
            await self.notify_users()
        await super().disconnect(code)
    
    @action()
    async def join_room(self, pk, **kwargs):
        self.room_subsribe = pk
        await self.add_user_to_room(pk)
        await self.notify_users()
    
    @action()
    async def leave_room(self, pk, **kwargs):
        await self.remove_user_from_room(pk)
    
    @action()
    async def create_message(self, message, **kwargs):
        room: Room = await self.get_room(pk=self.room_subsribe)
        await database_sync_to_async(Message.objects.create)(
            room=room,
            user=self.scope['user'],
            content=message
        )
    
    @action()
    async def subscribe_to_message_in_room(self, pk, **kwargs):
        await self.message_activity.subscribe(room=pk)
    
    @model_observer(Message)
    async def message_activity(self, message, onserver=None, **kwargs): await self.send_json(message)
    
    @message_activity.groups_for_signal
    def message_activity(self, instance: Message, **kwargs):
        yield f'room__{instance.room_id}'
        yield f'pk__{instance.pk}'
    
    @message_activity.groups_for_consumer
    def message_activity(self, room=None, **kwargs):
        if room: yield f'room__{room}'
    
    @message_activity.serializer
    def message_activity(self, instance: Message, action, **kwargs):
        return dict(data=MessageSerializer(instance), action=action.value, pk=instance.pk, **kwargs)
        # return dict(data=MessageSerializer(instance), action=action.value, pk=instance.pk)
    
    async def notify_users(self):
        room: Room = self.get_room(self.room_subsribe)    
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
        user.current_rooms.remove(room)

    @database_sync_to_async
    def add_user_to_room(self, pk):
        user: User = self.scope["user"]
        if not user.current_rooms.filter(pk=self.room_subscribe).exists():
            user.current_rooms.add(Room.objects.get(pk=pk))