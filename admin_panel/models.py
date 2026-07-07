from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Profile(models.Model):
    """User profile model for additional user information."""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    bio = models.TextField(blank=True, default="")
    display_name = models.CharField(max_length=150, blank=True, default="")
    avatar_url = models.URLField(blank=True, default="")
    
    # Moderation fields
    is_moderated = models.BooleanField(default=False)
    moderated_at = models.DateTimeField(null=True, blank=True)
    moderated_reason = models.CharField(max_length=255, blank=True, default="")
    
    # Add timestamps for tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile({self.user.username})"

    def clear_content(self, reason=""):
        """Wipe user-supplied content, keep an audit trail."""
        self.bio = ""
        self.display_name = ""
        self.avatar_url = ""
        self.is_moderated = True
        self.moderated_at = timezone.now()
        self.moderated_reason = reason[:255]  # Truncate to field length
        self.save()
        
    def get_display_name(self):
        """Return the best available display name."""
        if self.display_name:
            return self.display_name
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        if self.user.first_name:
            return self.user.first_name
        return self.user.username


class AdminActionLog(models.Model):
    """Audit trail for admin actions: deactivations, role changes, moderation."""
    
    class ActionType(models.TextChoices):
        DEACTIVATE_USER = "deactivate_user", "Deactivate user"
        REACTIVATE_USER = "reactivate_user", "Reactivate user"
        ASSIGN_ROLE = "assign_role", "Assign role"
        REMOVE_ROLE = "remove_role", "Remove role"
        MODERATE_PROFILE = "moderate_profile", "Moderate profile"
        CREATE_ROLE = "create_role", "Create role"  # Added for role creation
        DELETE_ROLE = "delete_role", "Delete role"  # Added for role deletion
        USER_LOGIN = "user_login", "User login"     # Optional: track logins
        USER_LOGOUT = "user_logout", "User logout"   # Optional: track logouts

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name="admin_actions_performed",
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name="admin_actions_received",
    )
    action = models.CharField(max_length=32, choices=ActionType.choices)
    reason = models.CharField(max_length=255, blank=True, default="")
    
    # Additional fields for better auditing
    request_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    details = models.JSONField(default=dict, blank=True)  # Store extra details
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['actor', '-created_at']),
            models.Index(fields=['target_user', '-created_at']),
        ]

    def __str__(self):
        target = self.target_user.username if self.target_user else "N/A"
        actor = self.actor.username if self.actor else "System"
        return f"{self.get_action_display()} on {target} by {actor} @ {self.created_at:%Y-%m-%d %H:%M}"
    
    @classmethod
    def log_action(cls, actor, action, target_user=None, reason="", request=None, details=None):
        """Helper method to create an audit log entry."""
        log_entry = cls.objects.create(
            actor=actor,
            target_user=target_user,
            action=action,
            reason=reason[:255],
            details=details or {},
        )
        
        if request:
            log_entry.request_ip = request.META.get('REMOTE_ADDR')
            log_entry.user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
            log_entry.save()
            
        return log_entry


# Optional: Activity Log Model for user actions
class ActivityLog(models.Model):
    """Track general user activity (not just admin actions)."""
    
    class ActivityType(models.TextChoices):
        REGISTER = "register", "User registered"
        LOGIN = "login", "User logged in"
        LOGOUT = "logout", "User logged out"
        PROFILE_UPDATE = "profile_update", "Profile updated"
        TEAM_CREATE = "team_create", "Team created"
        TEAM_JOIN = "team_join", "Team joined"
        TOURNAMENT_CREATE = "tournament_create", "Tournament created"
        TOURNAMENT_JOIN = "tournament_join", "Tournament joined"
        PASSWORD_RESET = "password_reset", "Password reset"
        CONTENT_REPORT = "content_report", "Content reported"
        
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activities"
    )
    activity_type = models.CharField(max_length=32, choices=ActivityType.choices)
    description = models.CharField(max_length=255, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['activity_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_activity_type_display()} by {self.user.username} @ {self.created_at:%Y-%m-%d %H:%M}"


# Optional: Settings model for admin configuration
class AdminSettings(models.Model):
    """Store admin panel settings."""
    
    class SettingKey(models.TextChoices):
        REGISTRATION_ENABLED = "registration_enabled", "Registration Enabled"
        REGISTRATION_APPROVAL = "registration_approval", "Require Admin Approval"
        ALLOW_TEAM_CREATION = "allow_team_creation", "Allow Team Creation"
        ALLOW_TOURNAMENT_CREATION = "allow_tournament_creation", "Allow Tournament Creation"
        MAINTENANCE_MODE = "maintenance_mode", "Maintenance Mode"
        MAX_TEAM_SIZE = "max_team_size", "Maximum Team Size"
        DEFAULT_USER_ROLE = "default_user_role", "Default User Role"
    
    key = models.CharField(max_length=50, choices=SettingKey.choices, unique=True)
    value = models.CharField(max_length=500, blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_settings"
    )
    
    class Meta:
        verbose_name = "Admin Setting"
        verbose_name_plural = "Admin Settings"
        ordering = ['key']
    
    def __str__(self):
        return f"{self.get_key_display()}: {self.value}"
    
    @classmethod
    def get_setting(cls, key, default=None):
        """Get a setting value by key."""
        try:
            setting = cls.objects.get(key=key)
            return setting.value
        except cls.DoesNotExist:
            return default
    
    @classmethod
    def get_bool_setting(cls, key, default=False):
        """Get a boolean setting value."""
        value = cls.get_setting(key, default)
        if isinstance(value, bool):
            return value
        return str(value).lower() in ('true', '1', 'yes', 'on')


# Optional: Report model for user-reported content
class ReportedContent(models.Model):
    """Model for tracking user reports of inappropriate content."""
    
    class ReportStatus(models.TextChoices):
        PENDING = "pending", "Pending Review"
        REVIEWING = "reviewing", "Under Review"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"
    
    class ReportType(models.TextChoices):
        USER = "user", "User"
        TEAM = "team", "Team"
        TOURNAMENT = "tournament", "Tournament"
        PROFILE = "profile", "Profile"
        COMMENT = "comment", "Comment"
        OTHER = "other", "Other"
    
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_made"
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_received",
        null=True,
        blank=True
    )
    report_type = models.CharField(max_length=20, choices=ReportType.choices)
    content_id = models.PositiveIntegerField(null=True, blank=True)  # ID of the reported object
    content_type = models.CharField(max_length=50, blank=True, default="")  # Model name
    reason = models.TextField()
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=ReportStatus.choices, default=ReportStatus.PENDING)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_resolved"
    )
    resolution_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['reported_user', '-created_at']),
        ]
    
    def __str__(self):
        target = self.reported_user.username if self.reported_user else "Anonymous"
        return f"Report #{self.id}: {self.get_report_type_display()} against {target}"
    
    def resolve(self, resolved_by, status, notes=""):
        """Mark a report as resolved."""
        self.status = status
        self.resolved_at = timezone.now()
        self.resolved_by = resolved_by
        self.resolution_notes = notes[:500]
        self.save()