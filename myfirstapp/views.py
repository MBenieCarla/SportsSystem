from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import User
from django.utils import timezone  
from .models import (
    Team, TournamentSchedule, Player, Trainer, 
    TournamentOrganiser, ChatRoom, Message, MessageAttachment,
    TeamJoinRequest, TrainingSession, TournamentApplication, PlayerFeedback,
    Tournament, Feedback, TournamentMatch
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
    PlayerFeedbackForm,
    TournamentForm,
    FeedbackForm,
    BaseUserRegistrationForm
)
from django.db.models import Avg, Count

# === HOME VIEW WITH ROLE-BASED REDIRECT ===
def home(request):
    """Landing page - only for non-logged-in users"""
    
    # If user is already logged in, redirect to dashboard
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
    
    # Show landing page for non-authenticated users
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
    
    context = {
        'my_team_name': my_team_name,
        'upcoming_matches': upcoming_matches,
        'upcoming_matches_count': upcoming_matches_count,
        'recent_matches': recent_matches,
        'matches_played': matches_played,
        'win_rate': win_rate,
    }
    return render(request, 'player_dashboard.html', context)


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
                phone_number=phone_number,
                location=location,
                specialization=specialization,
                experience_years=experience_years,
                certificate=certificate
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


def tournament_organiser_registration(request):
    """Registration view for tournament organisers"""
    if request.method == 'POST':
        form = BaseUserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create TournamentOrganiser profile with default organisation name
            TournamentOrganiser.objects.create(
                user=user,
                organisation_name=f"{user.username}'s Organisation",
                phone_number=form.cleaned_data['phone_number'],
                location=form.cleaned_data['location']
            )
            auth_login(request, user)
            messages.success(request, 'Registration successful! Welcome to your dashboard.')
            return redirect('tournament_organiser_dashboard')
    else:
        form = BaseUserRegistrationForm()
    
    return render(request, 'tournament_organiser_registration.html', {'form': form})

@login_required
def tournament_schedule(request):
    """View for tournament schedule - different views for organisers and trainers"""
    
    # Check if user is a tournament organiser
    is_organiser = TournamentOrganiser.objects.filter(user=request.user).exists()
    
    # Get filter status from request
    filter_status = request.GET.get('status')
    show_form = request.GET.get('add') == 'true'  # Check if we should show the form
    
    # Base queryset
    matches = TournamentSchedule.objects.all().order_by('date', 'time')
    
    # If user is a trainer, show only matches involving their teams
    if not is_organiser and hasattr(request.user, 'trainer'):
        trainer = request.user.trainer
        trainer_teams = Team.objects.filter(trainer=trainer)
        matches = matches.filter(
            Q(team1__in=trainer_teams) | Q(team2__in=trainer_teams)
        )
    
    # Apply status filter
    if filter_status:
        matches = matches.filter(status=filter_status)
    
    # Handle match creation (organisers only)
    if request.method == 'POST' and is_organiser:
        form = TournamentScheduleForm(request.POST)
        if form.is_valid():
            match = form.save(commit=False)
            match.created_by = request.user
            match.save()
            messages.success(request, 'Tournament match created successfully!')
            return redirect('tournament_schedule')
    else:
        form = TournamentScheduleForm() if is_organiser else None
    
    teams = Team.objects.filter(is_approved=True)
    
    context = {
        'matches': matches,
        'teams': teams,
        'form': form,
        'is_organiser': is_organiser,
        'filter_status': filter_status,
        'is_trainer': hasattr(request.user, 'trainer'),
        'show_form': show_form,
    }
    return render(request, 'tournament_schedule.html', context)


@require_http_methods(["GET", "POST"])
@csrf_protect
def logout_view(request):
    auth_logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')

# === PLACEHOLDER VIEWS ===
@login_required
def organiser_details(request):
    # Get the organiser profile for the current user
    organiser = TournamentOrganiser.objects.get(user=request.user)
    
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
def trainer_dashboard(request):
    """Dashboard for trainers"""
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
    
    # Training sessions
    training_sessions_count = TrainingSession.objects.filter(trainer=trainer).count()
    upcoming_sessions = TrainingSession.objects.filter(
        trainer=trainer
    ).order_by('date', 'time')[:5]
    
    # Pending join requests
    pending_requests_count = TeamJoinRequest.objects.filter(
        team__trainer=trainer,
        status='pending'
    ).count()
    
    # Feedback count
    feedback_count = Feedback.objects.filter(trainer=request.user).count()
    
    context = {
        'my_teams': my_teams,
        'teams_coaching': teams_coaching,
        'total_players': total_players,
        'team_win_rate': team_win_rate,
        'training_sessions_count': training_sessions_count,
        'upcoming_sessions': upcoming_sessions,
        'pending_requests_count': pending_requests_count,
        'feedback_count': feedback_count,
    }
    return render(request, 'trainer_dashboard.html', context)

@login_required
def manage_teams(request):
    teams = Team.objects.all()
    return render(request, 'manage_teams.html', {'teams': teams})

@login_required
def manage_matches(request):
    matches = TournamentSchedule.objects.all().order_by('date', 'time')
    return render(request, 'manage_matches.html', {'matches': matches})

# === TOURNAMENT VIEWS FOR TRAINERS ===


@login_required
def tournament_detail(request, tournament_id):
    """View tournament details including timetable"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Check if trainer's team has applied
    has_applied = False
    application_status = None
    trainer_teams = []
    
    if hasattr(request.user, 'trainer'):
        trainer = request.user.trainer
        trainer_teams = Team.objects.filter(trainer=trainer)
        
        application = TournamentApplication.objects.filter(
            tournament=tournament,
            team__in=trainer_teams
        ).first()
        
        if application:
            has_applied = True
            application_status = application.status
    
    # Get matches/timetable
    matches = tournament.matches.all().order_by('date', 'time')
    
    context = {
        'tournament': tournament,
        'matches': matches,
        'has_applied': has_applied,
        'application_status': application_status,
        'trainer_teams': trainer_teams,
    }
    return render(request, 'tournament_detail.html', context)

@login_required
def tournament_timetable(request, tournament_id):
    """View only the tournament timetable/schedule"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    matches = tournament.matches.all().order_by('date', 'time')
    
    context = {
        'tournament': tournament,
        'matches': matches,
    }
    return render(request, 'tournament_timetable.html', context)

