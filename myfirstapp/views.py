from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.contrib.auth.models import User
from .models import ChatRoom, Message
from .forms import ChatRoomForm, MessageForm
import json
from .models import (
    Team, TournamentSchedule, Player, Trainer, 
    TournamentOrganiser, ChatRoom, Message, MessageAttachment,
    TeamJoinRequest, TrainingSession, TournamentApplication, PlayerFeedback
)

from .forms import (
    TournamentOrganiserRegistrationForm,
    TournamentScheduleForm,
    TrainerRegistrationForm,
    PlayerRegistrationForm,
    OrganiserProfileForm,
    ChatRoomForm,
    MessageForm,
    TeamForm,
    TrainingSessionForm,
    TournamentApplicationForm,
    PlayerFeedbackForm
)

# === HOME VIEW WITH ROLE-BASED REDIRECT ===
def home(request):
    """Redirect users to their appropriate dashboard based on role"""
    if request.user.is_authenticated:
        # Check if user is a tournament organiser
        if TournamentOrganiser.objects.filter(user=request.user).exists():
            return redirect('tournament_organiser_dashboard')
        # Check if user is a trainer
        elif Trainer.objects.filter(user=request.user).exists():
            return redirect('trainer_dashboard')
        # Check if user is a player
        elif Player.objects.filter(user=request.user).exists():
            return redirect('player_dashboard')
        else:
            # Default redirect
            return redirect('tournament_organiser_dashboard')
    
    return render(request, 'home.html')

def registration_choice(request):
    return render(request, 'registration_choice.html')


# === TOURNAMENT ORGANISER DASHBOARD ===
@login_required
def tournament_organiser_dashboard(request):
    """Dashboard for tournament organisers"""
    # Get statistics
    total_matches = TournamentSchedule.objects.count()
    total_teams = Team.objects.count()
    ongoing_matches = TournamentSchedule.objects.filter(status='ongoing').count()
    upcoming_matches = TournamentSchedule.objects.filter(status='scheduled').count()
    matches = TournamentSchedule.objects.all().order_by('-date', '-time')[:10]
    
    context = {
        'total_matches': total_matches,
        'total_teams': total_teams,
        'ongoing_matches': ongoing_matches,
        'upcoming_matches': upcoming_matches,
        'matches': matches,
    }
    return render(request, 'tournament_organiser_dashboard.html', context)

# === PLAYER DASHBOARD ===
@login_required
def player_dashboard(request):
    """Dashboard for players"""
    try:
        player = request.user.player
        my_team = player.team
        my_team_name = my_team.team_name if my_team else "No Team"
        
        # Get matches for the player's team
        if my_team:
            matches = TournamentSchedule.objects.filter(
                Q(team1=my_team) | Q(team2=my_team)
            ).order_by('date', 'time')
            
            # Upcoming matches
            upcoming_matches = matches.filter(status='scheduled')[:5]
            upcoming_matches_count = upcoming_matches.count()
            
            # Recent matches (completed)
            recent_matches = matches.filter(status='completed').order_by('-date', '-time')[:5]
            
            # Matches played count
            matches_played = matches.filter(status='completed').count()
            
            # Win rate
            wins = matches.filter(winner=my_team).count()
            win_rate = int((wins / matches_played * 100)) if matches_played > 0 else 0
        else:
            upcoming_matches = []
            upcoming_matches_count = 0
            recent_matches = []
            matches_played = 0
            win_rate = 0
        
    except Player.DoesNotExist:
        my_team_name = "No Team"
        upcoming_matches = []
        upcoming_matches_count = 0
        recent_matches = []
        matches_played = 0
        win_rate = 0
    
    context = {
        'my_team_name': my_team_name,
        'upcoming_matches': upcoming_matches,
        'upcoming_matches_count': upcoming_matches_count,
        'recent_matches': recent_matches,
        'matches_played': matches_played,
        'win_rate': win_rate,
    }
    return render(request, 'player_dashboard.html', context)

