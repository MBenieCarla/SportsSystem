from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.admin import RelatedFieldListFilter
from django.contrib.auth import get_user_model

from .models import (
    AdminActionLog, 
    Profile, 
    ActivityLog, 
    AdminSettings, 
    ReportedContent
)

User = get_user_model()


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user", 
        "display_name", 
        "is_moderated", 
        "moderated_at",
        "created_at",
        "avatar_preview"
    )
    list_filter = ("is_moderated", "created_at", "moderated_at")
    search_fields = ("user__username", "user__email", "display_name", "bio")
    readonly_fields = ("created_at", "updated_at", "avatar_preview")
    
    fieldsets = (
        ("User Information", {
            "fields": ("user", "display_name")
        }),
        ("Profile Content", {
            "fields": ("bio", "avatar_url", "avatar_preview")
        }),
        ("Moderation", {
            "fields": ("is_moderated", "moderated_at", "moderated_reason"),
            "classes": ("collapse",)
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def avatar_preview(self, obj):
        """Show a thumbnail preview of the avatar URL."""
        if obj.avatar_url:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 50%; object-fit: cover;" />',
                obj.avatar_url
            )
        return "No avatar"
    avatar_preview.short_description = "Avatar Preview"
    
    def get_readonly_fields(self, request, obj=None):
        """Make moderation fields read-only if profile is already moderated."""
        if obj and obj.is_moderated:
            return self.readonly_fields + ("is_moderated", "moderated_at", "moderated_reason")
        return self.readonly_fields


@admin.register(AdminActionLog)
class AdminActionLogAdmin(admin.ModelAdmin):
    list_display = (
        "action", 
        "actor", 
        "target_user", 
        "created_at",
        "request_ip_preview",
        "action_with_icon"
    )
    list_filter = ("action", "created_at")
    readonly_fields = (
        "actor", 
        "target_user", 
        "action", 
        "reason", 
        "created_at",
        "request_ip",
        "user_agent",
        "details"
    )
    search_fields = ("actor__username", "target_user__username", "reason")
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Action Details", {
            "fields": ("action", "actor", "target_user", "reason")
        }),
        ("Technical Details", {
            "fields": ("request_ip", "user_agent", "details"),
            "classes": ("collapse",)
        }),
        ("Timestamp", {
            "fields": ("created_at",),
        }),
    )
    
    def action_with_icon(self, obj):
        """Display action with an icon."""
        icons = {
            "deactivate_user": "🔴",
            "reactivate_user": "🟢",
            "assign_role": "🔑",
            "remove_role": "🔓",
            "moderate_profile": "🛡️",
            "create_role": "➕",
            "delete_role": "❌",
            "user_login": "🔐",
            "user_logout": "🚪",
        }
        icon = icons.get(obj.action, "📝")
        return format_html(f"{icon} {obj.get_action_display()}")
    action_with_icon.short_description = "Action"
    
    def request_ip_preview(self, obj):
        """Truncate IP for display."""
        if obj.request_ip:
            return obj.request_ip
        return "-"
    request_ip_preview.short_description = "IP Address"
    
    def has_add_permission(self, request):
        """Prevent manual creation of audit log entries."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent modification of audit log entries."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion but restrict to superusers."""
        return request.user.is_superuser


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "activity_type_with_icon",
        "description",
        "created_at",
        "ip_address_preview"
    )
    list_filter = ("activity_type", "created_at")
    search_fields = ("user__username", "user__email", "description")
    readonly_fields = (
        "user", 
        "activity_type", 
        "description", 
        "created_at",
        "ip_address",
        "user_agent",
        "metadata"
    )
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Activity Details", {
            "fields": ("user", "activity_type", "description")
        }),
        ("Technical Details", {
            "fields": ("ip_address", "user_agent", "metadata"),
            "classes": ("collapse",)
        }),
        ("Timestamp", {
            "fields": ("created_at",),
        }),
    )
    
    def activity_type_with_icon(self, obj):
        """Display activity type with an icon."""
        icons = {
            "register": "📝",
            "login": "🔐",
            "logout": "🚪",
            "profile_update": "✏️",
            "team_create": "🏆",
            "team_join": "🤝",
            "tournament_create": "🎯",
            "tournament_join": "🏅",
            "password_reset": "🔑",
            "content_report": "🚨",
        }
        icon = icons.get(obj.activity_type, "📌")
        return format_html(f"{icon} {obj.get_activity_type_display()}")
    activity_type_with_icon.short_description = "Activity"
    
    def ip_address_preview(self, obj):
        """Truncate IP for display."""
        if obj.ip_address:
            return obj.ip_address
        return "-"
    ip_address_preview.short_description = "IP Address"
    
    def has_add_permission(self, request):
        """Prevent manual creation of activity log entries."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent modification of activity log entries."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion but restrict to superusers."""
        return request.user.is_superuser


