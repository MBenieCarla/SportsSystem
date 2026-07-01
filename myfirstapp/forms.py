import re
import os
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import FileExtensionValidator
from .models import (
    Trainer, TournamentOrganiser, Team, Player,
    TournamentSchedule, ChatRoom, Message, TeamJoinRequest, 
    TrainingSession, TournamentApplication, PlayerFeedback,
    Feedback, Tournament, TournamentMatch
)


class BaseUserRegistrationForm(UserCreationForm):
    
    username = forms.CharField(
        max_length=150, required=True, label="Username",
        widget=forms.TextInput(attrs={'placeholder': 'Enter your username'})
    )
    email = forms.EmailField(
        max_length=100, required=True, label="Email",
        widget=forms.EmailInput(attrs={'placeholder': 'Your email should consist of @gmail.com'})
    )
    phone_number = forms.CharField(
        max_length=15, required=True, label="Phone Number",
        widget=forms.TextInput(attrs={'placeholder': 'Enter 10 digits phone number'})
    )
    location = forms.CharField(
        max_length=100, required=True, label="Location",
        widget=forms.TextInput(attrs={'placeholder': 'Enter your city (e.g., LA, New York)'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

    def clean_email(self):
        email = self.cleaned_data['email']
        if '@gmail.com' not in email:
            raise forms.ValidationError("Email must be a Gmail address (@gmail.com)")
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number']
        phone = re.sub(r'\D', '', phone)
        if len(phone) != 10:
            raise forms.ValidationError("Phone number must have exactly 10 digits")
        return phone
    
    def clean_password1(self):
        password = self.cleaned_data['password1']
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long")
        if not any(char.isdigit() for char in password):
            raise forms.ValidationError("Password must contain at least one digit")
        if not any(char.isupper() for char in password):
            raise forms.ValidationError("Password must contain at least one uppercase letter")
        return password

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match")
        return password2

# ========== PLAYER REGISTRATION FORM ==========

class PlayerRegistrationForm(BaseUserRegistrationForm):
    """Form for player registration"""
    
    selected_team = forms.ModelChoiceField(
        queryset=Team.objects.none(),
        widget=forms.RadioSelect,
        required=True,
        label="Select Your Team"
    )
    
    class Meta(BaseUserRegistrationForm.Meta):
        fields = BaseUserRegistrationForm.Meta.fields + ['selected_team']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        location = self.initial.get('location') or self.data.get('location')
        
        if location:
            self.fields['selected_team'].queryset = Team.objects.filter(
                location__iexact=location,
                is_approved=True
            )
            if not self.fields['selected_team'].queryset.exists():
                self.fields['selected_team'].help_text = f"No teams found in {location}"
        else:
            self.fields['selected_team'].queryset = Team.objects.none()
            self.fields['selected_team'].help_text = "Please enter your location first"
    
    def clean_selected_team(self):
        team = self.cleaned_data.get('selected_team')
        location = self.cleaned_data.get('location')
        
        if team and location:
            if team.location.lower() != location.lower():
                raise forms.ValidationError(
                    f"This team is not available in {location}. Please select a team in your location."
                )
        
        if team and not team.is_available:
            raise forms.ValidationError(f"Sorry, {team.team_name} is full! Please select another team.")
        
        return team
    
    def save(self, commit=True):
        user = super().save(commit=True)
        
        player = Player.objects.create(
            user=user,
            phone_number=self.cleaned_data['phone_number'],
            location=self.cleaned_data['location'],
            team=None
        )
        
        TeamJoinRequest.objects.create(
            player=player,
            team=self.cleaned_data['selected_team']
        )
        
        return user

# ========== TRAINER REGISTRATION FORM ==========

class TrainerRegistrationForm(UserCreationForm):
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'})
    )
    location = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your location'})
    )
    specialization = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Football, Basketball'})
    )
    experience_years = forms.IntegerField(
        required=True,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Years of experience'})
    )
    certificate = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 
                 'phone_number', 'location', 'specialization', 
                 'experience_years', 'certificate']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field.widget.__class__ in [forms.TextInput, forms.EmailInput, 
                                          forms.PasswordInput, forms.NumberInput]:
                field.widget.attrs['class'] = 'form-control'
            elif field.widget.__class__ == forms.FileInput:
                field.widget.attrs['class'] = 'form-control'
    
    def clean_certificate(self):
        certificate = self.cleaned_data['certificate']
        if certificate:
            if certificate.size > 5 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 5MB")
            file_extension = os.path.splitext(certificate.name)[1].lower()
            if file_extension != '.pdf':
                raise forms.ValidationError("Only PDF files are allowed")
            if certificate.content_type != 'application/pdf':
                raise forms.ValidationError("File must be a valid PDF document")
        return certificate
    
    def save(self, commit=True):
        user = super().save(commit=True)
        Trainer.objects.create(
            user=user,
            phone_number=self.cleaned_data['phone_number'],
            location=self.cleaned_data['location'],
            specialization=self.cleaned_data['specialization'],
            experience_years=self.cleaned_data['experience_years'],
            certificate=self.cleaned_data['certificate']
        )
        return user

