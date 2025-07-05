from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

# Create your models here.


class UserManager(BaseUserManager):
    def create_user(self,username, email, password=None):
        if not email:
            raise ValueError('Users must have an email address')
        if not username:
            raise ValueError('Users must have a full name')
        
        user = self.model(
            email=self.normalize_email(email),
            username=username,
            is_superuser=False,
            is_staff=False
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None):
        user = self.create_user(username, email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractUser):
    email = models.EmailField(unique=True, blank=False, null=False)
    username = models.CharField(unique=True, blank=False, null=False)
    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        if self.username:
            return self.username
        return self.email

class Room(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    creator = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_rooms"
    )
    is_private = models.BooleanField(default=False)
    is_group = models.BooleanField(default=False)
    current_users = models.ManyToManyField(
        User, related_name="current_rooms", blank=True
    )

    def __str__(self):
        return f"Room({self.name})"
        

class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages")
    text = models.TextField(max_length=500)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message({self.user} {self.room})"