from django.urls import path
from . import views

urlpatterns = [
    path('create-room/', views.create_room, name='create_room'),
    path('chat/<uuid:room_id>/', views.room, name='room'),
]