@login_required
def apply_to_tournament(request, tournament_id):
    """Apply to a tournament as a trainer"""
    try:
        trainer = get_object_or_404(Trainer, user=request.user)
        tournament = get_object_or_404(Tournament, id=tournament_id)
        
        # Check if tournament is open
        if tournament.status != 'open':
            messages.error(request, "This tournament is no longer accepting applications.")
            return redirect('tournament_list')
        
        # Check if tournament is full
        if tournament.is_full:
            messages.error(request, "This tournament is full. No more spots available.")
            return redirect('tournament_list')
        
        # Get trainer's teams
        trainer_teams = Team.objects.filter(trainer=trainer)
        if not trainer_teams.exists():
            messages.warning(request, "You need to create a team first.")
            return redirect('my_teams')
        
        if request.method == 'POST':
            team_id = request.POST.get('team')
            reason = request.POST.get('reason')
            
            if not team_id:
                messages.error(request, "Please select a team.")
                return redirect('apply_to_tournament', tournament_id=tournament_id)
            
            team = get_object_or_404(Team, id=team_id, trainer=trainer)
            
            # Check if team already applied
            existing_application = TournamentApplication.objects.filter(
                tournament=tournament,
                team=team
            ).first()
            
            if existing_application:
                messages.warning(request, f"{team.team_name} has already applied to this tournament.")
                return redirect('tournament_list')
            
            # Create application
            application = TournamentApplication.objects.create(
                tournament=tournament,
                team=team,
                trainer=trainer,
                reason=reason,
                status='pending'
            )
            
            messages.success(request, f"{team.team_name} has applied to {tournament.name}!")
            return redirect('tournament_detail', tournament_id=tournament_id)
        
        context = {
            'tournament': tournament,
            'teams': trainer_teams,
        }
        return render(request, 'apply_to_tournament.html', context)
        
    except Trainer.DoesNotExist:
        messages.warning(request, 'Trainer profile not found.')
        return redirect('trainer_dashboard')

@login_required
def cancel_application(request, application_id):
    """Cancel a tournament application"""
    application = get_object_or_404(
        TournamentApplication, 
        id=application_id,
        trainer__user=request.user,
        status='pending'
    )
    
    if request.method == 'POST':
        application.delete()
        messages.success(request, "Application cancelled successfully.")
        return redirect('tournament_list')
    
    context = {
        'application': application,
    }
    return render(request, 'cancel_application.html', context)

# === TOURNAMENT MANAGEMENT VIEWS (Organiser Only) ===

@login_required
def manage_tournaments(request):
    """Manage all tournaments (Organiser only)"""
    if not TournamentOrganiser.objects.filter(user=request.user).exists():
        messages.error(request, "You don't have permission to manage tournaments.")
        return redirect('tournament_organiser_dashboard')
    
    tournaments = Tournament.objects.filter(created_by=request.user).order_by('-created_at')
    
    context = {
        'tournaments': tournaments,
    }
    return render(request, 'manage_tournaments.html', context)

@login_required
def create_tournament(request):
    """Create a new tournament (Organiser only)"""
    if not TournamentOrganiser.objects.filter(user=request.user).exists():
        messages.error(request, "You don't have permission to create tournaments.")
        return redirect('tournament_organiser_dashboard')
    
    if request.method == 'POST':
        form = TournamentForm(request.POST)
        if form.is_valid():
            tournament = form.save(commit=False)
            tournament.created_by = request.user
            tournament.save()
            messages.success(request, f'Tournament "{tournament.name}" created successfully!')
            return redirect('manage_tournaments')
    else:
        form = TournamentForm()
    
    context = {
        'form': form,
    }
    return render(request, 'create_tournament.html', context)

@login_required
def create_tournament_schedule(request, tournament_id):
    """Create match schedule for a tournament (Organiser only)"""
    if not TournamentOrganiser.objects.filter(user=request.user).exists():
        messages.error(request, "You don't have permission.")
        return redirect('tournament_organiser_dashboard')
    
    tournament = get_object_or_404(Tournament, id=tournament_id, created_by=request.user)
    
    # Get approved teams
    approved_applications = tournament.applications.filter(status='approved')
    approved_teams = [app.team for app in approved_applications]
    
    if len(approved_teams) < 2:
        messages.warning(request, "Need at least 2 approved teams to create a schedule.")
        return redirect('tournament_detail', tournament_id=tournament_id)
    
    if request.method == 'POST':
        # Create matches for each team pairing
        match_number = 1
        for i in range(len(approved_teams)):
            for j in range(i+1, len(approved_teams)):
                match = TournamentMatch.objects.create(
                    tournament=tournament,
                    team1=approved_teams[i],
                    team2=approved_teams[j],
                    match_number=match_number,
                    date=request.POST.get(f'date_{match_number}'),
                    time=request.POST.get(f'time_{match_number}'),
                    location=request.POST.get('location'),
                    status='scheduled'
                )
                match_number += 1
        
        messages.success(request, f"Schedule created with {match_number-1} matches!")
        return redirect('tournament_detail', tournament_id=tournament_id)
    
    context = {
        'tournament': tournament,
        'approved_teams': approved_teams,
        'total_matches': len(approved_teams) * (len(approved_teams) - 1) // 2,
    }
    return render(request, 'create_tournament_schedule.html', context)

