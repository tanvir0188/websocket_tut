from .models import User, Room, Message
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id','email', 'username']

        
class AddUserSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )

    def validate_user_ids(self, value):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        not_found = []
        for user_id in value:
            if not User.objects.filter(pk=user_id).exists():
                not_found.append(user_id)
        if not_found:
            raise serializers.ValidationError(f"User(s) with ID(s) {not_found} do not exist.")
        return value



class MessageSerializer(serializers.ModelSerializer):
    created_at_formatted = serializers.SerializerMethodField()
    user = UserSerializer()

    class Meta:
        model = Message
        fields = '__all__'

    def get_created_at_formatted(self, obj:Message):
        return obj.created_at.strftime("%d-%m-%Y %H:%M:%S")


class RoomSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    messages = MessageSerializer(many=True, read_only=True)
    current_users = UserSerializer(many =True, read_only=True)
    creator = UserSerializer(many=False)
    class Meta:
        model = Room
        fields = [
            "pk",
            "name",
            "messages",
            "current_users",
            "last_message",
            "creator",
            "is_private",
            "is_group",
        ]
        depth = 1
        read_only_fields = ["messages", "last_message", "creator"]

    def get_last_message(self, obj:Room):
        return MessageSerializer(obj.messages.order_by('created_at').last()).data
    def create(self, validated_data):
        return Room.objects.create(**validated_data)
