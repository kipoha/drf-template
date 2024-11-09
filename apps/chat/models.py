from django.db import models
from apps.common.models import BaseModel
from apps.users.models import User

class Room(BaseModel):
    name = models.CharField(max_length=255)
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rooms')
    current_users = models.ManyToManyField(User, related_name='users', blank=True)

    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'host': self.host.username,
            'current_users': [user.username for user in self.current_users.all()],
        }

class Message(BaseModel):
    room = models.ForeignKey(Room, related_name='messages', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def to_dict(self):
        return {
            'id': str(self.id),
            'room_id': str(self.room.id),
            'user': self.user.username,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
        }