@login_required
def review_application(request, application_id):
    """Review and approve/decline tournament application (Organiser only)"""
    # Check if user is a tournament organiser
    if not TournamentOrganiser.objects.filter(user=request.user).exists():
        messages.error(request, "You don't have permission to review applications.")
        return redirect('tournament_organiser_dashboard')
    
    application = get_object_or_404(TournamentApplication, id=application_id)
    
    # Check if the tournament belongs to this organiser
    if application.tournament.created_by != request.user:
        messages.error(request, "You don't have permission to review this application.")
        return redirect('tournament_organiser_dashboard')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('review_notes', '')
        
        if action == 'approve':
            application.approve()
            messages.success(request, f"Application from {application.team.team_name} approved!")
        elif action == 'decline':
            application.decline(notes)
            messages.success(request, f"Application from {application.team.team_name} declined.")
        else:
            messages.error(request, "Invalid action.")
        
        return redirect('tournament_detail', tournament_id=application.tournament.id)
    
    context = {
        'application': application,
    }
    return render(request, 'review_application.html', context)

# === PLAYER VIEWS ===
@login_required
def profile_settings(request):
    return render(request, 'profile_settings.html')

@login_required
def player_profile(request):
    """View player profile with team and match information"""
    player = request.user.player
    my_team = player.team
    
    # Get recent matches if player has a team
    recent_matches = []
    upcoming_matches = []
    
    if my_team:
        recent_matches = TournamentSchedule.objects.filter(
            Q(team1=my_team) | Q(team2=my_team),
            status='completed'
        ).order_by('-date')[:5]
        
        upcoming_matches = TournamentSchedule.objects.filter(
            Q(team1=my_team) | Q(team2=my_team),
            status='scheduled'
        ).order_by('date')[:5]
    
    context = {
        'player': player,
        'recent_matches': recent_matches,
        'upcoming_matches': upcoming_matches,
    }
    return render(request, 'player_profile.html', context)

@login_required
def my_team(request):
    """View player's team details"""
    player = request.user.player
    team = player.team
    
    if team:
        # Get team members
        players = team.players.all()
        
        # Get recent matches
        recent_matches = TournamentSchedule.objects.filter(
            Q(team1=team) | Q(team2=team),
            status='completed'
        ).order_by('-date')[:5]
        
        # Get upcoming matches
        upcoming_matches = TournamentSchedule.objects.filter(
            Q(team1=team) | Q(team2=team),
            status='scheduled'
        ).order_by('date')[:5]
        
        context = {
            'team': team,
            'players': players,
            'recent_matches': recent_matches,
            'upcoming_matches': upcoming_matches,
        }
    else:
        context = {
            'team': None,
            'players': [],
            'recent_matches': [],
            'upcoming_matches': [],
        }
    
    return render(request, 'my_team.html', context)

@login_required
def my_matches(request):
    """View matches for the player's team"""
    # Check if user is a player
    if hasattr(request.user, 'player'):
        player = request.user.player
        my_team = player.team
        
        if my_team:
            # Get all matches where the player's team is participating
            all_matches = TournamentSchedule.objects.filter(
                Q(team1=my_team) | Q(team2=my_team)
            ).order_by('date', 'time')
            
            # Separate upcoming and past matches
            upcoming_matches = all_matches.filter(
                status__in=['scheduled', 'ongoing']
            ).order_by('date', 'time')
            
            past_matches = all_matches.filter(
                status='completed'
            ).order_by('-date', '-time')
            
            # Calculate statistics
            total_matches = past_matches.count()
            wins = past_matches.filter(winner=my_team).count()
            losses = past_matches.exclude(winner=my_team).exclude(winner=None).count()
            draws = past_matches.filter(winner=None).count()
            
            context = {
                'my_team': my_team,
                'all_matches': all_matches,
                'upcoming_matches': upcoming_matches,
                'past_matches': past_matches,
                'total_matches': total_matches,
                'wins': wins,
                'losses': losses,
                'draws': draws,
                'has_team': True,
            }
        else:
            context = {
                'my_team': None,
                'all_matches': [],
                'upcoming_matches': [],
                'past_matches': [],
                'total_matches': 0,
                'wins': 0,
                'losses': 0,
                'draws': 0,
                'has_team': False,
                'no_team_message': 'You are not in a team yet. Join a team to see your matches!'
            }
    else:
        # For non-players, redirect to tournament_list
        return redirect('tournament_list')
        
    return render(request, 'my_matches.html', context)

@login_required
def available_teams(request):
    """View available teams for players to join"""
    player = get_object_or_404(Player, user=request.user)
    
    # Get all approved teams
    teams = Team.objects.filter(is_approved=True)
    
    # If player has a location, filter by it (case-insensitive, partial match)
    if player.location:
        # Clean the location string
        player_location = player.location.strip()
        
        # Try to find teams with matching location
        teams = teams.filter(location__icontains=player_location)
        
        # If no teams found, show all teams with a message
        if not teams.exists():
            messages.info(request, f'No teams found matching "{player_location}". Showing all available teams.')
            teams = Team.objects.filter(is_approved=True)
    else:
        # If player has no location, show all teams with a warning
        messages.warning(request, 'Please update your profile with your location to find nearby teams.')
        teams = Team.objects.filter(is_approved=True)
    
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
def team_standings(request):
    return render(request, 'team_standings.html')

@login_required
def player_stats(request):
    return render(request, 'player_stats.html')

@login_required
def player_settings(request):
    return render(request, 'player_settings.html')

