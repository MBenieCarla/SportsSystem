from django import forms
from django.contrib.auth import get_user_model
from .models import TrainingSession, Tournament, Match, PerformanceFeedback, Team
from .models import Message, ChatRoom

User = get_user_model()


# ==================== TRAINING SESSION FORM ====================
class TrainingSessionForm(forms.ModelForm):
    """Form for creating/editing training sessions"""
    
    class Meta:
        model = TrainingSession
        fields = ['team', 'title', 'description', 'date', 'start_time', 'end_time', 'location', 'max_participants']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Get the logged-in user from kwargs
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only show teams that belong to this trainer
        if user:
            self.fields['team'].queryset = Team.objects.filter(trainer=user)
        
        # Add CSS class to all fields
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
    
    def clean(self):
        """Validate that end time is after start time"""
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError("End time must be after start time")
        return cleaned_data


# ==================== TOURNAMENT FORM ====================
class TournamentForm(forms.ModelForm):
    """Form for creating/editing tournaments"""
    
    class Meta:
        model = Tournament
        fields = ['title', 'description', 'sport_type', 'start_date', 'end_date', 
                 'location', 'registration_deadline', 'max_teams']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'registration_deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
    
    def clean(self):
        """Validate dates: end date after start date, deadline before start"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        registration_deadline = cleaned_data.get('registration_deadline')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("End date must be after start date")
        
        if registration_deadline and start_date and registration_deadline > start_date:
            raise forms.ValidationError("Registration deadline must be before start date")
        
        return cleaned_data


# ==================== MATCH FORM ====================
class MatchForm(forms.ModelForm):
    """Form for creating/editing matches"""
    
    class Meta:
        model = Match
        fields = ['team_home', 'team_away', 'date', 'time', 'location']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Get tournament from kwargs to filter teams
        tournament = kwargs.pop('tournament', None)
        super().__init__(*args, **kwargs)
        
        # Only show teams registered in this tournament
        if tournament:
            self.fields['team_home'].queryset = tournament.teams_registered.all()
            self.fields['team_away'].queryset = tournament.teams_registered.all()
        
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
    
    def clean(self):
        """Validate that home and away teams are different"""
        cleaned_data = super().clean()
        team_home = cleaned_data.get('team_home')
        team_away = cleaned_data.get('team_away')
        
        if team_home and team_away and team_home == team_away:
            raise forms.ValidationError("Home and away teams cannot be the same")
        return cleaned_data


# ==================== PERFORMANCE FEEDBACK FORM ====================
class PerformanceFeedbackForm(forms.ModelForm):
    """Form for trainers to give performance feedback to players"""
    
    class Meta:
        model = PerformanceFeedback
        fields = ['player', 'skills_rating', 'teamwork_rating', 'attendance_rating', 
                 'attitude_rating', 'overall_comment', 'areas_for_improvement']
        widgets = {
            'skills_rating': forms.NumberInput(attrs={'min': 1, 'max': 10, 'class': 'form-control'}),
            'teamwork_rating': forms.NumberInput(attrs={'min': 1, 'max': 10, 'class': 'form-control'}),
            'attendance_rating': forms.NumberInput(attrs={'min': 1, 'max': 10, 'class': 'form-control'}),
            'attitude_rating': forms.NumberInput(attrs={'min': 1, 'max': 10, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Get trainer from kwargs
        trainer = kwargs.pop('trainer', None)
        super().__init__(*args, **kwargs)
        
        # Only show players that belong to this trainer's teams
        if trainer:
            self.fields['player'].queryset = User.objects.filter(
                player_teams__trainer=trainer  # ✅ FIXED: use player_teams
            ).distinct()
        
        # Add CSS class to all fields except rating fields (they already have it)
        for field in self.fields:
            if field not in ['skills_rating', 'teamwork_rating', 'attendance_rating', 'attitude_rating']:
                self.fields[field].widget.attrs.update({'class': 'form-control'})


# ==================== TEAM FORM ====================
class TeamForm(forms.ModelForm):
    """Form for creating/editing teams"""
    
    class Meta:
        model = Team
        fields = ['name', 'sport_type', 'location', 'description', 'max_players']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field != 'description':
                self.fields[field].widget.attrs.update({'class': 'form-control'})


# ==================== MESSAGE FORM ====================
class MessageForm(forms.ModelForm):
    """Form for sending chat messages"""
    
    class Meta:
        model = Message
        fields = ['content', 'attachment']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Type your message here...'
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,.pdf,.doc,.docx'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['attachment'].required = False  # Attachment is optional


# ==================== CREATE CHAT ROOM FORM ====================
class CreateChatRoomForm(forms.ModelForm):
    """Form for creating a new chat room"""
    
    # Field for selecting participants (multiple users)
    participants = forms.ModelMultipleChoiceField(
        queryset=None,  # Will be set in __init__ based on user
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=True,
        help_text="Hold Ctrl/Cmd to select multiple participants"
    )
    
    class Meta:
        model = ChatRoom
        fields = ['room_type', 'name', 'participants', 'team', 'tournament']
        widgets = {
            'room_type': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Chat name (optional)'}),
            'team': forms.Select(attrs={'class': 'form-control'}),
            'tournament': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Get the logged-in user from kwargs
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # ✅ FIXED: queryset (not querieset)
            # Show all users except the current user as potential participants
            self.fields['participants'].queryset = User.objects.exclude(id=user.id)
            
            # Show all active teams
            self.fields['team'].queryset = Team.objects.filter(is_active=True)
            
            # Show all tournaments
            self.fields['tournament'].queryset = Tournament.objects.all()
    
    def clean(self):
        """Validate that participants are selected"""
        cleaned_data = super().clean()
        participants = cleaned_data.get('participants')
        
        if not participants:
            raise forms.ValidationError("Please select at least one participant")
        
        return cleaned_data