from django.shortcuts import render, redirect
from .models import Room
from django.contrib.auth.decorators import login_required

@login_required
def create_room(request):
    if request.method == 'POST':
        room_name = request.POST['room_name']
        room = Room.objects.create(name=room_name, host=request.user)
        return redirect('room', room_id=room.id)
    return render(request, 'create_room.html')

@login_required
def room(request, room_id):
    room = Room.objects.get(id=room_id)
    return render(request, 'chat.html', {'room': room, 'messages': room.messages.order_by('-timestamp')})
    # return render(request, 'chat.html', {'room_name': room.name, 'room_id': room.id, 'messages': messages})

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Успешная аутентификация, создаем токен
            token = create_token(user.id)
            messages.success(request, 'Вы успешно вошли в систему!')
            # Возвращаем токен клиенту в качестве JSON-ответа
            return JsonResponse(token)
        else:
            messages.error(request, 'Неверное имя пользователя или пароль.')

    return render(request, 'chat/login.html')