# === TRAINER VIEWS ===
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
            team.is_approved = True  # Auto-approve for now
            team.save()
            
            messages.success(request, "Team created successfully!")
            return redirect('my_teams')
    else:
        form = TeamForm()
    
    return render(request, 'create_team.html', {
        'form': form
    })

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
    """View for trainers to see team performance"""
    try:
        trainer = get_object_or_404(Trainer, user=request.user)
        teams = Team.objects.filter(trainer=trainer)
        
        # Calculate overall stats
        total_players = sum(team.current_members for team in teams)
        total_matches = sum(team.matches_played for team in teams)
        
        # Calculate overall win rate
        total_wins = sum(team.matches_won for team in teams)
        overall_win_rate = (total_wins / total_matches * 100) if total_matches > 0 else 0
        
        # Get recent matches for all teams
        recent_matches = TournamentSchedule.objects.filter(
            Q(team1__in=teams) | Q(team2__in=teams)
        ).order_by('-date')[:10]
        
        # Add recent matches to each team
        for team in teams:
            # Get recent matches for this team
            team.recent_matches = TournamentSchedule.objects.filter(
                Q(team1=team) | Q(team2=team)
            ).order_by('-date')[:5]
            
            # Add result to each match for form display
            for match in team.recent_matches:
                if match.status == 'completed':
                    if match.winner == team:
                        match.result = 'Win'
                    elif match.winner and match.winner != team:
                        match.result = 'Loss'
                    else:
                        match.result = 'Draw'
                else:
                    match.result = None
        
        context = {
            'teams': teams,
            'total_players': total_players,
            'total_matches': total_matches,
            'overall_win_rate': overall_win_rate,
            'recent_matches': recent_matches,
        }
        return render(request, 'team_performance.html', context)
        
    except Trainer.DoesNotExist:
        messages.warning(request, 'Trainer profile not found.')
        return redirect('trainer_dashboard')
    
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
    
    messages.success(request, f'{join_request.player.full_name} has been added to {join_request.team.team_name}!')
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
def team_detail(request, team_id):
    """View detailed information about a specific team"""
    team = get_object_or_404(Team, id=team_id, trainer__user=request.user)
    
    # Get team players
    players = Player.objects.filter(team=team)
    
    # Get matches
    matches = TournamentSchedule.objects.filter(
        Q(team1=team) | Q(team2=team)
    ).order_by('-date')
    
    upcoming_matches = matches.filter(status='scheduled')
    past_matches = matches.filter(status='completed')
    
    # Get training sessions
    training_sessions = TrainingSession.objects.filter(team=team).order_by('date', 'time')
    
    context = {
        'team': team,
        'players': players,
        'matches': matches,
        'upcoming_matches': upcoming_matches,
        'past_matches': past_matches,
        'training_sessions': training_sessions,
    }
    return render(request, 'team_detail.html', context)

# === TRAINING SESSION VIEWS ===
@login_required
def training_sessions(request):
    """View all training sessions for the trainer"""
    trainer = get_object_or_404(Trainer, user=request.user)
    sessions = TrainingSession.objects.filter(trainer=trainer).order_by('date', 'time')
    
    status_counts = {
        'pending': sessions.filter(status='pending').count(),
        'in_progress': sessions.filter(status='in_progress').count(),
        'completed': sessions.filter(status='completed').count(),
        'cancelled': sessions.filter(status='cancelled').count(),
    }
    
    context = {
        'sessions': sessions,
        'status_counts': status_counts,
    }
    return render(request, 'training_sessions.html', context)

@login_required
def create_training_session(request):
    """Create a new training session"""
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
def update_session_status(request, session_id):
    """Update the status of a training session"""
    session = get_object_or_404(
        TrainingSession, 
        id=session_id, 
        trainer__user=request.user
    )
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['pending', 'in_progress', 'completed', 'cancelled']:
            session.status = new_status
            if new_status == 'completed':
                session.completed_at = timezone.now()
            session.save()
            messages.success(request, f'Session status updated to "{session.get_status_display()}"')
        else:
            messages.error(request, 'Invalid status selected.')
    
    return redirect('training_sessions')

