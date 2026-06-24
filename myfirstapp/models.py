from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.utils import timezone
from datetime import date as datetime_date
from django.core.validators import FileExtensionValidator, MinValueValidator


class Team(models.Model):
    team_name = models.CharField(max_length=100, unique=True)
    trainer = models.ForeignKey(
        'Trainer', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='teams'
    )
    location = models.CharField(max_length=200)
    max_members = models.IntegerField(default=20)
    current_members = models.IntegerField(default=0)
    matches_played = models.IntegerField(default=0)
    matches_won = models.IntegerField(default=0)
    matches_lost = models.IntegerField(default=0)
    matches_drawn = models.IntegerField(default=0)
    
    # Approval system
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_teams'
    )
    approved_date = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['team_name']
    
    def __str__(self):
        return self.team_name
    
    @property
    def available_spots(self):
        return self.max_members - self.current_members
    
    @property
    def is_available(self):
        return self.available_spots > 0
    
    @property
    def is_full(self):
        return self.current_members >= self.max_members
    
    @property
    def win_rate(self):
        if self.matches_played == 0:
            return 0
        return (self.matches_won / self.matches_played) * 100
    
    @property
    def status(self):
        if self.is_approved:
            return "Approved"
        else:
            return "Pending Approval"
    
    def save(self, *args, **kwargs):
        # Auto-update current_members count
        self.current_members = self.players.count()
        
        # If approving team, set approved date
        if self.is_approved and not self.approved_date:
            self.approved_date = timezone.now()
        
        super().save(*args, **kwargs)


class Match(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='matches')
    opponent = models.CharField(max_length=100)
    date = models.DateField()  # Changed from auto_now_add to allow manual entry
    time = models.TimeField(null=True, blank=True)  # Added time field
    team_score = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    opponent_score = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    location = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_matches')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date', '-time']
        verbose_name_plural = "Matches"
    
    def __str__(self):
        return f"{self.team.team_name} vs {self.opponent} on {self.date}"
    
    @property
    def result(self):
        if self.status != 'completed':
            return "Not completed"
        if self.team_score > self.opponent_score:
            return "Win"
        elif self.team_score < self.opponent_score:
            return "Loss"
        else:
            return "Draw"
    
    @property
    def is_upcoming(self):
        return datetime_date.today() < self.date
    
    @property
    def is_today(self):
        return datetime_date.today() == self.date
    
    @property
    def is_past(self):
        return datetime_date.today() > self.date
    
    @property
    def result_display(self):
        if self.status != 'completed':
            return "Match not completed"
        return f"{self.team.team_name} {self.team_score} - {self.opponent_score} {self.opponent}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # If match is being completed, set completed_at
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        
        super().save(*args, **kwargs)
        
        # Update team statistics only when match is completed
        if self.status == 'completed':
            team = self.team
            # Only update if not already counted
            if is_new or self._state.adding:
                team.matches_played += 1
                
                if self.team_score > self.opponent_score:
                    team.matches_won += 1
                elif self.team_score < self.opponent_score:
                    team.matches_lost += 1
                else:
                    team.matches_drawn += 1
                
                team.save()


class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15)
    location = models.CharField(max_length=100)
    team = models.ForeignKey(
        Team, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='players'
    )
    date_of_birth = models.DateField(null=True, blank=True)  # Added
    is_active = models.BooleanField(default=True)  # Added
    joined_at = models.DateTimeField(auto_now_add=True)  # Added
    
    class Meta:
        ordering = ['user__username']
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - Player"
    
    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username
    
    @property
    def age(self):
        if self.date_of_birth:
            today = datetime_date.today()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None
    
    @property
    def has_team(self):
        return self.team is not None
    
    def save(self, *args, **kwargs):
        # If player has a team, update team's current_members
        if self.pk:
            old_team = Player.objects.get(pk=self.pk).team
            if old_team != self.team:
                if old_team:
                    old_team.current_members = old_team.players.count()
                    old_team.save()
                if self.team:
                    self.team.current_members = self.team.players.count()
                    self.team.save()
        else:
            # New player
            if self.team:
                self.team.current_members = self.team.players.count() + 1
                self.team.save()
        
        super().save(*args, **kwargs)


# models.py
class Trainer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, default='')  # ← Add default
    location = models.CharField(max_length=100, default="Location not provided")
    specialization = models.CharField(max_length=100, default="General")
    experience_years = models.IntegerField(validators=[MinValueValidator(0)], default=0)  # ← Add default
    certificate = models.FileField(
        upload_to='trainer_certificates/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Upload your certificate (PDF format)",
        null=True,
        blank=True
    )
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='verified_trainers'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - Trainer ({self.specialization})"
    
    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username
    
    @property
    def certificate_url(self):
        if self.certificate:
            return self.certificate.url
        return None
    
    @property
    def is_experienced(self):
        return self.experience_years >= 5


