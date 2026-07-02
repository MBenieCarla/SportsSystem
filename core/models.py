from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Team(models.Model):
    """Team model - represents a sports team"""
    name = models.CharField(max_length=100)
    trainer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='trainer_teams'
    )
    players = models.ManyToManyField(
        User, 
        related_name='player_teams',
        blank=True
    )
    sport_type = models.CharField(max_length=50)
    location = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    max_players = models.IntegerField(default=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def get_player_count(self):
        return self.players.count()
    
    def get_available_slots(self):
        return self.max_players - self.get_player_count()
    
    class Meta:
        db_table = 'teams'
        ordering = ['-created_at']


class TrainingSession(models.Model):
    """Training session model"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='training_sessions')
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=200)
    max_participants = models.IntegerField(default=20)
    is_cancelled = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_trainings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.date}"
    
    def get_attendance_count(self):
        return self.attendances.filter(attended=True).count()
    
    class Meta:
        db_table = 'training_sessions'
        ordering = ['date', 'start_time']


class PlayerTrainingAttendance(models.Model):
    """Tracks player attendance at training sessions"""
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='training_attendances')
    training = models.ForeignKey(TrainingSession, on_delete=models.CASCADE, related_name='attendances')
    attended = models.BooleanField(default=False)
    feedback = models.TextField(blank=True, null=True)
    performance_rating = models.IntegerField(default=0, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'player_training_attendances'
        unique_together = ['player', 'training']


class Tournament(models.Model):
    """Tournament model - created by organizers"""
    STATUS_CHOICES = (
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tournaments')
    sport_type = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    location = models.CharField(max_length=200)
    registration_deadline = models.DateField()
    max_teams = models.IntegerField(default=16)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    teams_registered = models.ManyToManyField(Team, related_name='tournaments', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    def get_team_count(self):
        return self.teams_registered.count()
    
    def get_available_slots(self):
        return self.max_teams - self.get_team_count()
    
    class Meta:
        db_table = 'tournaments'
        ordering = ['-start_date']


class Match(models.Model):
    """Match model - individual matches within tournaments"""
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='matches')
    team_home = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    team_away = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=200)
    score_home = models.IntegerField(default=0, blank=True, null=True)
    score_away = models.IntegerField(default=0, blank=True, null=True)
    is_played = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.team_home.name} vs {self.team_away.name} - {self.date}"
    
    def get_score_display(self):
        if self.is_played:
            return f"{self.score_home} - {self.score_away}"
        return "Not Played Yet"
    
    class Meta:
        db_table = 'matches'
        ordering = ['date', 'time']


class PerformanceFeedback(models.Model):
    """Trainer feedback for players"""
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='performance_feedback')
    trainer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_feedback')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='feedback')
    date = models.DateField(auto_now_add=True)
    skills_rating = models.IntegerField()
    teamwork_rating = models.IntegerField()
    attendance_rating = models.IntegerField()
    attitude_rating = models.IntegerField()
    overall_comment = models.TextField()
    areas_for_improvement = models.TextField(blank=True, null=True)
    
    def get_average_rating(self):
        return (self.skills_rating + self.teamwork_rating + 
                self.attendance_rating + self.attitude_rating) / 4
    
    class Meta:
        db_table = 'performance_feedback'
        ordering = ['-date']


class ChatRoom(models.Model):
    """Chat room for messages"""
    ROOM_TYPES = (
        ('direct', 'Direct Message'),
        ('team', 'Team Chat'),
        ('tournament', 'Tournament Chat'),
    )
    
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='direct')
    name = models.CharField(max_length=200, blank=True, null=True)
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True, related_name='chat_rooms')
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, null=True, blank=True, related_name='chat_rooms')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        if self.room_type == 'direct':
            return f"Chat between {', '.join([u.username for u in self.participants.all()])}"
        return f"{self.get_room_type_display()}: {self.name or 'Unnamed'}"
    
    def get_last_message(self):
        return self.messages.order_by('-created_at').first()
    
    def get_unread_count(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()
    
    class Meta:
        db_table = 'chat_rooms'
        ordering = ['-updated_at']


class Message(models.Model):
    """Individual messages in chat rooms"""
    MESSAGE_TYPES = (
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
    )
    
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    content = models.TextField()
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"
    
    def mark_as_read(self, user):
        """Mark message as read by a user"""
        if user != self.sender and not self.read_receipts.filter(user=user).exists():
            MessageReadReceipt.objects.create(message=self, user=user)
            participants_count = self.chat_room.participants.count()
            read_count = self.read_receipts.count()
            if read_count >= participants_count - 1:
                self.is_read = True
                self.save()
    
    class Meta:
        db_table = 'messages'
        ordering = ['created_at']


class MessageReadReceipt(models.Model):
    """Tracks which users have read which messages"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_receipts')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_read_receipts')
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'message_read_receipts'
        unique_together = ['message', 'user']


class TeamJoinRequest(models.Model):
    """Player requests to join a team"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='join_requests')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='join_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True, null=True)
    responded_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'team_join_requests'
        unique_together = ['player', 'team']


class TournamentTeamRequest(models.Model):
    """Team requests to join a tournament - NEW MODEL"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='team_requests')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='tournament_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True, null=True)
    responded_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tournament_team_requests'
        unique_together = ['tournament', 'team']

class TournamentApplication(models.Model):
    """Model for teams applying to tournaments"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    tournament = models.ForeignKey('Tournament', on_delete=models.CASCADE, related_name='applications')
    team = models.ForeignKey('Team', on_delete=models.CASCADE, related_name='tournament_applications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True, null=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'tournament_applications'
        unique_together = ['tournament', 'team']
    
    def __str__(self):
        return f"{self.team.name} - {self.tournament.title} ({self.status})"