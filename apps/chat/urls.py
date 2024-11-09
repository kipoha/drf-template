from django.urls import path
from . import views

urlpatterns = [
    path('create-room/', views.create_room, name='create_room'),
    path('chat/<int:room_id>/', views.room, name='room'),
    path('select-room/', views.select_room, name='select_room'),
]
