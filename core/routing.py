# chat/routing.py
from django.urls import re_path, path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/room/$', consumers.RoomConsumer.as_asgi()),
    path('ws/sc/', consumers.MyConsumer.as_asgi()),
    path('ws/ac/', consumers.MyAsyncConsumer.as_asgi()),

]