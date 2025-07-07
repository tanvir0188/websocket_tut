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
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from .models import Room, Message
from .serializers import MessageSerializer
from asgiref.sync import sync_to_async

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if self.user.is_anonymous:
            await self.close()
            return
            
        # Check if room exists and user has access
        room_exists = await self.check_room_access()
        if not room_exists:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send existing messages to the newly connected user
        await self.send_existing_messages()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'chat_message')
            
            if message_type == 'chat_message':
                message_text = text_data_json.get('message', '')
                
                if not message_text.strip():
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Message cannot be empty'
                    }))
                    return
                
                # Save message to database
                message = await self.save_message(message_text)
                
                if message:
                    # Serialize the message
                    message_data = await self.serialize_message(message)
                    
                    # Send message to room group
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_message',
                            'message_data': message_data
                        }
                    )
            
            elif message_type == 'get_messages':
                # Send existing messages
                await self.send_existing_messages()
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'An error occurred: {str(e)}'
            }))
    
    async def chat_message(self, event):
        message_data = event['message_data']
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message_data
        }))
    
    @database_sync_to_async
    def check_room_access(self):
        """Check if room exists and user has access to it"""
        try:
            room = Room.objects.get(pk=self.room_id)
            
            # Check if user is in the room or is the creator
            return (self.user in room.current_users.all() or 
                   room.creator == self.user)
        except Room.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, message_text):
        """Save message to database"""
        try:
            room = Room.objects.get(pk=self.room_id)
            
            # Check if user has access to send messages in this room
            if self.user not in room.current_users.all() and room.creator != self.user:
                return None
                
            message = Message.objects.create(
                room=room,
                user=self.user,
                text=message_text
            )
            return message
        except Room.DoesNotExist:
            return None
    
    @database_sync_to_async
    def serialize_message(self, message):
        """Serialize message using MessageSerializer"""
        serializer = MessageSerializer(message)
        return serializer.data
    
    @database_sync_to_async
    def get_room_messages(self):
        """Get all messages for the room"""
        try:
            room = Room.objects.get(pk=self.room_id)
            messages = Message.objects.filter(room=room).order_by('created_at')
            serializer = MessageSerializer(messages, many=True)
            return serializer.data
        except Room.DoesNotExist:
            return []
    
    async def send_existing_messages(self):
        """Send existing messages to the user"""
        messages = await self.get_room_messages()
        await self.send(text_data=json.dumps({
            'type': 'message_history',
            'messages': messages
        }))


class NotificationConsumer(AsyncWebsocketConsumer):
    """Consumer for user-specific notifications"""
    
    
    async def connect(self):
        self.user = self.scope['user']
        
        if self.user.is_anonymous:
            await self.close()
            return
            
        self.user_group_name = f'user_{self.user.id}'
        
        # Join user group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave user group
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        # Handle incoming messages if needed
        pass
    
    async def user_notification(self, event):
        """Send notification to user"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data']
        }))