# ========== TOURNAMENT ORGANISER REGISTRATION FORM ==========

class TournamentOrganiserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

# ========== TOURNAMENT FORMS ==========

class TournamentForm(forms.ModelForm):
    """Form for creating/editing tournaments"""
    class Meta:
        model = Tournament
        fields = ['name', 'sport_type', 'location', 'description', 
                  'start_date', 'end_date', 'application_deadline', 
                  'max_teams', 'min_teams']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Nairobi Football Championship 2024'}),
            'sport_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Football, Basketball'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Kasarani Stadium'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Tournament details...'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'application_deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'max_teams': forms.NumberInput(attrs={'class': 'form-control', 'min': 2, 'placeholder': 'e.g., 8'}),
            'min_teams': forms.NumberInput(attrs={'class': 'form-control', 'min': 2, 'placeholder': 'e.g., 2'}),
        }
        labels = {
            'name': 'Tournament Name',
            'sport_type': 'Sport Type',
            'location': 'Location',
            'description': 'Description',
            'start_date': 'Start Date',
            'end_date': 'End Date',
            'application_deadline': 'Application Deadline',
            'max_teams': 'Maximum Teams',
            'min_teams': 'Minimum Teams Required',
        }
        help_texts = {
            'application_deadline': 'Teams must apply before this date.',
            'max_teams': 'Maximum number of teams that can participate.',
            'min_teams': 'Minimum teams required for the tournament to proceed.',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        application_deadline = cleaned_data.get('application_deadline')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("End date must be after start date.")
        
        if application_deadline and start_date and application_deadline > start_date:
            raise forms.ValidationError("Application deadline must be before the start date.")
        
        return cleaned_data


class TournamentScheduleForm(forms.ModelForm):
    """Form for creating matches in the general schedule"""
    class Meta:
        model = TournamentSchedule
        fields = ['name', 'team1', 'team2', 'date', 'time', 'location']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Match name'}),
            'team1': forms.Select(attrs={'class': 'form-select'}),
            'team2': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location'}),
        }
        labels = {
            'name': 'Match Name',
            'team1': 'Team 1',
            'team2': 'Team 2',
            'date': 'Date',
            'time': 'Time',
            'location': 'Location',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show approved teams
        approved_teams = Team.objects.filter(
            tournament_applications__status='approved'
        ).distinct().order_by('team_name')
        self.fields['team1'].queryset = approved_teams
        self.fields['team2'].queryset = approved_teams


class TournamentApplicationForm(forms.ModelForm):
    """Form for trainers to apply to tournaments"""
    class Meta:
        model = TournamentApplication
        fields = ['tournament', 'reason']
        widgets = {
            'tournament': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Why should your team be selected?'}),
        }
        labels = {
            'tournament': 'Select Tournament',
            'reason': 'Application Reason',
        }
    
    def __init__(self, trainer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        trainer_teams = Team.objects.filter(trainer=trainer)
        self.fields['tournament'].queryset = Tournament.objects.filter(
            status='open'
        ).exclude(
            applications__team__in=trainer_teams,
            applications__status__in=['pending', 'approved']
        )


# ========== OTHER FORMS ==========

class OrganiserProfileForm(forms.ModelForm):
    """Form for updating organiser profile"""
    
    class Meta:
        model = TournamentOrganiser
        fields = ['organisation_name', 'phone_number', 'location']
        widgets = {
            'organisation_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter organisation name'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone number'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter location'
            }),
        }


