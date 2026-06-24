from django.contrib import admin

from django.contrib import admin
from .models import ChatRoom, Message, MessageAttachment

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'room_type', 'created_by', 'created_at', 'is_active']
    filter_horizontal = ['participants']
    list_filter = ['room_type', 'is_active', 'created_at']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'room', 'sender', 'content_preview', 'sent_at', 'is_read']
    list_filter = ['is_read', 'sent_at']
    search_fields = ['content']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Message'

@admin.register(MessageAttachment)
class MessageAttachmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'message', 'filename', 'uploaded_at']