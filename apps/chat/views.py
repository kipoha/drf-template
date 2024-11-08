from django.shortcuts import render, redirect, get_object_or_404
from .models import Room
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpRequest

@login_required(login_url='/auth/login/')
def create_room(request: HttpRequest):
    if request.method == 'POST':
        room_name = request.POST.get('room_name')
        if not room_name:
            messages.error(request, 'Имя комнаты не может быть пустым.')
            return redirect('create_room')
        room = Room.objects.create(name=room_name, host=request.user)
        messages.success(request, f'Комната "{room_name}" успешно создана.')
        return redirect('room', room_id=room.id)
    return render(request, 'create_room.html')

@login_required(login_url='/auth/login/')
def room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    return render(request, 'chat.html', {'room': room, 'messages': room.messages.order_by('timestamp')})

@login_required(login_url='/auth/login/')
def select_room(request):
    rooms = Room.objects.all().order_by('-created_at')
    if not rooms:
        messages.error(request, 'Нет доступных комнат.')
        return redirect('create_room')
    return render(request, 'select_room.html', {'rooms': rooms})
