# chat/routing.py
from django.urls import re_path, path

from . import consumers

websocket_urlpatterns = [
     path('ws/chat/<int:room_id>/', consumers.ChatConsumer.as_asgi()),
    
    # User notifications WebSocket
    path('ws/notifications/', consumers.NotificationConsumer.as_asgi()),    
]
