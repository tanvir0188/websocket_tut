# import json

# from asgiref.sync import async_to_sync
# from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer
# from channels.consumer import SyncConsumer, AsyncConsumer
# Not fully async yet
# class ChatConsumer(WebsocketConsumer):
#     def connect(self):
#         self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
#         self.room_group_name = f"chat_{self.room_name}"

#         # Join room group
#         async_to_sync(self.channel_layer.group_add)(
#             self.room_group_name, self.channel_name
#         )

#         self.accept()

#     def disconnect(self, close_code):
#         # Leave room group
#         async_to_sync(self.channel_layer.group_discard)(
#             self.room_group_name, self.channel_name
#         )

#     # Receive message from WebSocket
#     def receive(self, text_data):
#         text_data_json = json.loads(text_data)
#         message = text_data_json["message"]

#         # Send message to room group
#         async_to_sync(self.channel_layer.group_send)(
#             self.room_group_name, {"type": "chat.message", "message": message}
#         )

#     # Receive message from room group
#     def chat_message(self, event):
#         message = event["message"]

#         # Send message to WebSocket
#         self.send(text_data=json.dumps({"message": message}))
# class ChatConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
#         self.room_group_name = f"chat_{self.room_name}"

#         # Join room group
#         await self.channel_layer.group_add(self.room_group_name, self.channel_name)

#         await self.accept()

#     async def disconnect(self, close_code):
#         # Leave room group
#         await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

#     # Receive message from WebSocket
#     async def receive(self, text_data):
#         text_data_json = json.loads(text_data)
#         message = text_data_json["message"]

#         # Send message to room group
#         await self.channel_layer.group_send(
#             self.room_group_name, {"type": "chat.message", "message": message}
#         )

#     # Receive message from room group
#     async def chat_message(self, event):
#         message = event["message"]

#         # Send message to WebSocket
#         await self.send(text_data=json.dumps({"message": message}))
# #syncconsumer is a the lower sub class. which means it's more of a raw version.
# class MyConsumer(SyncConsumer):
#     def websocket_connect(self, event):#this handler is called that initially opens the connection through the handshake
#         print('websocket connect', event)
#         self.send({
#             'type':'websocket.accept'
#         })
    
#     def websocket_receive(self, event):#when data is received by the client
#         print('websocket received', event)
#     def websocket_disconnect(self, event):#either the client lost the connection or the server. or both of them lost the connection
#         print('websocket disconnect', event)

# class MyAsyncConsumer(AsyncConsumer):
#     async def websocket_connect(self, event):#this handler is called that initially opens the connection through the handshake
#         print('websocket connect')
    
#     async def websocket_receive(self, event):#when data is received by the client
#         print('websocket received')
#     async def websocket_disconnect(self, event):#either the client lost the connection or the server. or both of them lost the connection
#         print('websocket disconnect')

# chat/consumers.py
import json

from channels.db import database_sync_to_async
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework.observer import model_observer
from djangochannelsrestframework.observer.generics import ObserverModelInstanceMixin, action
from djangochannelsrestframework.mixins import CreateModelMixin

from .models import Message, Room, User
from .serializers import MessageSerializer, RoomSerializer, UserSerializer


class RoomConsumer(CreateModelMixin, ObserverModelInstanceMixin, GenericAsyncAPIConsumer):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    lookup_field = "pk"

    @action()
    async def create(self, data: dict, request_id: str, **kwargs):
        response, status = await super().create(data, **kwargs)
        room_pk = response["pk"]
        await self.join_room(request_id=request_id, pk=room_pk)
        return response, status
    
    @action()
    async def join_room(self, pk, request_id, **kwargs):
        room = await database_sync_to_async(self.get_object)(pk=pk)
        await self.subscribe_instance(request_id=request_id, pk=room.pk)
        await self.add_user_to_room(room)
    
    @action()
    async def leave_room(self, pk, **kwargs):
        room = await database_sync_to_async(self.get_object)(pk=pk)
        await self.remove_user_from_room(room)
        await self.unsubscribe_instance(pk=room.pk)
    @database_sync_to_async
    def add_user_to_room(self, room: Room):
        user: User = self.scope["user"]
        room.current_users.add(user)

    @database_sync_to_async
    def remove_user_from_room(self, room: Room):
        user: User = self.scope["user"]
        room.current_users.remove(user)
    
    @action()
    async def create_message(self, message, room, **kwargs):
        room: Room = await database_sync_to_async(self.get_object)(pk=room)
        await database_sync_to_async(Message.objects.create)(
            room=room,
            user=self.scope["user"],
            text=message
        )
    @model_observer(Message)
    async def message_activity(
        self,
        message,
        observer=None,
        subscribing_request_ids=[],
        **kwargs
    ):
        """
        This is evaluated once for each subscribed consumer.
        The result of `@message_activity.serializer` is provided here as the message.
        """
        # Since we provide the request_id when subscribing, we can just loop over them here.
        for request_id in subscribing_request_ids:
            message_body = dict(request_id=request_id)
            message_body.update(message)
            await self.send_json(message_body)

    @message_activity.groups_for_signal
    def message_activity(self, instance: Message, **kwargs):
        yield f'room__{instance.room_id}'

    @message_activity.groups_for_consumer
    def message_activity(self, room=None, **kwargs):
        if room is not None:
            yield f'room__{room}'

    @message_activity.serializer
    def message_activity(self, instance: Message, action, **kwargs):
        """
        This is evaluated before the update is sent
        out to all the subscribing consumers.
        """
        return dict(
            data=MessageSerializer(instance).data,
            action=action.value,
            pk=instance.pk
        )

    @action()
    async def join_room(self, pk, request_id, **kwargs):
        room = await database_sync_to_async(self.get_object)(pk=pk)
        await self.subscribe_instance(request_id=request_id, pk=room.pk)
        await self.message_activity.subscribe(room=pk, request_id=request_id)
        await self.add_user_to_room(room)

    @action()
    async def leave_room(self, pk, **kwargs):
        room = await database_sync_to_async(self.get_object)(pk=pk)
        await self.unsubscribe_instance(pk=room.pk)
        await self.message_activity.unsubscribe(room=room.pk)
        await self.remove_user_from_room(room)