class ChatRoomForm(forms.ModelForm):
    participants = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=True,
        help_text="Hold Ctrl to select multiple users"
    )
    
    class Meta:
        model = ChatRoom
        fields = ['name', 'participants']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Group name'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['participants'].queryset = User.objects.exclude(id=user.id)


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Type your message...'
            })
        }


class TeamForm(forms.ModelForm):
    """Form for trainers to create teams"""
    
    class Meta:
        model = Team
        fields = ['team_name', 'location', 'max_members']
        widgets = {
            'team_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter team name'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter team location'}),
            'max_members': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Maximum members'}),
        }
    
    def clean_team_name(self):
        team_name = self.cleaned_data['team_name']
        if Team.objects.filter(team_name__iexact=team_name).exists():
            raise forms.ValidationError("A team with this name already exists.")
        return team_name


class TrainingSessionForm(forms.ModelForm):
    """Form for trainers to create training sessions"""
    
    class Meta:
        model = TrainingSession
        fields = ['team', 'title', 'date', 'time', 'location', 'description']
        widgets = {
            'team': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Training title'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Training location'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Training details'}),
        }


class PlayerFeedbackForm(forms.ModelForm):

    def __init__(self, *args, trainer=None, **kwargs):
        super().__init__(*args, **kwargs)

        if trainer:
            self.fields['player'].queryset = Player.objects.filter(
                team__trainer=trainer
            )

    class Meta:
        model = PlayerFeedback
        fields = [
            'player',
            'feedback_type',
            'rating',
            'skill_category',
            'detailed_feedback',
            'strengths',
            'improvements',
            'goals',
        ]

        widgets = {
            'player': forms.Select(attrs={'class': 'form-select'}),
            'feedback_type': forms.Select(attrs={'class': 'form-select'}),
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 5
            }),
            'skill_category': forms.Select(attrs={'class': 'form-select'}),
            'detailed_feedback': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
            'strengths': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'improvements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'goals': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }

    def clean_rating(self):
        rating = self.cleaned_data['rating']
        if not 1 <= rating <= 5:
            raise forms.ValidationError("Rating must be between 1 and 5.")
        return rating


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = [
            'player', 
            'feedback_type', 
            'rating', 
            'skill_category', 
            'comment', 
            'strengths', 
            'areas_for_improvement', 
            'goals'
        ]
        widgets = {
            'player': forms.Select(attrs={'class': 'form-select'}),
            'feedback_type': forms.Select(attrs={'class': 'form-select'}),
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'skill_category': forms.Select(attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Provide detailed feedback here...'
            }),
            'strengths': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'List the player\'s key strengths...'
            }),
            'areas_for_improvement': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'What areas need improvement?...'
            }),
            'goals': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Set specific goals for the player...'
            }),
        }
    
    def __init__(self, trainer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['player'].queryset = Player.objects.filter(
            team__trainer=trainer
        ).select_related('user')
        self.fields['rating'].empty_label = 'Select rating...'
        self.fields['skill_category'].empty_label = 'Select skill category...'
        self.fields['rating'].required = False
        self.fields['skill_category'].required = False
        self.fields['strengths'].required = False
        self.fields['areas_for_improvement'].required = False
        self.fields['goals'].required = False