@admin.register(AdminSettings)
class AdminSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "key_with_icon",
        "value_preview",
        "updated_at",
        "updated_by",
        "is_boolean"
    )
    list_filter = ("key", "updated_at")
    search_fields = ("key", "value", "description")
    readonly_fields = ("updated_at",)
    
    fieldsets = (
        ("Setting Details", {
            "fields": ("key", "value", "description")
        }),
        ("Audit", {
            "fields": ("updated_by", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def key_with_icon(self, obj):
        """Display key with an icon."""
        icons = {
            "registration_enabled": "🔓",
            "registration_approval": "✅",
            "allow_team_creation": "🏗️",
            "allow_tournament_creation": "🏟️",
            "maintenance_mode": "🔧",
            "max_team_size": "👥",
            "default_user_role": "👤",
        }
        icon = icons.get(obj.key, "⚙️")
        return format_html(f"{icon} {obj.get_key_display()}")
    key_with_icon.short_description = "Setting"
    
    def value_preview(self, obj):
        """Truncate value for display."""
        if len(obj.value) > 50:
            return format_html(f"{obj.value[:50]}...")
        return obj.value
    value_preview.short_description = "Value"
    
    def is_boolean(self, obj):
        """Show if the setting is boolean."""
        val = obj.value.lower()
        is_bool = val in ('true', 'false', '1', '0', 'yes', 'no', 'on', 'off')
        return format_html(
            '✅' if is_bool else '❌'
        )
    is_boolean.short_description = "Is Boolean"
    
    def save_model(self, request, obj, form, change):
        """Set updated_by when saving."""
        if not obj.pk:
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        if change:
            obj.updated_by = request.user
            obj.save()


@admin.register(ReportedContent)
class ReportedContentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "report_type_with_icon",
        "reporter",
        "reported_user",
        "status_colored",
        "created_at",
        "quick_actions"
    )
    list_filter = (
        "report_type",
        "status",
        "created_at",
        ("reporter", RelatedFieldListFilter),
        ("reported_user", RelatedFieldListFilter),
    )
    search_fields = (
        "reporter__username", 
        "reporter__email",
        "reported_user__username", 
        "reported_user__email",
        "reason",
        "description",
        "resolution_notes"
    )
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    actions = ["mark_resolved", "mark_dismissed"]
    
    fieldsets = (
        ("Report Details", {
            "fields": ("report_type", "reporter", "reported_user", 
                      "content_type", "content_id", "reason", "description")
        }),
        ("Status", {
            "fields": ("status", "resolved_by", "resolved_at", "resolution_notes")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def report_type_with_icon(self, obj):
        """Display report type with an icon."""
        icons = {
            "user": "👤",
            "team": "🏆",
            "tournament": "🎯",
            "profile": "📋",
            "comment": "💬",
            "other": "📌",
        }
        icon = icons.get(obj.report_type, "📌")
        return format_html(f"{icon} {obj.get_report_type_display()}")
    report_type_with_icon.short_description = "Type"
    
    def status_colored(self, obj):
        """Display status with color."""
        colors = {
            "pending": "#ff9800",
            "reviewing": "#2196f3",
            "resolved": "#4caf50",
            "dismissed": "#9e9e9e",
        }
        color = colors.get(obj.status, "#000000")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = "Status"
    
    def quick_actions(self, obj):
        """Quick action buttons for reports."""
        if obj.status in ["pending", "reviewing"]:
            return format_html(
                '<a href="{}" class="button" style="margin-right: 5px;">✅ Resolve</a> '
                '<a href="{}" class="button">❌ Dismiss</a>',
                f"/admin/admin_panel/reportedcontent/{obj.id}/resolve/",
                f"/admin/admin_panel/reportedcontent/{obj.id}/dismiss/"
            )
        return "-"
    quick_actions.short_description = "Actions"
    
    def mark_resolved(self, request, queryset):
        """Admin action to mark reports as resolved."""
        updated = queryset.update(status="resolved", resolved_at=timezone.now(), resolved_by=request.user)
        self.message_user(request, f"{updated} report(s) marked as resolved.")
    mark_resolved.short_description = "Mark selected reports as resolved"
    
    def mark_dismissed(self, request, queryset):
        """Admin action to mark reports as dismissed."""
        updated = queryset.update(status="dismissed", resolved_at=timezone.now(), resolved_by=request.user)
        self.message_user(request, f"{updated} report(s) marked as dismissed.")
    mark_dismissed.short_description = "Mark selected reports as dismissed"


# Register User model if not already registered
if not admin.site.is_registered(User):
    @admin.register(User)
    class UserAdmin(admin.ModelAdmin):
        list_display = (
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "role_display"
        )
        list_filter = ("is_active", "is_staff", "is_superuser", "date_joined")
        search_fields = ("username", "email", "first_name", "last_name")
        readonly_fields = ("date_joined", "last_login")
        
        fieldsets = (
            ("Personal Information", {
                "fields": ("username", "email", "first_name", "last_name")
            }),
            ("Permissions", {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")
            }),
            ("Important Dates", {
                "fields": ("date_joined", "last_login"),
                "classes": ("collapse",)
            }),
        )
        
        def role_display(self, obj):
            """Display user's roles."""
            if obj.is_superuser:
                return "Admin"
            if obj.groups.exists():
                return ", ".join(obj.groups.values_list("name", flat=True))
            return "User"
        role_display.short_description = "Roles"
        
        def save_model(self, request, obj, form, change):
            """Handle password changes."""
            if not obj.pk:
                obj.set_password(obj.password)
            super().save_model(request, obj, form, change)


# Custom admin site configuration
admin.site.site_header = "Community Sports Admin Panel"
admin.site.site_title = "Community Sports Admin"
admin.site.index_title = "Welcome to the Community Sports Admin Dashboard"