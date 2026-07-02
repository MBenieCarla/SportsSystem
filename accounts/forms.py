from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from django import forms
from core.models import Team, TeamJoinRequest 

class CustomUserCreationForm(UserCreationForm):
    USER_TYPES = (
        ('player', 'Player'),
        ('trainer', 'Trainer'),
        ('organizer', 'Tournament Organizer'),
    )
    
    user_type = forms.ChoiceField(
        choices=USER_TYPES, 
        widget=forms.RadioSelect,
        label='I want to register as:'
    )
    
    # ✅ Team dropdown for players
    team = forms.ModelChoiceField(
        queryset=Team.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Select a team to join'
    )
    
    phone_number = forms.CharField(
        max_length=15, 
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., 0712345678'})
    )
    location = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Nairobi, Karen'})
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Date of Birth'
    )
    
    class Meta:
        model = CustomUser
        fields = (
            'username', 
            'email', 
            'first_name', 
            'last_name', 
            'user_type', 
            'team',  # ✅ Add team here
            'phone_number', 
            'location', 
            'date_of_birth', 
            'password1', 
            'password2'
        )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes to all fields
        for field in self.fields:
            if field != 'user_type':
                self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Show only active teams
        self.fields['team'].queryset = Team.objects.filter(is_active=True)
        self.fields['team'].empty_label = "-- Select a team (optional) --"
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = self.cleaned_data['user_type']
        
        if commit:
            user.save()
            
            # ✅ If player selected a team, create join request
            if user.user_type == 'player':
                team = self.cleaned_data.get('team')
                if team:
                    TeamJoinRequest.objects.create(
                        player=user,
                        team=team,
                        status='pending',
                        message=f"{user.username} wants to join {team.name}"
                    )
        
        return user


class CustomUserLoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise forms.ValidationError('Username is required.')
        return username
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not password:
            raise forms.ValidationError('Password is required.')
        return password


class UserProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile (non-admin users)"""
    
    class Meta:
        model = CustomUser
        fields = (
            'first_name', 
            'last_name', 
            'email', 
            'phone_number', 
            'location', 
            'profile_picture'
        )
        widgets = {
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field != 'profile_picture':
                self.fields[field].widget.attrs.update({
                    'class': 'form-control'
                })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email


class AdminUserCreateForm(UserCreationForm):
    """Form for admin to create new users"""
    USER_TYPES = (
        ('player', 'Player'),
        ('trainer', 'Trainer'),
        ('organizer', 'Tournament Organizer'),
        ('admin', 'Administrator'),
    )
    
    user_type = forms.ChoiceField(choices=USER_TYPES)
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'user_type', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})


class CustomUserCreationForm(UserCreationForm):
    USER_TYPES = (
        ('player', 'Player'),
        ('trainer', 'Trainer'),
        ('organizer', 'Tournament Organizer'),
    )
    
    user_type = forms.ChoiceField(
        choices=USER_TYPES, 
        widget=forms.RadioSelect,
        label='I want to register as:'
    )
    
    # ✅ NEW: Team selection field for players
    team = forms.ModelChoiceField(
        queryset=Team.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Select a team to join (optional)',
        help_text='You can also join a team later from your dashboard.'
    )
    
    phone_number = forms.CharField(
        max_length=15, 
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., 0712345678'})
    )
    location = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Nairobi, Karen'})
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Date of Birth'
    )
    
    class Meta:
        model = CustomUser
        fields = (
            'username', 
            'email', 
            'first_name', 
            'last_name', 
            'user_type', 
            'team',  # ✅ Added team field
            'phone_number', 
            'location', 
            'date_of_birth', 
            'password1', 
            'password2'
        )
        labels = {
            'username': 'Username',
            'email': 'Email Address',
            'first_name': 'First Name',
            'last_name': 'Last Name',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes to all fields
        for field in self.fields:
            if field != 'user_type' and field != 'team':
                self.fields[field].widget.attrs.update({
                    'class': 'form-control'
                })
        # Special styling for radio buttons
        self.fields['user_type'].widget.attrs.update({
            'class': 'form-check-input'
        })
        # Only show team field for players
        self.fields['team'].queryset = Team.objects.filter(is_active=True)
        
        # Add JavaScript to show/hide team field based on user type
        self.fields['team'].widget.attrs.update({
            'class': 'form-control team-select',
            'data-user-type': 'player'
        })
    
    def clean_email(self):
        """Validate that email is unique"""
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = self.cleaned_data['user_type']
        if commit:
            user.save()
            # ✅ Create join request if player selected a team
            if user.user_type == 'player':
                team = self.cleaned_data.get('team')
                if team:
                    TeamJoinRequest.objects.create(
                        player=user,
                        team=team,
                        status='pending',
                        message=f"{user.get_full_name()} requested to join {team.name} during registration."
                    )
        return user


class CustomUserLoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise forms.ValidationError('Username is required.')
        return username
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not password:
            raise forms.ValidationError('Password is required.')
        return password


class UserProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile (non-admin users)"""
    
    class Meta:
        model = CustomUser
        fields = (
            'first_name', 
            'last_name', 
            'email', 
            'phone_number', 
            'location', 
            'profile_picture'
        )
        widgets = {
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field != 'profile_picture':
                self.fields[field].widget.attrs.update({
                    'class': 'form-control'
                })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email