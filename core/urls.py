from django.urls import path
from . import views
urlpatterns = [
    path('register', views.register_user, name='register'),
    path('user-list', views.get_users, name='user-list'),
    path('create-room', views.create_room, name='create-room'),
    path('room-list', views.room_list, name='room-list'),
    path('add-user-to-room/<int:pk>', views.add_user_to_room, name='add-user-to-room'),
    path('remove-users-from-room/<int:pk>', views.remove_user_from_room, name='remove-users-from-room'),
    path('message-by-room/<int:pk>', views.messages_by_room, name='messages-by-room'),
    path('send-message/<int:pk>', views.create_message, name='create-message'),
]