# === TRAINER DASHBOARD ===
@login_required
def trainer_dashboard(request):
    """Dashboard for trainers"""
    try:
        trainer = request.user.trainer
        my_teams = Team.objects.filter(trainer=trainer)
        teams_coaching = my_teams.count()
        
        # Total players across all teams
        total_players = 0
        for team in my_teams:
            total_players += team.current_members
        
        # Team win rate (average)
        total_wins = 0
        total_matches = 0
        for team in my_teams:
            total_wins += team.matches_won
            total_matches += team.matches_played
        team_win_rate = int((total_wins / total_matches * 100)) if total_matches > 0 else 0

        training_sessions_count = TrainingSession.objects.filter(trainer=trainer).count()
        upcoming_sessions = TrainingSession.objects.filter(
            trainer=trainer
        ).order_by('date', 'time')[:5]

        pending_requests_count = TeamJoinRequest.objects.filter(
            team__trainer=trainer,
            status='pending'
        ).count()
        
    except Trainer.DoesNotExist:
        pending_requests_count = 0
        my_teams = []
        teams_coaching = 0
        total_players = 0
        team_win_rate = 0
        training_sessions_count = 0
        upcoming_sessions = []
    
    context = {
        'pending_requests_count': pending_requests_count,
        'my_teams': my_teams,
        'teams_coaching': teams_coaching,
        'total_players': total_players,
        'team_win_rate': team_win_rate,
        'training_sessions_count': training_sessions_count,
        'upcoming_sessions': upcoming_sessions,
    }
    return render(request, 'trainer_dashboard.html', context)

# === REGISTRATION VIEWS ===
def tournament_organiser_registration(request):
    if request.method == 'POST':
        form = TournamentOrganiserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create TournamentOrganiser profile
            TournamentOrganiser.objects.create(
                user=user,
                organisation_name=form.cleaned_data.get('organisation_name', f"{user.username}'s Org"),
                phone_number=form.cleaned_data.get('phone_number', ''),
                location=form.cleaned_data.get('location', '')
            )
            auth_login(request, user)
            messages.success(request, 'Registration successful! Welcome to your dashboard.')
            return redirect('tournament_organiser_dashboard')
    else:
        form = TournamentOrganiserRegistrationForm()
    return render(request, 'tournament_organiser.html', {'form': form})


def trainer_registration(request):
    if request.method == 'POST':
        form = TrainerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the user first
            user = form.save()
            
            # Get all form data
            phone_number = form.cleaned_data.get('phone_number', '')
            location = form.cleaned_data.get('location', '')
            specialization = form.cleaned_data.get('specialization', 'General')
            experience_years = form.cleaned_data.get('experience_years', 0)
            certificate = form.cleaned_data.get('certificate', None)
            
            # Check if trainer profile already exists
            if Trainer.objects.filter(user=user).exists():
                messages.warning(request, 'You already have a trainer profile. Please login.')
                return redirect('login')
            
            # Create trainer profile with ALL data
            trainer = Trainer.objects.create(
                user=user,
                phone_number=phone_number,  # ← Make sure this is saved
                location=location,          # ← Make sure this is saved
                specialization=specialization,  # ← Make sure this is saved
                experience_years=experience_years,  # ← Make sure this is saved
                certificate=certificate     # ← Make sure this is saved
            )
            
            messages.success(request, f'Registration successful! Welcome {user.username}! Please login.')
            return redirect('login')
        else:
            # Print form errors to console for debugging
            print("Form errors:", form.errors)
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TrainerRegistrationForm()
    
    return render(request, 'trainer_registration.html', {'form': form})

def player_registration(request):
    teams = Team.objects.filter(is_approved=True)
    
    if request.method == 'POST':
        form = PlayerRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registration successful! Please login with your credentials.')
            return redirect('login')
    else:
        form = PlayerRegistrationForm()
    
    return render(request, 'player_registration.html', {
        'form': form,
        'teams': teams
    })

@login_required
def tournament_schedule(request):
    matches = TournamentSchedule.objects.all().order_by('date', 'time')
    
    if request.method == 'POST':
        form = TournamentScheduleForm(request.POST)
        if form.is_valid():
            match = form.save(commit=False)
            match.created_by = request.user
            match.save()
            messages.success(request, 'Tournament schedule created successfully!')
            return redirect('tournament_schedule')
    else:
        form = TournamentScheduleForm()
    
    teams = Team.objects.filter(is_approved=True)
    
    context = {
        'form': form,
        'matches': matches,
        'teams': teams,
    }
    return render(request, 'tournament_schedule.html', context)


@require_http_methods(["GET", "POST"])
@csrf_protect
def logout_view(request):
    auth_logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')

# === PLACEHOLDER VIEWS (Create these as needed) ===
@login_required
def organiser_details(request):
    return render(request, 'organiser_details.html')

@login_required
def manage_teams(request):
    teams = Team.objects.all()
    return render(request, 'manage_teams.html', {'teams': teams})

