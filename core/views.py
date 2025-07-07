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


@extend_schema(
        request=RoomSerializer, 
        responses=RoomSerializer,
        examples=[
            OpenApiExample(
                name="Create a new room",
                value={                    
                    "name": "room",                                                                                
                    "is_private": True,
                    "is_group": False,
                }
            )
        ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_room(request):
    # Use DRF's built-in request.data
    data = request.data.copy()
    data['creator'] = request.user  # pass user id to serializer

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

    # Count current users
    current_user_count = room.current_users.count()

    # Filter users to add (to avoid invalid IDs)
    users_to_add = User.objects.filter(pk__in=user_ids)

    # Calculate total if we add these new users (exclude duplicates)
    new_unique_users_count = users_to_add.exclude(pk__in=room.current_users.values_list('pk', flat=True)).count()
    total_after_add = current_user_count + new_unique_users_count

    if room.is_private and not room.is_group and total_after_add > 2:
        return Response({
            'message': 'Private one-to-one room cannot have more than 2 users.',
            'status': 'error'
        }, status=400)

    # Add users only after validation passed
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
