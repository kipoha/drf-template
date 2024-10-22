from django.shortcuts import render, redirect
from .models import Room
from django.contrib.auth.decorators import login_required

@login_required
def create_room(request):
    if request.method == 'POST':
        room_name = request.POST['room_name']
        room = Room.objects.create(name=room_name, created_by=request.user)
        return redirect('room', room_id=room.id)
    return render(request, 'create_room.html')

@login_required
def room(request, room_id):
    room = Room.objects.get(id=room_id)
    messages = room.messages.order_by('-timestamp') 
    return render(request, 'chat.html', {'room_name': room.name, 'room_id': room.id, 'messages': messages})