@login_required
def manage_matches(request):
    matches = TournamentSchedule.objects.all().order_by('date', 'time')
    return render(request, 'manage_matches.html', {'matches': matches})

@login_required
def tournament_list(request):
    return render(request, 'tournament_list.html')

@login_required
def reports(request):
    return render(request, 'reports.html')

@login_required
def profile_settings(request):
    return render(request, 'profile_settings.html')

@login_required
def player_profile(request):
    return render(request, 'player_profile.html')

@login_required
def my_team(request):
    return render(request, 'my_team.html')
@login_required
def available_teams(request):
    player = get_object_or_404(Player, user=request.user)

    teams = Team.objects.filter(
        is_approved=True,
        location__iexact=player.location
    )

    return render(request, 'available_teams.html', {
        'teams': teams,
        'player': player
    })


@login_required
def request_join_team(request, team_id):
    player = get_object_or_404(Player, user=request.user)
    team = get_object_or_404(Team, id=team_id)

    if player.team:
        messages.warning(request, 'You already belong to a team.')
        return redirect('my_team')

    existing_request = TeamJoinRequest.objects.filter(
        player=player,
        team=team
    ).first()

    if existing_request:
        messages.info(request, 'You have already requested to join this team.')
    else:
        TeamJoinRequest.objects.create(
            player=player,
            team=team
        )
        messages.success(request, f'Request sent to join {team.team_name}!')

    return redirect('available_teams')

@login_required
def my_matches(request):
    return render(request, 'my_matches.html')

@login_required
def team_standings(request):
    return render(request, 'team_standings.html')

@login_required
def player_stats(request):
    return render(request, 'player_stats.html')

@login_required
def player_settings(request):
    return render(request, 'player_settings.html')

@login_required
def trainer_profile(request):
    return render(request, 'trainer_profile.html')
@login_required
def create_team(request):
    trainer = get_object_or_404(Trainer, user=request.user)

    if request.method == 'POST':
        form = TeamForm(request.POST)

        if form.is_valid():
            team = form.save(commit=False)
            team.trainer = trainer
            team.is_approved = True
            team.save()

            messages.success(request, "Team created successfully!")

            return redirect('my_teams')
    else:
        form = TeamForm()

    return render(request, 'create_team.html', {
        'form': form
    })
@login_required
def join_requests(request):
    trainer = get_object_or_404(Trainer, user=request.user)

    requests = TeamJoinRequest.objects.filter(
        team__trainer=trainer,
        status='pending'
    ).order_by('-requested_at')

    return render(request, 'join_requests.html', {
        'requests': requests
    })


@login_required
def accept_join_request(request, request_id):
    join_request = get_object_or_404(
        TeamJoinRequest,
        id=request_id,
        team__trainer__user=request.user
    )

    join_request.accept()
    messages.success(request, 'Player request accepted successfully!')
    return redirect('join_requests')


@login_required
def decline_join_request(request, request_id):
    join_request = get_object_or_404(
        TeamJoinRequest,
        id=request_id,
        team__trainer__user=request.user
    )

    join_request.decline()
    messages.success(request, 'Player request declined.')
    return redirect('join_requests')



@login_required
def my_teams(request):
    trainer = get_object_or_404(Trainer, user=request.user)
    teams = Team.objects.filter(trainer=trainer)

    return render(request, 'my_teams.html', {
        'teams': teams
    })

@login_required
def trainer_schedule(request):
    return render(request, 'trainer_schedule.html')

@login_required
def team_performance(request):
    return render(request, 'team_performance.html')

@login_required
def player_development(request):
    return render(request, 'player_development.html')

@login_required
def training_sessions(request):
    trainer = get_object_or_404(Trainer, user=request.user)
    sessions = TrainingSession.objects.filter(trainer=trainer).order_by('date', 'time')

    return render(request, 'training_sessions.html', {
        'sessions': sessions
    })

@login_required
def create_training_session(request):
    trainer = get_object_or_404(Trainer, user=request.user)

    if request.method == 'POST':
        form = TrainingSessionForm(request.POST)
        form.fields['team'].queryset = Team.objects.filter(trainer=trainer)

        if form.is_valid():
            session = form.save(commit=False)
            session.trainer = trainer
            session.save()
            messages.success(request, 'Training session created successfully!')
            return redirect('training_sessions')
    else:
        form = TrainingSessionForm()
        form.fields['team'].queryset = Team.objects.filter(trainer=trainer)

    return render(request, 'create_training_session.html', {
        'form': form
    })
