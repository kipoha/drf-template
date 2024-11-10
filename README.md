# drf-template
template for ur project


## Chat


код для тестирования чата
```python
main_token = 'access_jwt_token'


import aiohttp, asyncio, json, time

async def send_message(ws: aiohttp.ClientWebSocketResponse, message_data: dict):
    await ws.send_str(json.dumps(message_data))
    print(f"Отправлено сообщение: {message_data}")

async def receive_message(ws: aiohttp.ClientWebSocketResponse):
    response = await ws.receive()
    if response.type == aiohttp.WSMsgType.TEXT:
        print("Ответ от сервера:", response.data)
        return json.loads(response.data)
    elif response.type == aiohttp.WSMsgType.ERROR:
        print("Ошибка WebSocket:", response.data)
    elif response.type == aiohttp.WSMsgType.CLOSED:
        print("Соединение закрыто")
        return None
    elif response.type == 8:
        print("Соединение закрывается")
        return None
    else:
        print(f"Неизвестный тип сообщения {response.type}")
        return None

async def join_room(ws: aiohttp.ClientWebSocketResponse, room_id: str, user_id: str):
    request_id = str(int(time.time() * 1000))
    message = {
        "action": "join_room",
        "pk": room_id,
        "request_id": request_id
    }
    await send_message(ws, message)

async def create_message(ws: aiohttp.ClientWebSocketResponse, room_id: str, user_id: str, message_content: str):
    request_id = str(int(time.time() * 1000))
    message = {
        "action": "create_message",
        "message": message_content,
        "room_id": room_id,
        "user_id": user_id,
        "request_id": request_id
    }
    await send_message(ws, message)

async def edit_message(ws: aiohttp.ClientWebSocketResponse, message_id: str, new_content: str):
    request_id = str(int(time.time() * 1000))
    message = {
        "action": "edit_message",
        "message_id": message_id,
        "new_content": new_content,
        "request_id": request_id
    }
    await send_message(ws, message)

async def create_socket(url: str, token: str, chat_id: str) -> None:
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.ws_connect(url) as ws:
                    print("WebSocket подключен.")
                    
                    user_id = token.split('.')[1]

                    await join_room(ws, chat_id, user_id)

                    while True:
                        message = input("Введите сообщение: ")
                        await create_message(ws, chat_id, user_id, message)
                        
                        response = await receive_message(ws)
                        if response:
                            if response['action'] == 'create_message':
                                print(f"Новое сообщение от {response['user']}: {response['message']}")
                            elif response['action'] == 'edit_message':
                                print(f"Сообщение от {response['user']} отредактировано: {response['message']}")
            except aiohttp.ClientConnectionError as e:
                print(f"Ошибка соединения: {e}")
            except Exception as e:
                print(f"Произошла ошибка: {e}")
            
            print("Переподключение через 3 секунды...")
            await asyncio.sleep(3)

async def main():
    chat_id = '2'
    url = f'ws://localhost:8000/ws/chat/{chat_id}/?token={main_token}'
    await create_socket(url, main_token, chat_id)

if __name__ == '__main__':
    asyncio.run(main())

```
