from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    USER_TYPES = (
        ('player', 'Player'),
        ('trainer', 'Trainer'),
        ('organizer', 'Tournament Organizer'),
        ('admin', 'Administrator'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='player')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    
    # Player-specific fields
    preferred_sport = models.CharField(max_length=50, blank=True, null=True)
    skill_level = models.CharField(max_length=20, blank=True, null=True)
    
    # Trainer-specific fields
    specialization = models.CharField(max_length=50, blank=True, null=True)
    experience_years = models.IntegerField(default=0)
    certification = models.CharField(max_length=100, blank=True, null=True)
    
    # Profile image
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    def get_dashboard_url(self):
        if self.user_type == 'player':
            return 'accounts:player_dashboard'
        elif self.user_type == 'trainer':
            return 'accounts:trainer_dashboard'
        elif self.user_type == 'organizer':
            return 'accounts:organizer_dashboard'
        elif self.user_type == 'admin' or self.is_superuser:
            return 'accounts:admin_dashboard'
        return 'accounts:dashboard'
    
    class Meta:
        db_table = 'users'