@login_required
def apply_tournament(request):
    trainer = get_object_or_404(Trainer, user=request.user)

    if request.method == 'POST':
        form = TournamentApplicationForm(request.POST)
        form.fields['team'].queryset = Team.objects.filter(trainer=trainer)

        if form.is_valid():
            application = form.save(commit=False)
            application.trainer = trainer
            application.save()

            messages.success(request, 'Tournament application submitted successfully!')
            return redirect('tournament_applications')
    else:
        form = TournamentApplicationForm()
        form.fields['team'].queryset = Team.objects.filter(trainer=trainer)

    return render(request, 'apply_tournament.html', {
        'form': form
    })


@login_required
def tournament_applications(request):
    trainer = get_object_or_404(Trainer, user=request.user)
    applications = TournamentApplication.objects.filter(trainer=trainer).order_by('-applied_at')

    return render(request, 'tournament_applications.html', {
        'applications': applications
    })


@login_required
def trainer_settings(request):
    return render(request, 'trainer_settings.html')

# === EDIT, DELETE, DETAIL VIEWS ===
@login_required
def edit_match(request, match_id):
    match = get_object_or_404(TournamentSchedule, id=match_id)
    
    if match.created_by and match.created_by != request.user:
        messages.error(request, "You don't have permission to edit this match!")
        return redirect('tournament_schedule')
    
    if request.method == 'POST':
        form = TournamentScheduleForm(request.POST, instance=match)
        
        if form.is_valid():
            updated_match = form.save()
            messages.success(request, f"Match '{updated_match.name}' updated successfully!")
            return redirect('tournament_schedule')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TournamentScheduleForm(instance=match)

    teams = Team.objects.filter(is_approved=True)
    
    context = {
        'form': form,
        'match': match,
        'teams': teams,
        'is_editing': True,
    }
    return render(request, 'edit_match.html', context)

@login_required
def delete_match(request, match_id):
    match = get_object_or_404(TournamentSchedule, id=match_id)
    
    if match.created_by and match.created_by != request.user:
        messages.error(request, "You don't have permission to delete this match!")
        return redirect('tournament_schedule')
    
    if request.method == 'POST':
        match_name = match.name
        match.delete()
        messages.success(request, f"Match '{match_name}' deleted successfully!")
        return redirect('tournament_schedule')
    
    return render(request, 'confirm_delete.html', {'match': match})

@login_required
def match_detail(request, match_id):
    match = get_object_or_404(TournamentSchedule, id=match_id)
    return render(request, 'match_detail.html', {'match': match})

@login_required
def organiser_details(request):
    try:
        # Get the organiser profile for the current user
        organiser = TournamentOrganiser.objects.get(user=request.user)
    except TournamentOrganiser.DoesNotExist:
        # If profile doesn't exist, create one
        organiser = TournamentOrganiser.objects.create(
            user=request.user,
            organisation_name=f"{request.user.username}'s Organisation",
            phone_number='',
            location=''
        )
        messages.info(request, 'Your organiser profile has been created. Please complete your details.')
    
    if request.method == 'POST':
        form = OrganiserProfileForm(request.POST, instance=organiser)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your details have been updated successfully!')
            return redirect('organiser_details')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = OrganiserProfileForm(instance=organiser)
    
    total_matches = TournamentSchedule.objects.count()
    total_teams = Team.objects.count()
    upcoming_matches = TournamentSchedule.objects.filter(status='scheduled').count()
    
    context = {
        'form': form,
        'organiser': organiser,
        'total_matches': total_matches,
        'total_teams': total_teams,
        'upcoming_matches': upcoming_matches,
    }
    return render(request, 'organiser_details.html', context)


@login_required
def chat_list(request):
    """View all chat rooms for the current user"""
    chat_rooms = request.user.chat_rooms.filter(is_active=True).order_by('-updated_at')
    
    # Separate team chats and individual chats
    team_chats = []
    individual_chats = []
    
    for room in chat_rooms:
        room.unread = room.unread_count(request.user)
        
        if room.name and room.name.startswith('Team '):
            team_chats.append(room)
        else:
            individual_chats.append(room)
    
    context = {
        'chat_rooms': chat_rooms,
        'team_chats': team_chats,
        'individual_chats': individual_chats,
    }
    return render(request, 'chat_list.html', context)

