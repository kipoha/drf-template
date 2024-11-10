import json
from channels.db import database_sync_to_async
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework.observer import model_observer
from djangochannelsrestframework.observer.generics import ObserverModelInstanceMixin, action
from apps.users.models import User
from .models import Room, Message
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

    async def notify_users(self):
        room: Room = self.room_subscribe
        for group in self.groups:
            await self.channel_layer.group_send(
                group,
                {
                    'type': 'update_users',
                    'action': 'update_users',
                    'user_id': str(self.scope['user'].id),
                    'user': self.scope['user'].username,
                    'usuarios': await self.current_users(room)
                }
            )

    async def update_users(self, event: dict):
        await self.send(
            text_data=json.dumps({
                'action': 'update_users',
                'user_id': event["user_id"],
                'user': event["user"],
                'usuarios': event["usuarios"]
            })
        )

    async def chat_message(self, event: dict):
        if event['action'] == 'edit_message':
            await self.send(text_data=json.dumps({
                'action': 'edit_message',
                'message_id': event['message_id'],
                'message': event['message'],
                'user': event['user'],
                'user_id': event['user_id']
            }))
        else:
            await self.send(text_data=json.dumps({
                'action': 'create_message',
                'message': event['message'],
                'user': event['user'],
                'user_id': event['user_id']
            }))

    async def user_activity(self, event: dict):
        await self.send(text_data=json.dumps({
            'action': event['action'],
            'user_id': event['user_id'],
            'user': event['user']
        }))




    # actions
    @action()
    async def join_room(self, pk, **kwargs):
        room = await self.get_room(pk)
        self.room_subscribe = room
        await self.add_user_to_room(room)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_activity',
                'action': 'user_joined',
                'user_id': str(self.scope['user'].id),
                'user': self.scope['user'].username,
            }
        )
        await self.notify_users()

    @action()
    async def leave_room(self, pk, **kwargs):
        room = await self.get_room(pk)
        await self.remove_user_from_room(room)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_activity',
                'action': 'user_left',
                'user_id': str(self.scope['user'].id),
                'user': self.scope['user'].username,
            }
        )
        await self.notify_users()

    @action()
    async def create_message(self, message, **kwargs):
        room: Room = self.room_subscribe
        new_message: Message = await database_sync_to_async(Message.objects.create)(
            room=room,
            user=self.scope['user'],
            content=message
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'action': 'create_message',
                'message': new_message.content,
                'user': self.scope['user'].username,
                'user_id': str(self.scope['user'].id),
            }
        )
    
    @action()
    async def edit_message(self, message_id, new_content, **kwargs):
        try:
            message = await database_sync_to_async(Message.objects.get)(pk=message_id)
            message.content = new_content
            await database_sync_to_async(message.save)()

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'action': 'edit_message',
                    'message': message.content,
                    'user': self.scope['user'].username,
                    'user_id': str(self.scope['user'].id),
                    'message_id': message_id
                }
            )
        except Message.DoesNotExist:
            await self.send_json({'error': 'Message not found'})


    @model_observer(Message)
    async def message_activity(self, message, onserver=None, **kwargs):
        data = MessageSerializer(message).data
        await self.send_json({
            'action': 'update_message',
            'message': data
        })


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





    # database sync to async
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

