from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.utils import timezone
from datetime import date as datetime_date
from django.core.validators import MinValueValidator, MaxValueValidator


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
    
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_teams'
    )
    approved_date = models.DateTimeField(null=True, blank=True)
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
    def update_member_count(self):
        """Update current_members to match actual player count"""
        self.current_members = self.players.count()
        self.save(update_fields=['current_members'])
    
    @property
    def win_rate(self):
        if self.matches_played == 0:
            return 0
        return (self.matches_won / self.matches_played) * 100
    
    @property
    def status(self):
        return "Approved" if self.is_approved else "Pending Approval"
    
    def save(self, *args, **kwargs):
        if self.is_approved and not self.approved_date:
            self.approved_date = timezone.now()
        super().save(*args, **kwargs)
        if self.pk:
            actual_members = self.players.count()
            if self.current_members != actual_members:
                self.current_members = actual_members
                super().save(update_fields=['current_members'])
    


class Match(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='matches')
    opponent = models.CharField(max_length=100)
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    team_score = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    opponent_score = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    location = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
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
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)
        if self.status == 'completed':
            team = self.team
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
    date_of_birth = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    
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
            if self.team:
                self.team.current_members = self.team.players.count() + 1
                self.team.save()
        
        super().save(*args, **kwargs)


class Trainer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, default='')
    location = models.CharField(max_length=100, default="Location not provided")
    specialization = models.CharField(max_length=100, default="General")
    experience_years = models.IntegerField(validators=[MinValueValidator(0)], default=0)
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


class TournamentOrganiser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organisation_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    location = models.CharField(max_length=100, default="Location not provided")
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_organisers')
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['organisation_name']
    
    def __str__(self):
        return f"{self.organisation_name} - {self.user.username}"


# ========== TOURNAMENT MODELS ==========

class Tournament(models.Model):
    """A tournament event that teams can apply to participate in"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('open', 'Open for Applications'),
        ('closed', 'Closed'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    name = models.CharField(max_length=200)
    sport_type = models.CharField(max_length=100, help_text="e.g., Football, Basketball, Tennis")
    location = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Dates
    start_date = models.DateField()
    end_date = models.DateField()
    application_deadline = models.DateField()
    
    # Capacity
    max_teams = models.IntegerField(default=8, validators=[MinValueValidator(2)])
    min_teams = models.IntegerField(default=2, validators=[MinValueValidator(2)])
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Organiser
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tournaments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.sport_type}"
    
    @property
    def accepted_teams_count(self):
        return self.applications.filter(status='approved').count()
    
    @property
    def pending_teams_count(self):
        return self.applications.filter(status='pending').count()
    
    @property
    def total_applications_count(self):
        return self.applications.count()
    
    @property
    def spots_remaining(self):
        return self.max_teams - self.accepted_teams_count
    
    @property
    def is_full(self):
        return self.accepted_teams_count >= self.max_teams
    
    @property
    def can_apply(self):
        """Check if teams can still apply"""
        from django.utils import timezone
        return (self.status == 'open' and 
                not self.is_full and 
                timezone.now().date() <= self.application_deadline)
    
    def update_status(self):
        """Auto-update status based on conditions"""
        from django.utils import timezone
        today = timezone.now().date()
        
        if self.accepted_teams_count >= self.max_teams:
            self.status = 'closed'
        elif self.application_deadline < today and self.status == 'open':
            self.status = 'closed'
        elif self.start_date <= today <= self.end_date and self.status == 'closed':
            self.status = 'ongoing'
        elif self.end_date < today and self.status == 'ongoing':
            self.status = 'completed'
        self.save()


class TournamentApplication(models.Model):
    """Team application to join a tournament"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    ]
    
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='applications')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='tournament_applications')
    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='tournament_applications')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-applied_at']
        unique_together = ['tournament', 'team']
    
    def __str__(self):
        return f"{self.team.team_name} - {self.tournament.name} ({self.status})"
    
    def approve(self):
        self.status = 'approved'
        self.reviewed_at = timezone.now()
        self.save()
        self.tournament.update_status()
    
    def decline(self, notes=None):
        self.status = 'declined'
        self.reviewed_at = timezone.now()
        if notes:
            self.review_notes = notes
        self.save()


class TournamentSchedule(models.Model):
    """General match schedule (public timetable)"""
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
        unique_together = ['date', 'time', 'location']
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
    def status_display(self):
        if self.is_completed:
            return "Completed"
        elif self.is_today:
            return "Today"
        elif self.is_upcoming:
            return "Upcoming"
        return self.get_status_display()
    
    def save(self, *args, **kwargs):
        if self.team1 == self.team2:
            raise ValueError("A team cannot play against itself!")
        
        if self.status == 'completed':
            if self.score_team1 > self.score_team2:
                self.winner = self.team1
            elif self.score_team2 > self.score_team1:
                self.winner = self.team2
            else:
                self.winner = None
            
            if not self.completed_at:
                self.completed_at = timezone.now()
            self._update_team_stats()
        
        super().save(*args, **kwargs)
    
    def _update_team_stats(self):
        if self.status != 'completed':
            return
        
        self.team1.matches_played += 1
        self.team2.matches_played += 1
        
        if self.winner == self.team1:
            self.team1.matches_won += 1
            self.team2.matches_lost += 1
        elif self.winner == self.team2:
            self.team2.matches_won += 1
            self.team1.matches_lost += 1
        else:
            self.team1.matches_drawn += 1
            self.team2.matches_drawn += 1
        
        self.team1.save(update_fields=['matches_played', 'matches_won', 'matches_lost', 'matches_drawn'])
        self.team2.save(update_fields=['matches_played', 'matches_won', 'matches_lost', 'matches_drawn'])


