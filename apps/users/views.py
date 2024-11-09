from django.http import JsonResponse
from django.shortcuts import render, redirect
from .forms import RegisterForm, LoginForm
from django.contrib.auth import authenticate, login
from django.contrib import messages
from rest_framework_simplejwt.tokens import RefreshToken
from django.http.request import HttpRequest
from .models import User

def login_view(request: HttpRequest):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Некорректные данные формы.')
            return JsonResponse({'error': 'Некорректные данные формы.'}, status=400)
        
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user = authenticate(request, username=username, password=password)
        if not user:
            messages.error(request, 'Неверное имя пользователя или пароль.')
            return JsonResponse({'error': 'Неверное имя пользователя или пароль.'}, status=401)

        login(request, user)

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = redirect('/api/v1/chat/select-room/')
        response.set_cookie('access_token', access_token)
        response.set_cookie('refresh_token', refresh_token)

        messages.success(request, 'Вы успешно вошли в систему!')
        return response
    else:
        form = LoginForm()
        return render(request, 'login.html', {'form': form})
    
def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Ошибка регистрации. Проверьте данные и попробуйте снова.')
            return render(request, 'register.html', {'form': form})
        user = User.objects.create_user(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
            email=form.cleaned_data['email'],
        )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = redirect('/api/v1/chat/select-room/')
        response.set_cookie('access_token', access_token)
        response.set_cookie('refresh_token', refresh_token)

        messages.success(request, 'Регистрация прошла успешно. Войдите в систему.')
        return response

    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})
