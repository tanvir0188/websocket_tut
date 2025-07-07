from django.shortcuts import render, get_object_or_404, reverse
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .serializers import UserSerializer, RoomSerializer, AddUserSerializer, MessageSerializer
from .models import Room, User, Message
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiTypes, OpenApiParameter
from rest_framework.parsers import JSONParser


@extend_schema(
    request=UserSerializer,
    responses=UserSerializer,
    examples=[
        OpenApiExample(
            name="Register as a new user",
            value={
                "email": "someone@example.com",                
                "username": 'someone',
                "password": "**********"
            }
        )
    ]
)
@api_view(['POST'])
def register_user(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = User.objects.create_user(**serializer.validated_data)
        return Response({'message': 'User created successfully',
                         'data':serializer.data
                         })
    return Response(serializer.errors, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_users(request):
    users = User.objects.all()
    serialize = UserSerializer(users, many=True)
    return Response({
        'status':'success',
        'users':serialize.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_room(request):
    # Use DRF's built-in request.data
    data = request.data.copy()
    data['creator'] = request.user.id  # pass user id to serializer

    serializer = RoomSerializer(data=data)
    if serializer.is_valid():
        room = serializer.save(creator=request.user)
        room.current_users.add(request.user)

        return Response({
            'message': 'Room created',
            'room': RoomSerializer(room).data,
            'status': 'success'
        }, status=201)
    else:
        return Response({
            'message': 'Room creation failed',
            'errors': serializer.errors,
            'status': 'error'
        }, status=400)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def room_list(request):
    try:
        rooms = Room.objects.filter(creator = request.user)                
    except Room.DoesNotExist:
        return JsonResponse({
            'status':'error'
        }, 500)
    serializer = RoomSerializer(rooms, many=True)
    return JsonResponse({
            'status':'success',
            'rooms':serializer.data
        })




@extend_schema(
    request=RoomSerializer,
    responses=RoomSerializer,
    parameters=[
        OpenApiParameter
    ],
    examples=[
        OpenApiExample(
            name="Add users to room",
            
            value={
                "user_ids": [],
            }
        )
    ]
)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def add_user_to_room(request, pk):
    serializer = AddUserSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'message': 'Validation failed',
            'errors': serializer.errors,
            'status': 'error'
        }, status=400)

    user_ids = serializer.validated_data['user_ids']

    room = get_object_or_404(Room, pk=pk)

    if room.creator != request.user:
        return Response({
            'message': 'Only the creator can add new users',
            'status': 'unauthorized'
        }, status=403)

    
    users_to_add = User.objects.filter(pk__in=user_ids)
    room.current_users.add(*users_to_add)

    return Response({
        'message': f"Added users {', '.join([u.username for u in users_to_add])} to the room",
        'status': 'success'
    }, status=200)
@extend_schema(
    request=RoomSerializer,
    responses=RoomSerializer,
    parameters=[
        OpenApiParameter
    ],
    examples=[
        OpenApiExample(
            name="Remove users from a room",
            
            value={
                "user_ids": [],
            }
        )
    ]
)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def remove_user_from_room(request, pk):
    serializer = AddUserSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'message': 'Validation failed',
            'errors': serializer.errors,
            'status': 'error'
        }, status=400)

    room = get_object_or_404(Room, pk=pk)
    if room.creator != request.user:
        return Response({
            'message': 'Only the creator can remove users',
            'status': 'unauthorized'
        }, status=403)

    user_ids = serializer.validated_data.get('user_ids', [])
    users_to_remove = room.current_users.filter(pk__in=user_ids)
    users_in_room_ids = set(room.current_users.values_list('pk', flat=True))
    not_in_room = list(set(user_ids) - users_in_room_ids)

    room.current_users.remove(*users_to_remove)

    return Response({
        'message': f"Removed users {', '.join([u.username for u in users_to_remove])} from the room",
        'not_in_room': not_in_room,
        'status': 'success'
    }, status=200)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def messages_by_room(request, pk):
    messages = Message.objects.filter(room=pk)
    serializer = MessageSerializer(messages,many = True)
    return Response({
        'status':'success',
        'messages':serializer.data
    }, status =200)

@extend_schema(
    request=MessageSerializer,
    responses=MessageSerializer,
    parameters=[
        OpenApiParameter
    ],
    examples=[
        OpenApiExample(
            name="Create message in a room",
            
            value={                
                "text":"text message",                
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_message(request, pk):
    room=get_object_or_404(Room, pk=pk)
    data = JSONParser().parse(request)
    text = data.get('text')

    message = Message.objects.create(
        room=room,
        user=request.user,
        text=text
    )
    serializer = MessageSerializer(message)
    return JsonResponse(serializer.data, safe=False)