class TournamentMatch(models.Model):
    """Matches within a specific tournament"""
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
    ]
    
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='matches')
    team1 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='tournament_matches_team1')
    team2 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='tournament_matches_team2')
    match_number = models.IntegerField(default=1)
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    score_team1 = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    score_team2 = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    winner = models.ForeignKey(
        Team, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='won_tournament_match_matches'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['date', 'time']
    
    def __str__(self):
        return f"{self.tournament.name} - {self.team1.team_name} vs {self.team2.team_name}"


# ========== CHAT MODELS ==========

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


# ========== TRAINER WORKFLOW MODELS ==========

class TeamJoinRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='join_requests')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='join_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']
        unique_together = ['player', 'team']

    def __str__(self):
        return f"{self.player.full_name} requested to join {self.team.team_name}"

    def accept(self):
        """Accept the join request and add player to team"""
        self.status = 'accepted'
        self.responded_at = timezone.now()
        
        # Assign player to the team
        self.player.team = self.team
        self.player.save()
        
        # Update team's current_members count
        self.team.current_members = self.team.players.count()
        self.team.save()
        
        self.save()

    def decline(self):
        """Decline the join request"""
        self.status = 'declined'
        self.responded_at = timezone.now()
        self.save()

class TrainingSession(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='training_sessions')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='training_sessions')
    title = models.CharField(max_length=100)
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['date', 'time']

    def __str__(self):
        return f"{self.title} - {self.team.team_name} on {self.date}"

    @property
    def status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    @property
    def status_badge_class(self):
        badges = {
            'pending': 'bg-warning text-dark',
            'in_progress': 'bg-info',
            'completed': 'bg-success',
            'cancelled': 'bg-danger',
        }
        return badges.get(self.status, 'bg-secondary')
    
    @property
    def is_upcoming(self):
        from datetime import date
        return date.today() < self.date
    
    @property
    def is_today(self):
        from datetime import date
        return date.today() == self.date
    
    @property
    def is_past(self):
        from datetime import date
        return date.today() > self.date and self.status != 'completed'
class PlayerFeedback(models.Model):

    FEEDBACK_TYPES = [
        ('Positive', 'Positive'),
        ('Constructive', 'Constructive'),
        ('Excellent', 'Excellent'),
        ('Needs Improvement', 'Needs Improvement'),
    ]

    SKILL_CATEGORIES = [
        ('Physical Performance', 'Physical Performance'),
        ('Technical Skills', 'Technical Skills'),
        ('Tactical Awareness', 'Tactical Awareness'),
        ('Mental Performance', 'Mental Performance'),
    ]

    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='given_feedback')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='feedback')

    feedback_type = models.CharField(
        max_length=30,
        choices=FEEDBACK_TYPES,
        default='Positive'
    )

    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=3
    )

    skill_category = models.CharField(
        max_length=50,
        choices=SKILL_CATEGORIES,
        default='Physical Performance'
    )

    status = models.BooleanField(default=False)

    detailed_feedback = models.TextField(default="")
    strengths = models.TextField(blank=True, default="")
    improvements = models.TextField(blank=True, default="")
    goals = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
    

class Feedback(models.Model):
    FEEDBACK_TYPES = [
        ('positive', 'Positive'),
        ('constructive', 'Constructive'),
        ('general', 'General'),
        ('performance_review', 'Performance Review'),
    ]
    
    SKILL_CATEGORIES = [
        ('technique', 'Technical Skills'),
        ('tactical', 'Tactical Awareness'),
        ('physical', 'Physical Performance'),
        ('mental', 'Mental/Behavioral'),
        ('teamwork', 'Teamwork & Communication'),
    ]
    
    trainer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_feedback')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='received_feedback')
    feedback_type = models.CharField(max_length=50, choices=FEEDBACK_TYPES)
    rating = models.IntegerField(
        choices=[(1, '1 - Needs Improvement'), (2, '2 - Below Average'), 
                 (3, '3 - Average'), (4, '4 - Good'), (5, '5 - Excellent')],
        null=True, 
        blank=True
    )
    skill_category = models.CharField(max_length=50, choices=SKILL_CATEGORIES, blank=True)
    comment = models.TextField()
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    goals = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Feedback from {self.trainer.username} to {self.player.user.username} - {self.created_at.date()}"