from django.urls import path
from . import views
urlpatterns = [
    path('register', views.register_user, name='register'),
    path('user-list', views.get_users, name='user-list'),
    path('create-room', views.create_room, name='create-room'),
    path('room-list', views.room_list, name='room-list'),
    path('add-user-to-room/<int:pk>', views.add_user_to_room, name='add-user-to-room')
]
