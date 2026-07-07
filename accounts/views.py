from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from .forms import CustomUserCreationForm, CustomUserLoginForm, UserProfileUpdateForm
from .decorators import role_required
from core.models import (
    Team, TrainingSession, Tournament, Match, 
    PerformanceFeedback, TeamJoinRequest
)
from core.models import ChatRoom


def register_view(request):
    """User registration with team selection"""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # ✅ DON'T login the user
            # login(request, user)  <-- KEEP THIS COMMENTED OUT
            
            team = form.cleaned_data.get('team')
            if team:
                messages.success(
                    request, 
                    f'Registration successful! Your request to join {team.name} has been sent to the trainer. Please log in.'
                )
            else:
                messages.success(request, 'Registration successful! Please log in to continue.')
            
            # ✅ REDIRECT TO LOGIN PAGE
            return redirect('accounts:login')
        else:
            # ❌ If form invalid, show errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'register.html', {'form': form})


def login_view(request):
    """User login with role-based redirect"""
    if request.user.is_authenticated:
        # Redirect based on user type
        user = request.user
        if user.is_superuser or user.user_type == 'admin':
            return redirect('admin_panel:dashboard')
        else:
            return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = CustomUserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                
                # Redirect based on user type
                if user.is_superuser or user.user_type == 'admin':
                    return redirect('admin_panel:dashboard')
                else:
                    return redirect('accounts:dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = CustomUserLoginForm()
    
    return render(request, 'login.html', {'form': form})


@login_required
def logout_view(request):
    """User logout"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


# ==================== DASHBOARD ROUTER ====================

@login_required
def dashboard_view(request):
    """Route user to their appropriate dashboard based on role"""
    user = request.user
    
    if user.user_type == 'player':
        return player_dashboard(request)
    elif user.user_type == 'trainer':
        return trainer_dashboard(request)
    elif user.user_type == 'organizer':
        return organizer_dashboard(request)
    elif user.user_type == 'admin' or user.is_superuser:
        return admin_dashboard(request)
    
    return render(request, 'dashboard_base.html', {'user': user})


# ==================== PLAYER DASHBOARD ====================

@login_required
@role_required(['player'])
def player_dashboard(request):
    """Player dashboard showing teams, matches, trainings, and feedback"""
    user = request.user
    teams = user.player_teams.filter(is_active=True)
    
    # Matches Played
    matches_played = Match.objects.filter(
        Q(team_home__in=teams) | Q(team_away__in=teams),
        is_played=True
    ).distinct().count()
    
    # Upcoming Matches
    upcoming_matches = Match.objects.filter(
        Q(team_home__in=teams) | Q(team_away__in=teams),
        date__gte=timezone.now().date(),
        is_played=False
    ).distinct().order_by('date', 'time')[:5]
    
    upcoming_matches_count = upcoming_matches.count()
    
    # Win Rate
    all_matches = Match.objects.filter(
        Q(team_home__in=teams) | Q(team_away__in=teams),
        is_played=True
    ).distinct()
    
    wins = 0
    total_played = all_matches.count()
    
    for match in all_matches:
        for team in teams:
            if match.team_home == team:
                if match.score_home > match.score_away:
                    wins += 1
                    break
            elif match.team_away == team:
                if match.score_away > match.score_home:
                    wins += 1
                    break
    
    win_rate = round((wins / total_played * 100) if total_played > 0 else 0)
    
    # Tournament Count
    tournament_count = Tournament.objects.filter(
        teams_registered__in=teams
    ).distinct().count()
    
    # Upcoming training sessions
    upcoming_trainings = TrainingSession.objects.filter(
        team__in=teams,
        date__gte=timezone.now().date(),
        is_cancelled=False
    ).order_by('date', 'start_time')[:5]
    
    # Recent feedback
    recent_feedback = PerformanceFeedback.objects.filter(
        player=user
    ).order_by('-date')[:5]
    
    # Pending join requests
    join_requests = TeamJoinRequest.objects.filter(
        player=user,
        status='pending'
    )
    
    # Unread messages count
    unread_count = 0
    for room in user.chat_rooms.filter(is_active=True):
        unread_count += room.get_unread_count(user)
    
    context = {
        'user': user,
        'teams': teams,
        'matches_played': matches_played,
        'upcoming_matches': upcoming_matches,
        'upcoming_matches_count': upcoming_matches_count,
        'win_rate': win_rate,
        'tournament_count': tournament_count,
        'upcoming_trainings': upcoming_trainings,
        'recent_feedback': recent_feedback,
        'join_requests': join_requests,
        'unread_count': unread_count,
        'dashboard_type': 'player'
    }
    
    return render(request, 'player_dashboard.html', context)


# ==================== TRAINER DASHBOARD ====================

@login_required
@role_required(['trainer'])
def trainer_dashboard(request):
    """Trainer dashboard showing teams, players, and training sessions"""
    user = request.user
    teams = user.trainer_teams.filter(is_active=True)
    
    # Upcoming training sessions
    upcoming_trainings = TrainingSession.objects.filter(
        team__in=teams,
        date__gte=timezone.now().date(),
        is_cancelled=False
    ).order_by('date', 'start_time')[:5]
    
    # Pending join requests
    pending_requests = TeamJoinRequest.objects.filter(
        team__in=teams,
        status='pending'
    )
    pending_requests_count = TeamJoinRequest.objects.filter(
        team__in=teams,
        status='pending'
    ).count()
    
    # Upcoming tournaments
    upcoming_tournaments = Tournament.objects.filter(
        teams_registered__in=teams,
        status__in=['upcoming', 'ongoing']
    ).distinct().order_by('start_date')[:5]
    
    # Team statistics
    total_players = sum([team.get_player_count() for team in teams])
    total_trainings = TrainingSession.objects.filter(team__in=teams).count()
    
    context = {
        'user': user,
        'teams': teams,
        'upcoming_trainings': upcoming_trainings,
        'pending_requests': pending_requests,
        'upcoming_tournaments': upcoming_tournaments,
        'total_players': total_players,
        'total_trainings': total_trainings,
        'total_teams': len(teams),
        'pending_requests_count': pending_requests_count,
        'dashboard_type': 'trainer'
    }
    
    return render(request, 'trainer_dashboard.html', context)


# ==================== ORGANIZER DASHBOARD ====================

@login_required
@role_required(['organizer'])
def organizer_dashboard(request):
    """Organizer dashboard showing tournaments and matches"""
    user = request.user
    tournaments = user.tournaments.all()
    
    # Upcoming matches
    upcoming_matches = Match.objects.filter(
        tournament__in=tournaments,
        date__gte=timezone.now().date()
    ).order_by('date', 'time')[:5]
    
    # Active tournaments
    active_tournaments = tournaments.filter(status__in=['upcoming', 'ongoing'])
    
    # Statistics
    total_tournaments = tournaments.count()
    total_matches = Match.objects.filter(tournament__in=tournaments).count()
    total_teams_registered = Tournament.objects.filter(
        organizer=user
    ).aggregate(total=Count('teams_registered'))['total'] or 0
    
    context = {
        'user': user,
        'tournaments': tournaments,
        'upcoming_matches': upcoming_matches,
        'active_tournaments': active_tournaments,
        'total_tournaments': total_tournaments,
        'total_matches': total_matches,
        'total_teams': total_teams_registered,
        'dashboard_type': 'organizer'
    }
    
    return render(request, 'organizer_dashboard.html', context)


# ==================== ADMIN DASHBOARD ====================

@login_required
@role_required(['admin'])
def admin_dashboard(request):
    """Admin dashboard showing system-wide statistics"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Statistics
    total_users = User.objects.count()
    total_teams = Team.objects.count()
    total_tournaments = Tournament.objects.count()
    total_trainings = TrainingSession.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    
    # User type breakdown
    players = User.objects.filter(user_type='player').count()
    trainers = User.objects.filter(user_type='trainer').count()
    organizers = User.objects.filter(user_type='organizer').count()
    
    # Recent activities (✅ FIXED: use [:5] not [5])
    recent_users = User.objects.order_by('-date_joined')[:5]
    recent_tournaments = Tournament.objects.order_by('-created_at')[:5]
    recent_teams = Team.objects.order_by('-created_at')[:5]
    
    context = {
        'user': request.user,
        'total_users': total_users,
        'total_teams': total_teams,
        'total_tournaments': total_tournaments,
        'total_trainings': total_trainings,
        'active_users': active_users,
        'players': players,
        'trainers': trainers,
        'organizers': organizers,
        'recent_users': recent_users,
        'recent_tournaments': recent_tournaments,
        'recent_teams': recent_teams,
        'dashboard_type': 'admin'
    }
    
    return render(request, 'admin_dashboard.html', context)


# ==================== PROFILE VIEW ====================

@login_required
def profile_view(request):
    """View for user to see and edit their profile"""
    user = request.user
    
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileUpdateForm(instance=user)
    
    context = {
        'form': form,
        'user': user,
    }
    return render(request, 'profile.html', context)

