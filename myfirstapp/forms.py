import re
import os
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import FileExtensionValidator
from .models import (
    Trainer, TournamentOrganiser, Team, Player,
    TournamentSchedule, ChatRoom, Message,TeamJoinRequest, TrainingSession, TournamentApplication, PlayerFeedback
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

    # Keep all your clean_ methods here directly
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
        self.fields['selected_team'].queryset = Team.objects.filter(is_approved=True)
    
    def clean_selected_team(self):
        team = self.cleaned_data.get('selected_team')
        location = self.cleaned_data.get('location')
        
        # if team and location:
        #     if team.location.lower() != location.lower():
        #         raise forms.ValidationError(
        #             f"This team is not available in {location}. Please select a team in your location."
        #         )
        
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
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if field.widget.__class__ in [forms.TextInput, forms.EmailInput, 
                                          forms.PasswordInput, forms.NumberInput]:
                field.widget.attrs['class'] = 'form-control'
            elif field.widget.__class__ == forms.FileInput:
                field.widget.attrs['class'] = 'form-control'
    
    class Meta(BaseUserRegistrationForm.Meta):
        fields = BaseUserRegistrationForm.Meta.fields + ['specialization', 'experience_years']
    
    def clean_certificate(self):
        certificate = self.cleaned_data['certificate']
        
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
            experience_years=self.cleaned_data['experience_years']
        )
        
        return user

class TournamentOrganiserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class TournamentScheduleForm(forms.ModelForm):
    team1 = forms.ModelChoiceField(
        queryset=Team.objects.filter(is_approved=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        label="Team 1",
        empty_label="Select Team 1"
    )
    
    team2 = forms.ModelChoiceField(
        queryset=Team.objects.filter(is_approved=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        label="Team 2",
        empty_label="Select Team 2"
    )
    
    class Meta:
        model = TournamentSchedule
        fields = ['name', 'team1', 'team2', 'date', 'time', 'location']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter match name'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter location'}),
        }
        labels = {
            'name': 'Match Name',
            'date': 'Match Date',
            'time': 'Match Time',
            'location': 'Venue/Location',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        team1 = cleaned_data.get('team1')
        team2 = cleaned_data.get('team2')
        
        if team1 and team2 and team1 == team2:
            raise forms.ValidationError("A team cannot play against itself!")
        
        return cleaned_data

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
        labels = {
            'organisation_name': 'Organisation Name',
            'phone_number': 'Phone Number',
            'location': 'Location',
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

        # ========== TRAINER WORKFLOW FORMS ==========

class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['team_name', 'location', 'max_members']
        widgets = {
            'team_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter team name'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter team location'}),
            'max_members': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Maximum members'}),
        }


class TeamJoinRequestForm(forms.ModelForm):
    class Meta:
        model = TeamJoinRequest
        fields = ['team']


class TrainingSessionForm(forms.ModelForm):
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


class TournamentApplicationForm(forms.ModelForm):
    class Meta:
        model = TournamentApplication
        fields = ['team', 'tournament_name', 'reason']
        widgets = {
            'team': forms.Select(attrs={'class': 'form-select'}),
            'tournament_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tournament name'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason for applying'}),
        }


class PlayerFeedbackForm(forms.ModelForm):
    class Meta:
        model = PlayerFeedback
        fields = ['player', 'team', 'feedback', 'rating']
        widgets = {
            'player': forms.Select(attrs={'class': 'form-select'}),
            'team': forms.Select(attrs={'class': 'form-select'}),
            'feedback': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Write feedback for the player'}),
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
        }