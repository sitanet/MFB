import uuid
from django.db import models
from django.conf import settings
from company.models import Branch


class ChatRoom(models.Model):
    """
    Chat room for conversations between staff members.
    Can be direct (1-on-1) or group chat.
    """
    ROOM_TYPES = (
        ('direct', 'Direct Message'),
        ('branch', 'Branch Group'),
        ('company', 'Company Group'),
    )
    
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='direct')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, 
                               related_name='chat_rooms')
    company_id = models.CharField(max_length=20, blank=True, null=True)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        if self.name:
            return self.name
        return f"Chat Room {self.uuid}"
    
    def get_other_participant(self, user):
        """For direct chats, get the other participant"""
        if self.room_type == 'direct':
            return self.participants.exclude(id=user.id).first()
        return None
    
    def get_last_message(self):
        return self.messages.order_by('-created_at').first()


class Message(models.Model):
    """Individual chat message"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                               related_name='sent_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender.first_name}: {self.content[:30]}"


class MessageReadStatus(models.Model):
    """Track read status for each user in group chats"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_statuses')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('message', 'user')