@login_required
def chat_room(request, room_id):
    """View a specific chat room"""
    room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
    
    # Get all messages for this room
    messages_list = room.messages.all().order_by('sent_at')
    
    # Mark messages as read
    unread_messages = room.messages.filter(is_read=False).exclude(sender=request.user)
    for msg in unread_messages:
        msg.mark_as_read()
    
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.room = room
            message.sender = request.user
            message.save()
            
            # Update room's updated_at
            room.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': {
                        'id': message.id,
                        'sender': message.sender.username,
                        'content': message.content,
                        'sent_at': message.sent_at.strftime('%H:%M'),
                        'sent_at_full': message.sent_at.strftime('%Y-%m-%d %H:%M'),
                    }
                })
            return redirect('chat_room', room_id=room.id)
    else:
        form = MessageForm()
    
    # Get participants excluding current user for individual chats
    other_participants = room.participants.exclude(id=request.user.id)
    
    context = {
        'room': room,
        'messages': messages_list,
        'form': form,
        'other_participants': other_participants,
    }
    return render(request, 'chat_room.html', context)

@login_required
def start_chat(request):
    # Get user's teams (if they are a player)
    my_teams = []
    if hasattr(request.user, 'player'):
        if request.user.player.team:
            my_teams = [request.user.player.team]
    elif hasattr(request.user, 'trainer'):
        # If trainer, get all teams they coach
        my_teams = Team.objects.filter(trainer=request.user.trainer)
    
    if request.method == 'POST':
        room_type = request.POST.get('room_type', 'individual')
        
        # Handle Team Chat
        if room_type == 'team':
            team_id = request.POST.get('team_id')
            if not team_id:
                messages.error(request, 'Please select a team.')
                return redirect('start_chat')
            
            try:
                team = Team.objects.get(id=team_id)
                # Get all players in the team
                players = Player.objects.filter(team=team)
                users = [player.user for player in players if player.user != request.user]
                
                if not users:
                    messages.error(request, 'No other players in this team.')
                    return redirect('start_chat')
                
                # Check if a team chat already exists
                existing_room = ChatRoom.objects.filter(
                    room_type='group',
                    name=f"Team {team.team_name} Chat"
                ).filter(participants=request.user)
                
                for room in existing_room:
                    # Check if all team members are in this room
                    room_users = room.participants.all()
                    team_users = [player.user for player in Player.objects.filter(team=team)]
                    if set(room_users) == set(team_users):
                        return redirect('chat_room', room_id=room.id)
                
                # Create new team chat room
                room = ChatRoom.objects.create(
                    name=f"Team {team.team_name} Chat",
                    room_type='group',
                    created_by=request.user
                )
                
                # Add all team members
                room.participants.add(request.user)
                for user in users:
                    room.participants.add(user)
                
                room.save()
                messages.success(request, f'Team chat for "{team.team_name}" created successfully!')
                return redirect('chat_room', room_id=room.id)
                
            except Team.DoesNotExist:
                messages.error(request, 'Team not found.')
                return redirect('start_chat')
        
        # Handle Individual Chat
        elif room_type == 'individual':
            user_ids = request.POST.getlist('participants')
            if not user_ids:
                messages.error(request, 'Please select at least one participant.')
                return redirect('start_chat')
            
            # Get the users (excluding current user)
            users = User.objects.filter(id__in=user_ids).exclude(id=request.user.id)
            
            if not users.exists():
                messages.error(request, 'Please select at least one participant.')
                return redirect('start_chat')
            
            # For individual chat, only take the first user
            user = users.first()
            
            # Check if individual chat already exists
            existing_room = ChatRoom.objects.filter(
                room_type='individual',
                participants=request.user
            ).filter(participants=user)
            
            if existing_room.exists():
                return redirect('chat_room', room_id=existing_room.first().id)
            
            # Create new individual chat
            room = ChatRoom.objects.create(
                room_type='individual',
                created_by=request.user
            )
            room.participants.add(request.user)
            room.participants.add(user)
            room.save()
            
            messages.success(request, 'Individual chat created successfully!')
            return redirect('chat_room', room_id=room.id)
        
        # Handle Group Chat
        else:
            user_ids = request.POST.getlist('participants')
            if not user_ids:
                messages.error(request, 'Please select at least one participant.')
                return redirect('start_chat')
            
            users = User.objects.filter(id__in=user_ids).exclude(id=request.user.id)
            
            if not users.exists():
                messages.error(request, 'Please select at least one participant.')
                return redirect('start_chat')
            
            name = request.POST.get('name', 'Group Chat')
            
            # Check if group chat already exists with same name and members
            existing_room = ChatRoom.objects.filter(
                room_type='group',
                name=name
            )
            
            for room in existing_room:
                room_users = set(room.participants.all())
                new_users = set(list(users) + [request.user])
                if room_users == new_users:
                    return redirect('chat_room', room_id=room.id)
            
            # Create new group chat
            room = ChatRoom.objects.create(
                name=name,
                room_type='group',
                created_by=request.user
            )
            room.participants.add(request.user)
            for user in users:
                room.participants.add(user)
            room.save()
            
            messages.success(request, 'Group chat created successfully!')
            return redirect('chat_room', room_id=room.id)
    
    # GET request - show form
    users = User.objects.exclude(id=request.user.id)
    
    context = {
        'users': users,
        'my_teams': my_teams,
    }
    return render(request, 'start_chat.html', context)