class TournamentOrganiser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organisation_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    location = models.CharField(max_length=100, default="Location not provided")
    is_verified = models.BooleanField(default=False)  # Added
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_organisers')
    verified_at = models.DateTimeField(null=True, blank=True)  # Added
    created_at = models.DateTimeField(auto_now_add=True)  # Added
    
    class Meta:
        ordering = ['organisation_name']
    
    def __str__(self):
        return f"{self.organisation_name} - {self.user.username}"
    
    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username
    
    def save(self, *args, **kwargs):
        if self.is_verified and not self.verified_at:
            self.verified_at = timezone.now()
        super().save(*args, **kwargs)


class TournamentSchedule(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
    ]
    
    name = models.CharField(max_length=100)
    team1 = models.ForeignKey(
        Team, 
        on_delete=models.CASCADE, 
        related_name='tournaments_as_team1'
    )
    team2 = models.ForeignKey(
        Team, 
        on_delete=models.CASCADE, 
        related_name='tournaments_as_team2'
    )
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=200)
    
    # Additional fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    score_team1 = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    score_team2 = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    winner = models.ForeignKey(
        Team, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='won_tournament_matches'
    )
    
    # Tracking
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_tournament_matches'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['date', 'time']
        unique_together = ['date', 'time', 'location']  # Prevent double booking
        verbose_name = "Tournament Match"
        verbose_name_plural = "Tournament Matches"
    
    def __str__(self):
        return f"{self.name} - {self.team1.team_name} vs {self.team2.team_name} ({self.date})"
    
    @property
    def is_upcoming(self):
        return datetime_date.today() < self.date
    
    @property
    def is_today(self):
        return datetime_date.today() == self.date
    
    @property
    def is_past(self):
        return datetime_date.today() > self.date
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    @property
    def match_result(self):
        if not self.is_completed:
            return "Match not completed yet"
        if self.score_team1 > self.score_team2:
            return f"{self.team1.team_name} won"
        elif self.score_team2 > self.score_team1:
            return f"{self.team2.team_name} won"
        else:
            return "Match drawn"
    
    @property
    def teams_display(self):
        return f"{self.team1.team_name} vs {self.team2.team_name}"
    
    @property
    def status_display(self):
        if self.is_completed:
            return "Completed"
        elif self.is_today:
            return "Today"
        elif self.is_upcoming:
            return "Upcoming"
        else:
            return self.get_status_display()
    
    def save(self, *args, **kwargs):
        # Validate teams are different
        if self.team1 == self.team2:
            raise ValueError("A team cannot play against itself!")
        
        # Auto-calculate winner based on scores
        if self.status == 'completed':
            if self.score_team1 > self.score_team2:
                self.winner = self.team1
            elif self.score_team2 > self.score_team1:
                self.winner = self.team2
            else:
                self.winner = None
            
            # Set completed date if not set
            if not self.completed_at:
                self.completed_at = timezone.now()
            
            # Update team statistics
            self._update_team_stats()
        
        super().save(*args, **kwargs)
    
    def _update_team_stats(self):
        """Update team statistics when match is completed"""
        if self.status != 'completed':
            return
        
        # Update both teams' matches played
        self.team1.matches_played += 1
        self.team2.matches_played += 1
        
        # Update wins/losses/draws
        if self.winner == self.team1:
            self.team1.matches_won += 1
            self.team2.matches_lost += 1
        elif self.winner == self.team2:
            self.team2.matches_won += 1
            self.team1.matches_lost += 1
        else:
            self.team1.matches_drawn += 1
            self.team2.matches_drawn += 1
        
        # Save team stats without triggering recursion
        self.team1.save(update_fields=['matches_played', 'matches_won', 'matches_lost', 'matches_drawn'])
        self.team2.save(update_fields=['matches_played', 'matches_won', 'matches_lost', 'matches_drawn'])





# myfirstapp/models.py

# ... your existing models (Team, Match, Player, Trainer, TournamentOrganiser, TournamentSchedule) ...

# ========== CHAT MODELS ==========
# Add these at the very end of the file

class ChatRoom(models.Model):
    ROOM_TYPES = (
        ('individual', 'Individual'),
        ('group', 'Group'),
    )
    
    name = models.CharField(max_length=100, blank=True, null=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='individual')
    participants = models.ManyToManyField('auth.User', related_name='chat_rooms', blank=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='created_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        if self.room_type == 'individual':
            other_users = self.participants.exclude(id=self.created_by.id)
            if other_users.exists():
                return f"Chat with {other_users.first().username}"
            return f"Individual Chat {self.id}"
        return self.name or f"Group Chat {self.id}"
    
    @property
    def last_message(self):
        return self.messages.order_by('-sent_at').first()
    
    def unread_count(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['sent_at']
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:30]}..."
    
    def mark_as_read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save()


class MessageAttachment(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='chat_attachments/')
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.filename