# === FEEDBACK VIEWS ===
@login_required
def player_development(request):
    """Combined view for player development - create feedback and view history"""
    trainer = get_object_or_404(Trainer, user=request.user)
    teams = Team.objects.filter(trainer=trainer)
    trainer_players = Player.objects.filter(team__in=teams)
    
    # Get all feedback sent by this trainer
    feedback_list = Feedback.objects.filter(
        trainer=request.user
    ).select_related('player', 'player__user').order_by('-created_at')
    
    # Statistics
    total_feedback = feedback_list.count()
    average_rating = feedback_list.aggregate(Avg('rating'))['rating__avg']
    
    # Feedback type distribution
    feedback_types = feedback_list.values('feedback_type').annotate(count=Count('id'))
    # Add display names
    for item in feedback_types:
        item['get_feedback_type_display'] = dict(Feedback.FEEDBACK_TYPES).get(item['feedback_type'], item['feedback_type'])
    
    # Handle form submission
    if request.method == 'POST':
        form = FeedbackForm(trainer, request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.trainer = request.user
            feedback.save()
            messages.success(request, f"Feedback sent successfully to {feedback.player.user.get_full_name()}!")
            return redirect('player_development')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FeedbackForm(trainer)
    
    context = {
        'form': form,
        'feedback_list': feedback_list,
        'total_feedback': total_feedback,
        'average_rating': average_rating,
        'total_players': trainer_players.count(),
        'teams': teams,
        'players': trainer_players,
        'feedback_types': feedback_types,
    }
    return render(request, 'player_development.html', context)

@login_required
def player_feedback_list(request):
    """View for trainers to see all feedback they've sent"""
    feedback_list = Feedback.objects.filter(
        trainer=request.user
    ).select_related('player', 'player__user')  # This is correct
    
    total_feedback = feedback_list.count()
    average_rating = feedback_list.aggregate(Avg('rating'))['rating__avg']
    unread_count = feedback_list.filter(is_read=False).count()
    
    context = {
        'feedback_list': feedback_list,
        'total_feedback': total_feedback,
        'average_rating': average_rating,
        'unread_count': unread_count,
        'feedback_types': feedback_list.values('feedback_type').annotate(count=Count('id')),
    }
    return render(request, 'trainer_feedback_list.html', context)


@login_required
def player_feedback_detail(request, feedback_id):
    """View for players to see feedback details (marks as read)"""
    try:
        player = request.user.player
        feedback = get_object_or_404(
            Feedback, 
            id=feedback_id, 
            player=player
        )
        
        # Mark as read when player views it
        if not feedback.is_read:
            feedback.is_read = True
            feedback.save()
        
        context = {
            'feedback': feedback,
        }
        # Change from 'feedback/feedback_detail.html' to 'feedback_detail.html'
        return render(request, 'feedback_detail.html', context)
        
    except Player.DoesNotExist:
        messages.error(request, "You don't have a player profile.")
        return redirect('home')

@login_required
def player_feedback_for_players(request):
    """View for players to see feedback received"""
    try:
        player = request.user.player
        feedback_list = Feedback.objects.filter(
            player=player
        ).select_related('trainer')  # Only select_related('trainer') since trainer is a User FK
        
        total_feedback = feedback_list.count()
        unread_count = feedback_list.filter(is_read=False).count()
        
        context = {
            'feedback_list': feedback_list,
            'player': player,
            'total_feedback': total_feedback,
            'unread_count': unread_count,
        }
        return render(request, 'player_feedback_list.html', context)
        
    except Player.DoesNotExist:
        messages.error(request, "You don't have a player profile.")
        return redirect('home')
    
@login_required
def delete_feedback(request, feedback_id):
    """View to delete feedback"""
    feedback = get_object_or_404(
        Feedback, 
        id=feedback_id, 
        trainer=request.user
    )
    
    if request.method == 'POST':
        feedback.delete()
        messages.success(request, "Feedback deleted successfully.")
        return redirect('player_feedback_list')
    
    context = {
        'feedback': feedback,
    }
    return render(request, 'feedback/delete_feedback_confirm.html', context)

@login_required
def edit_feedback(request, feedback_id):
    """View to edit existing feedback"""
    feedback = get_object_or_404(
        Feedback, 
        id=feedback_id, 
        trainer=request.user
    )
    
    trainer = get_object_or_404(Trainer, user=request.user)
    
    if request.method == 'POST':
        form = FeedbackForm(trainer, request.POST, instance=feedback)
        if form.is_valid():
            form.save()
            messages.success(request, "Feedback updated successfully!")
            return redirect('player_feedback_detail', feedback_id=feedback.id)
    else:
        form = FeedbackForm(trainer, instance=feedback)
    
    context = {
        'form': form,
        'feedback': feedback,
    }
    return render(request, 'feedback/edit_feedback.html', context)

# === MATCH VIEWS ===
@login_required
def update_match_status(request, match_id):
    """Update the status of a match"""
    if not TournamentOrganiser.objects.filter(user=request.user).exists():
        messages.error(request, "You don't have permission to update match status.")
        return redirect('tournament_organiser_dashboard')
    
    match = get_object_or_404(TournamentSchedule, id=match_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['scheduled', 'ongoing', 'completed', 'cancelled', 'postponed']:
            match.status = new_status
            if new_status == 'completed':
                match.completed_at = timezone.now()
                # This calls _update_team_stats() which updates win rates
                match.save()
            else:
                match.save()
            messages.success(request, f'Match status updated to "{match.get_status_display()}"')
        else:
            messages.error(request, 'Invalid status selected.')
    
    return redirect('tournament_schedule')

@login_required
def edit_match(request, match_id):
    """Edit an existing match"""
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
    """Delete a match"""
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
    """View match details"""
    match = get_object_or_404(TournamentSchedule, id=match_id)
    return render(request, 'match_detail.html', {'match': match})

@login_required
def create_match(request):
    """Create a new match (Organisers only)"""
    # Check if user is a tournament organiser
    if not TournamentOrganiser.objects.filter(user=request.user).exists():
        messages.error(request, "You don't have permission to create matches.")
        return redirect('tournament_organiser_dashboard')
    
    if request.method == 'POST':
        form = TournamentScheduleForm(request.POST)
        if form.is_valid():
            match = form.save(commit=False)
            match.created_by = request.user
            match.save()
            messages.success(request, 'Tournament match created successfully!')
            return redirect('tournament_schedule')
    else:
        form = TournamentScheduleForm()
    
    teams = Team.objects.filter(is_approved=True)
    context = {
        'form': form,
        'teams': teams,
    }
    return render(request, 'create_match.html', context)

# === CHAT VIEWS ===
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
    """Start a new chat (individual or team)"""
    # Get user's teams
    my_teams = []
    if hasattr(request.user, 'player'):
        if request.user.player.team:
            my_teams = [request.user.player.team]
    elif hasattr(request.user, 'trainer'):
        my_teams = Team.objects.filter(trainer=request.user.trainer)

    if request.method == 'POST':
        room_type = request.POST.get('room_type', 'individual')

        if room_type == 'team':
            team_id = request.POST.get('team_id')
            if not team_id:
                messages.error(request, 'Please select a team.')
                return redirect('start_chat')

            try:
                team = Team.objects.get(id=team_id)
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
                    room_users = set(room.participants.all())
                    team_users = set(player.user for player in Player.objects.filter(team=team))
                    if room_users == team_users:
                        return redirect('chat_room', room_id=room.id)

                # Create new team chat room
                room = ChatRoom.objects.create(
                    name=f"Team {team.team_name} Chat",
                    room_type='group',
                    created_by=request.user
                )
                room.participants.add(request.user)
                for user in users:
                    room.participants.add(user)
                room.save()

                messages.success(request, f'Team chat for "{team.team_name}" created successfully!')
                return redirect('chat_room', room_id=room.id)

            except Team.DoesNotExist:
                messages.error(request, 'Team not found.')
                return redirect('start_chat')

        else:
            # Individual chat
            other_user_id = request.POST.get('user_id')
            if not other_user_id:
                messages.error(request, 'Please select a user.')
                return redirect('start_chat')

            other_user = get_object_or_404(User, id=other_user_id)

            # Check if chat already exists
            existing_room = ChatRoom.objects.filter(
                room_type='individual',
                participants=request.user
            ).filter(participants=other_user)

            if existing_room.exists():
                return redirect('chat_room', room_id=existing_room.first().id)

            # Create new individual chat
            room = ChatRoom.objects.create(
                room_type='individual',
                created_by=request.user
            )
            room.participants.add(request.user, other_user)
            messages.success(request, f'Chat with {other_user.username} started successfully!')
            return redirect('chat_room', room_id=room.id)

    # GET request
    all_users = User.objects.exclude(id=request.user.id)
    return render(request, 'start_chat.html', {
        'my_teams': my_teams,
        'all_users': all_users,
    })

# views.py

# === TOURNAMENT MANAGEMENT VIEWS ===
@login_required
def tournament_applications(request):
    """View for trainers to see their tournament applications"""
    try:
        trainer = get_object_or_404(Trainer, user=request.user)
        applications = TournamentApplication.objects.filter(trainer=trainer).order_by('-applied_at')
        
        # Get statistics
        total_applications = applications.count()
        pending_count = applications.filter(status='pending').count()
        approved_count = applications.filter(status='approved').count()
        declined_count = applications.filter(status='declined').count()
        
        context = {
            'applications': applications,
            'total_applications': total_applications,
            'pending_count': pending_count,
            'approved_count': approved_count,
            'declined_count': declined_count,
        }
        return render(request, 'tournament_applications.html', context)
        
    except Trainer.DoesNotExist:
        messages.warning(request, 'Trainer profile not found.')
        return redirect('trainer_dashboard')

@login_required
def create_tournament(request):
    """Create a new tournament (Organiser only)"""
    if not TournamentOrganiser.objects.filter(user=request.user).exists():
        messages.error(request, "You don't have permission to create tournaments.")
        return redirect('tournament_organiser_dashboard')
    
    if request.method == 'POST':
        form = TournamentForm(request.POST)
        if form.is_valid():
            tournament = form.save(commit=False)
            tournament.created_by = request.user
            tournament.status = 'open'  # Default to open
            tournament.save()
            messages.success(request, f'Tournament "{tournament.name}" created successfully!')
            return redirect('manage_tournaments')
    else:
        form = TournamentForm()
    
    context = {
        'form': form,
    }
    return render(request, 'create_tournament.html', context)


@login_required
def manage_tournaments(request):
    """Manage all tournaments (Organiser only)"""
    if not TournamentOrganiser.objects.filter(user=request.user).exists():
        messages.error(request, "You don't have permission to manage tournaments.")
        return redirect('tournament_organiser_dashboard')
    
    tournaments = Tournament.objects.filter(created_by=request.user).order_by('-created_at')
    
    context = {
        'tournaments': tournaments,
    }
    return render(request, 'manage_tournaments.html', context)


@login_required
def tournament_list_view(request):
    """View all tournaments for trainers"""
    try:
        # Check if user is a player
        if hasattr(request.user, 'player'):
            # Get open tournaments
            open_tournaments = Tournament.objects.filter(status='open').order_by('start_date')
            
            # Get tournaments the player's team is participating in
            player = request.user.player
            participating_tournaments = []
            if player.team:
                participating_tournaments = Tournament.objects.filter(
                    applications__team=player.team,
                    applications__status='approved'
                ).distinct()
            
            context = {
                'open_tournaments': open_tournaments,
                'participating_tournaments': participating_tournaments,
                'is_player': True,
            }
            return render(request, 'player_tournament_list.html', context)
        
        # Trainer view
        trainer = get_object_or_404(Trainer, user=request.user)
        trainer_teams = Team.objects.filter(trainer=trainer)
        
        # Get open tournaments
        open_tournaments = Tournament.objects.filter(status='open').order_by('start_date')
        
        # Get tournaments the trainer's teams have applied to
        applied_tournaments = Tournament.objects.filter(
            applications__team__in=trainer_teams,
            applications__status__in=['pending', 'approved']
        ).distinct()
        
        # Get tournaments the trainer's teams are participating in
        participating_tournaments = Tournament.objects.filter(
            applications__team__in=trainer_teams,
            applications__status='approved'
        ).distinct()
        
        context = {
            'open_tournaments': open_tournaments,
            'applied_tournaments': applied_tournaments,
            'participating_tournaments': participating_tournaments,
            'trainer_teams': trainer_teams,
            'is_player': False,
        }
        return render(request, 'tournament_list.html', context)
        
    except Trainer.DoesNotExist:
        messages.warning(request, 'Trainer profile not found.')
        return redirect('trainer_dashboard')


@login_required
def tournament_detail(request, tournament_id):
    """View tournament details including timetable"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    can_apply = tournament.can_apply
    
    # Check if trainer's team has applied
    has_applied = False
    application_status = None
    trainer_teams = []
    
    if hasattr(request.user, 'trainer'):
        trainer = request.user.trainer
        trainer_teams = Team.objects.filter(trainer=trainer)
        
        application = TournamentApplication.objects.filter(
            tournament=tournament,
            team__in=trainer_teams
        ).first()
        
        if application:
            has_applied = True
            application_status = application.status
    
    # Get matches/timetable
    matches = tournament.matches.all().order_by('date', 'time')
    
    context = {
        'tournament': tournament,
        'matches': matches,
        'has_applied': has_applied,
        'application_status': application_status,
        'trainer_teams': trainer_teams,
        'can_apply': can_apply,
        'spots_remaining': tournament.spots_remaining,
    }
    return render(request, 'tournament_detail.html', context)


@login_required
def tournament_schedule(request):
    """View for tournament schedule - both organisers and trainers"""
    is_organiser = TournamentOrganiser.objects.filter(user=request.user).exists()
    
    if is_organiser:
        # Organiser view - can create matches
        approved_teams = Team.objects.filter(
            tournament_applications__status='approved'
        ).distinct()
        
        matches = TournamentSchedule.objects.filter(
            created_by=request.user
        ).order_by('date', 'time')
        
        if request.method == 'POST':
            form = TournamentScheduleForm(request.POST)
            if form.is_valid():
                match = form.save(commit=False)
                match.created_by = request.user
                match.save()
                messages.success(request, 'Match created successfully!')
                return redirect('tournament_schedule')
        else:
            form = TournamentScheduleForm()
            form.fields['team1'].queryset = approved_teams
            form.fields['team2'].queryset = approved_teams
        
        context = {
            'matches': matches,
            'form': form,
            'is_organiser': True,
            'approved_teams': approved_teams,
        }
    else:
        # Trainer view - can only see matches involving their teams
        trainer = get_object_or_404(Trainer, user=request.user)
        trainer_teams = Team.objects.filter(trainer=trainer)
        
        matches = TournamentSchedule.objects.filter(
            Q(team1__in=trainer_teams) | Q(team2__in=trainer_teams)
        ).order_by('date', 'time')
        
        context = {
            'matches': matches,
            'is_organiser': False,
            'is_trainer': True,
        }
    
    return render(request, 'tournament_schedule.html', context)

@login_required
def update_application_status(request, application_id):
    """Update application status (Organiser only)"""
    if not TournamentOrganiser.objects.filter(user=request.user).exists():
        messages.error(request, "You don't have permission to update application status.")
        return redirect('tournament_organiser_dashboard')
    
    application = get_object_or_404(TournamentApplication, id=application_id)
    
    # Check if the tournament belongs to this organiser
    if application.tournament.created_by != request.user:
        messages.error(request, "You don't have permission to update this application.")
        return redirect('tournament_organiser_dashboard')
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['pending', 'approved', 'declined']:
            # Update the status
            application.status = new_status
            
            # If approved, check if tournament is now full
            if new_status == 'approved':
                application.reviewed_at = timezone.now()
                # Check if tournament is full
                if application.tournament.accepted_teams_count >= application.tournament.max_teams:
                    application.tournament.status = 'closed'
                    application.tournament.save()
                messages.success(request, f"✅ Application from {application.team.team_name} approved!")
            elif new_status == 'declined':
                application.reviewed_at = timezone.now()
                messages.success(request, f"❌ Application from {application.team.team_name} declined.")
            else:
                application.reviewed_at = None
                messages.info(request, f"⏳ Application from {application.team.team_name} set to pending.")
            
            application.save()
        else:
            messages.error(request, "Invalid status selected.")
    
    return redirect('tournament_detail', tournament_id=application.tournament.id)

@login_required
def update_match_score(request, match_id):
    """Update the score of a match (Organiser only)"""
    if not TournamentOrganiser.objects.filter(user=request.user).exists():
        messages.error(request, "You don't have permission to update match scores.")
        return redirect('tournament_organiser_dashboard')
    
    match = get_object_or_404(TournamentSchedule, id=match_id)
    
    if request.method == 'POST':
        score_team1 = request.POST.get('score_team1')
        score_team2 = request.POST.get('score_team2')
        
        if score_team1 is not None and score_team2 is not None:
            match.score_team1 = int(score_team1)
            match.score_team2 = int(score_team2)
            
            # Determine winner
            if match.score_team1 > match.score_team2:
                match.winner = match.team1
            elif match.score_team2 > match.score_team1:
                match.winner = match.team2
            else:
                match.winner = None
            
            # If scores are entered and status is not completed, mark as completed
            if match.status != 'completed':
                match.status = 'completed'
                match.completed_at = timezone.now()
                # This calls _update_team_stats() which updates win rates
                match.save()
            else:
                # If already completed, just save without updating stats again
                match.save()
            
            messages.success(request, f"Score updated for {match.name}!")
        else:
            messages.error(request, "Please enter valid scores.")
    
    return redirect('tournament_schedule')

# === CHAT VIEWS ===

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
    """Start a new chat (individual or team)"""
    # Get user's teams
    my_teams = []
    if hasattr(request.user, 'player'):
        if request.user.player.team:
            my_teams = [request.user.player.team]
    elif hasattr(request.user, 'trainer'):
        my_teams = Team.objects.filter(trainer=request.user.trainer)

    if request.method == 'POST':
        room_type = request.POST.get('room_type', 'individual')

        if room_type == 'team':
            team_id = request.POST.get('team_id')
            if not team_id:
                messages.error(request, 'Please select a team.')
                return redirect('start_chat')

            try:
                team = Team.objects.get(id=team_id)
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
                    room_users = set(room.participants.all())
                    team_users = set(player.user for player in Player.objects.filter(team=team))
                    if room_users == team_users:
                        return redirect('chat_room', room_id=room.id)

                # Create new team chat room
                room = ChatRoom.objects.create(
                    name=f"Team {team.team_name} Chat",
                    room_type='group',
                    created_by=request.user
                )
                room.participants.add(request.user)
                for user in users:
                    room.participants.add(user)
                room.save()

                messages.success(request, f'Team chat for "{team.team_name}" created successfully!')
                return redirect('chat_room', room_id=room.id)

            except Team.DoesNotExist:
                messages.error(request, 'Team not found.')
                return redirect('start_chat')

        else:
            # Individual chat
            other_user_id = request.POST.get('user_id')
            if not other_user_id:
                messages.error(request, 'Please select a user.')
                return redirect('start_chat')

            other_user = get_object_or_404(User, id=other_user_id)

            # Check if chat already exists
            existing_room = ChatRoom.objects.filter(
                room_type='individual',
                participants=request.user
            ).filter(participants=other_user)

            if existing_room.exists():
                return redirect('chat_room', room_id=existing_room.first().id)

            # Create new individual chat
            room = ChatRoom.objects.create(
                room_type='individual',
                created_by=request.user
            )
            room.participants.add(request.user, other_user)
            messages.success(request, f'Chat with {other_user.username} started successfully!')
            return redirect('chat_room', room_id=room.id)

    # GET request
    all_users = User.objects.exclude(id=request.user.id)
    return render(request, 'start_chat.html', {
        'my_teams': my_teams,
        'all_users': all_users,
    })

@login_required
def add_participants(request, room_id):
    """Add participants to a group chat"""
    room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
    
    if request.method == 'POST':
        user_ids = request.POST.getlist('user_ids')
        if user_ids:
            for user_id in user_ids:
                try:
                    user = User.objects.get(id=user_id)
                    room.participants.add(user)
                except User.DoesNotExist:
                    pass
            messages.success(request, f'{len(user_ids)} participant(s) added successfully.')
        else:
            messages.warning(request, 'Please select at least one user.')
        return redirect('chat_room', room_id=room.id)
    
    # Exclude users already in the room
    existing_participants = room.participants.all()
    available_users = User.objects.exclude(id__in=existing_participants)
    
    context = {
        'room': room,
        'available_users': available_users,
    }
    return render(request, 'add_participants.html', context)

@login_required
def delete_room(request, room_id):
    """Delete/Deactivate a chat room"""
    room = get_object_or_404(ChatRoom, id=room_id, created_by=request.user)
    if request.method == 'POST':
        room.is_active = False
        room.save()
        messages.success(request, 'Chat deleted successfully.')
        return redirect('chat_list')
    return render(request, 'confirm_delete_room.html', {'room': room})

@login_required
def player_training_sessions(request):
    """View for players to see training sessions for their team"""
    try:
        player = request.user.player
        team = player.team
        
        if not team:
            messages.warning(request, "You are not in a team yet.")
            return redirect('player_dashboard')
        
        # Get training sessions for the player's team
        sessions = TrainingSession.objects.filter(
            team=team
        ).order_by('date', 'time')
        
        # Status counts
        status_counts = {
            'pending': sessions.filter(status='pending').count(),
            'in_progress': sessions.filter(status='in_progress').count(),
            'completed': sessions.filter(status='completed').count(),
            'cancelled': sessions.filter(status='cancelled').count(),
        }
        
        context = {
            'sessions': sessions,
            'status_counts': status_counts,
            'team': team,
            'is_player': True,
        }
        return render(request, 'player_training_sessions.html', context)
        
    except Player.DoesNotExist:
        messages.error(request, "Player profile not found.")
        return redirect('home')
    
@login_required
def player_dashboard(request):
    """Dashboard for players"""
    try:
        player = request.user.player
        my_team = player.team
        my_team_name = my_team.team_name if my_team else "No Team"
        
        # Training sessions count
        training_sessions_count = 0
        if my_team:
            training_sessions_count = TrainingSession.objects.filter(team=my_team).count()
        
        # Get matches for the player's team
        if my_team:
            matches = TournamentSchedule.objects.filter(
                Q(team1=my_team) | Q(team2=my_team)
            ).order_by('date', 'time')
            
            upcoming_matches = matches.filter(status='scheduled')[:5]
            upcoming_matches_count = upcoming_matches.count()
            recent_matches = matches.filter(status='completed').order_by('-date', '-time')[:5]
            matches_played = matches.filter(status='completed').count()
            wins = matches.filter(winner=my_team).count()
            win_rate = int((wins / matches_played * 100)) if matches_played > 0 else 0
        else:
            upcoming_matches = []
            upcoming_matches_count = 0
            recent_matches = []
            matches_played = 0
            win_rate = 0
        
        # Unread feedback count
        unread_feedback_count = Feedback.objects.filter(
            player=player,
            is_read=False
        ).count()
        
    except Player.DoesNotExist:
        my_team_name = "No Team"
        upcoming_matches = []
        upcoming_matches_count = 0
        recent_matches = []
        matches_played = 0
        win_rate = 0
        unread_feedback_count = 0
        training_sessions_count = 0
    
    context = {
        'my_team_name': my_team_name,
        'upcoming_matches': upcoming_matches,
        'upcoming_matches_count': upcoming_matches_count,
        'recent_matches': recent_matches,
        'matches_played': matches_played,
        'win_rate': win_rate,
        'unread_feedback_count': unread_feedback_count,
        'training_sessions_count': training_sessions_count,
    }
    return render(request, 'player_dashboard.html', context)

@login_required
def player_tournament_view(request, tournament_id):
    """View-only tournament page for players"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Check if player's team is participating
    player = None
    is_participating = False
    application_status = None
    
    if hasattr(request.user, 'player'):
        player = request.user.player
        if player.team:
            application = TournamentApplication.objects.filter(
                tournament=tournament,
                team=player.team
            ).first()
            if application and application.status == 'approved':
                is_participating = True
                application_status = application.status
    
    # Get matches/timetable
    matches = tournament.matches.all().order_by('date', 'time')
    
    context = {
        'tournament': tournament,
        'matches': matches,
        'is_participating': is_participating,
        'application_status': application_status,
        'player': player,
        'is_organiser': False,
        'is_trainer': False,
        'is_player_view': True,
    }
    return render(request, 'player_tournament_detail.html', context)
@login_required
def player_tournament_schedule(request):
    """View for players to see tournaments their team is participating in"""
    try:
        player = request.user.player
        
        if not player.team:
            messages.warning(request, "You are not in a team yet.")
            return redirect('player_dashboard')
        
        # Get tournaments where the player's team is participating
        participating_tournaments = Tournament.objects.filter(
            applications__team=player.team,
            applications__status='approved'
        ).distinct()
        
        # Get tournaments where the player's team has applied (pending)
        pending_tournaments = Tournament.objects.filter(
            applications__team=player.team,
            applications__status='pending'
        ).distinct()
        
        # Get open tournaments the team can apply to
        open_tournaments = Tournament.objects.filter(
            status='open'
        ).exclude(
            applications__team=player.team
        ).order_by('start_date')
        
        context = {
            'participating_tournaments': participating_tournaments,
            'pending_tournaments': pending_tournaments,
            'open_tournaments': open_tournaments,
            'player': player,
            'team': player.team,
        }
        return render(request, 'player_tournament_schedule.html', context)
        
    except Player.DoesNotExist:
        messages.error(request, "Player profile not found.")
        return redirect('home')

@login_required
def send_player_feedback(request):
    return redirect('player_development')