@login_required
def get_new_messages(request, room_id):
    """AJAX endpoint to get new messages for a room"""
    room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
    last_message_id = request.GET.get('last_id', 0)
    
    new_messages = room.messages.filter(id__gt=last_message_id).order_by('sent_at')
    
    messages_data = []
    for msg in new_messages:
        messages_data.append({
            'id': msg.id,
            'sender': msg.sender.username,
            'content': msg.content,
            'sent_at': msg.sent_at.strftime('%H:%M'),
            'sent_at_full': msg.sent_at.strftime('%Y-%m-%d %H:%M'),
            'is_own': msg.sender == request.user,
        })
    
    # Mark messages as read
    unread_messages = room.messages.filter(is_read=False).exclude(sender=request.user)
    for msg in unread_messages:
        msg.mark_as_read()
    
    return JsonResponse({
        'success': True,
        'messages': messages_data,
    })

@login_required
def get_unread_counts(request):
    """AJAX endpoint to get unread message counts"""
    rooms = request.user.chat_rooms.filter(is_active=True)
    unread_data = {}
    
    for room in rooms:
        count = room.unread_count(request.user)
        if count > 0:
            unread_data[room.id] = count
    
    return JsonResponse({
        'success': True,
        'unread_counts': unread_data,
    })

@login_required
def delete_room(request, room_id):
    """Delete/Leave a chat room"""
    room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
    
    if request.method == 'POST':
        room.is_active = False
        room.save()
        messages.success(request, 'Chat room deleted successfully.')
        return redirect('chat_list')
    
    return render(request, 'confirm_delete_room.html', {'room': room})

@login_required
def add_participants(request, room_id):
    """Add participants to a group chat"""
    room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
    
    if room.room_type != 'group':
        messages.error(request, 'You can only add participants to group chats.')
        return redirect('chat_room', room_id=room.id)
    
    if request.method == 'POST':
        user_ids = request.POST.getlist('participants')
        users = User.objects.filter(id__in=user_ids)
        
        for user in users:
            if user not in room.participants.all():
                room.participants.add(user)
        
        messages.success(request, f'{len(users)} participant(s) added successfully.')
        return redirect('chat_room', room_id=room.id)
    
    # Show form to add participants
    available_users = User.objects.exclude(
        id__in=room.participants.all().values_list('id', flat=True)
    ).exclude(id=request.user.id)
    
    context = {
        'room': room,
        'available_users': available_users,
    }
    return render(request, 'add_participants.html', context)

@login_required
def send_player_feedback(request):
    trainer = get_object_or_404(Trainer, user=request.user)
    teams = Team.objects.filter(trainer=trainer)
    players = Player.objects.filter(team__in=teams)

    if request.method == 'POST':
        form = PlayerFeedbackForm(request.POST)
        form.fields['team'].queryset = teams
        form.fields['player'].queryset = players

        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.trainer = trainer
            feedback.save()

            messages.success(request, 'Feedback sent successfully!')
            return redirect('player_feedback_list')
    else:
        form = PlayerFeedbackForm()
        form.fields['team'].queryset = teams
        form.fields['player'].queryset = players

    return render(request, 'send_player_feedback.html', {'form': form})


@login_required
def player_feedback_list(request):
    trainer = get_object_or_404(Trainer, user=request.user)
    feedbacks = PlayerFeedback.objects.filter(trainer=trainer)

    return render(request, 'player_feedback_list.html', {
        'feedbacks': feedbacks
    })