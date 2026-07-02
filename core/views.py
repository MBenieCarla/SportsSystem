from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import JsonResponse
from accounts.decorators import role_required
from accounts.forms import UserProfileUpdateForm

from .models import (
    Team, TrainingSession, Tournament, Match, 
    PerformanceFeedback, TeamJoinRequest, PlayerTrainingAttendance,
    ChatRoom, Message, TournamentTeamRequest, TournamentApplication
)
from .forms import (
    TrainingSessionForm, TournamentForm, MatchForm, 
    PerformanceFeedbackForm, TeamForm,
    MessageForm, CreateChatRoomForm
)

User = get_user_model()


# ==================== HOME PAGE ====================

def home_view(request):
    """Show homepage, redirect to dashboard if logged in"""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    return render(request, 'home.html')


# ==================== PLAYER VIEWS ====================

@login_required
@role_required(['player'])
def player_tournaments_view(request):
    """Show tournaments the player's team is in + all upcoming tournaments"""
    user = request.user
    teams = user.player_teams.filter(is_active=True)
    
    # Tournaments the player's teams are registered in
    my_tournaments = Tournament.objects.filter(
        teams_registered__in=teams
    ).distinct().order_by('start_date')
    
    # All upcoming tournaments for browsing
    all_upcoming_tournaments = Tournament.objects.filter(
        status='upcoming'
    ).exclude(
        teams_registered__in=teams
    ).distinct().order_by('start_date')[:10]
    
    context = {
        'my_tournaments': my_tournaments,
        'all_upcoming_tournaments': all_upcoming_tournaments,
    }
    return render(request, 'tournaments.html', context)


@login_required
@role_required(['player'])
def player_tournament_schedule_view(request):
    """Show all tournament schedules and matches"""
    all_tournaments = Tournament.objects.filter(
        status__in=['upcoming', 'ongoing']
    ).order_by('start_date')
    
    all_matches = Match.objects.filter(
        tournament__in=all_tournaments,
        date__gte=timezone.now().date()
    ).order_by('date', 'time')
    
    context = {
        'tournaments': all_tournaments,
        'matches': all_matches,
        'user': request.user,
    }
    return render(request, 'tournament_schedule.html', context)


@login_required
@role_required(['player'])
def player_trainings_view(request):
    """Show upcoming and past training sessions for the player"""
    user = request.user
    teams = user.player_teams.filter(is_active=True)
    
    upcoming_trainings = TrainingSession.objects.filter(
        team__in=teams,
        date__gte=timezone.now().date(),
        is_cancelled=False
    ).order_by('date', 'start_time')
    
    past_trainings = TrainingSession.objects.filter(
        team__in=teams,
        date__lt=timezone.now().date()
    ).order_by('-date')
    
    context = {
        'upcoming_trainings': upcoming_trainings,
        'past_trainings': past_trainings,
    }
    return render(request, 'trainings.html', context)


@login_required
@role_required(['player'])
def player_feedback_view(request):
    """Show performance feedback for the player"""
    user = request.user
    feedbacks = PerformanceFeedback.objects.filter(player=user).order_by('-date')
    
    context = {
        'feedbacks': feedbacks,
    }
    return render(request, 'feedback.html', context)


@login_required
def my_team_view(request):
    """Show the player's team details"""
    user = request.user
    teams = user.player_teams.filter(is_active=True)
    
    context = {
        'teams': teams,
    }
    return render(request, 'my_team.html', context)


# ==================== TRAINER VIEWS ====================

@login_required
@role_required(['trainer'])
def create_training_view(request):
    """Create a new training session"""
    if request.method == 'POST':
        form = TrainingSessionForm(request.POST, user=request.user)
        if form.is_valid():
            training = form.save(commit=False)
            training.created_by = request.user
            training.save()
            messages.success(request, 'Training session created successfully!')
            return redirect('accounts:trainer_dashboard')
    else:
        form = TrainingSessionForm(user=request.user)
    
    return render(request, 'create_training.html', {'form': form})


@login_required
@role_required(['trainer'])
def manage_teams_view(request):
    """Manage teams - create, activate/deactivate, remove players"""
    
    # ✅ FIX: Get ALL teams, not just active ones
    teams = request.user.trainer_teams.all().order_by('-created_at')  # Changed from filter(is_active=True)
    
    if request.method == 'POST':
        team_id = request.POST.get('team_id')
        action = request.POST.get('action')
        
        # CREATE NEW TEAM
        if action == 'create_team':
            form = TeamForm(request.POST)
            if form.is_valid():
                team_obj = form.save(commit=False)
                team_obj.trainer = request.user
                team_obj.is_active = True  # ✅ Make sure it's active by default
                team_obj.save()
                messages.success(request, f'Team "{team_obj.name}" created successfully!')
                return redirect('core:manage_teams')  # ✅ Redirect to refresh the page
            else:
                messages.error(request, 'Invalid team data. Please check the form.')
                return redirect('core:manage_teams')
        
        # ✅ Check if team_id exists for other actions
        if not team_id:
            messages.error(request, 'No team selected.')
            return redirect('core:manage_teams')
        
        try:
            team = Team.objects.get(id=team_id, trainer=request.user)
        except Team.DoesNotExist:
            messages.error(request, 'Team not found.')
            return redirect('core:manage_teams')
        
        # Remove player from team
        if action == 'remove_player':
            player_id = request.POST.get('player_id')
            if not player_id:
                messages.error(request, 'No player selected.')
                return redirect('core:manage_teams')
            
            try:
                player = User.objects.get(id=player_id)
            except User.DoesNotExist:
                messages.error(request, 'Player not found.')
                return redirect('core:manage_teams')
            
            team.players.remove(player)
            messages.success(request, f'Player removed from {team.name}')
        
        # Activate/Deactivate team
        elif action == 'activate':
            team.is_active = not team.is_active
            team.save()
            status = 'activated' if team.is_active else 'deactivated'
            messages.success(request, f'Team {status} successfully')
    
    context = {
        'teams': teams,
    }
    return render(request, 'manage_teams.html', context)


@login_required
@role_required(['trainer'])
def manage_join_requests_view(request):
    """Manage player join requests for trainer's teams"""
    trainer = request.user
    teams = trainer.trainer_teams.filter(is_active=True)
    
    pending_requests = TeamJoinRequest.objects.filter(
        team__in=teams,
        status='pending'
    ).select_related('player', 'team').order_by('-created_at')
    
    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        action = request.POST.get('action')
        join_request = get_object_or_404(TeamJoinRequest, id=request_id, team__trainer=trainer)
        
        if action == 'approve':
            join_request.status = 'approved'
            join_request.responded_at = timezone.now()
            join_request.save()
            join_request.team.players.add(join_request.player)
            messages.success(request, f'✅ Player approved for {join_request.team.name}!')
        
        elif action == 'reject':
            join_request.status = 'rejected'
            join_request.responded_at = timezone.now()
            join_request.save()
            messages.info(request, f'❌ Player rejected for {join_request.team.name}.')
        
        elif action == 'bulk_approve':
            team_id = request.POST.get('team_id')
            team = get_object_or_404(Team, id=team_id, trainer=trainer)
            pending = TeamJoinRequest.objects.filter(team=team, status='pending')
            count = pending.count()
            for req in pending:
                req.status = 'approved'
                req.responded_at = timezone.now()
                req.save()
                req.team.players.add(req.player)
            messages.success(request, f'✅ {count} players approved for {team.name}!')
        
        return redirect('core:manage_join_requests')
    
    context = {
        'pending_requests': pending_requests,
        'total_pending': pending_requests.count(),
        'teams': teams,
    }
    return render(request, 'manage_join_requests.html', context)


@login_required
@role_required(['trainer'])
def trainer_trainings_view(request):
    """Show all training sessions for the trainer's teams"""
    teams = request.user.trainer_teams.all()
    trainings = TrainingSession.objects.filter(team__in=teams).order_by('-date')
    
    context = {
        'trainings': trainings,
        'teams': teams,
    }
    return render(request, 'training_sessions.html', context)


@login_required
@role_required(['trainer'])
def edit_training_view(request, pk):
    """Edit an existing training session"""
    training = get_object_or_404(TrainingSession, id=pk, created_by=request.user)
    
    if request.method == 'POST':
        form = TrainingSessionForm(request.POST, instance=training, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Training session updated successfully!')
            return redirect('core:trainer_trainings')
    else:
        form = TrainingSessionForm(instance=training, user=request.user)
    
    return render(request, 'create_training.html', {'form': form, 'editing': True})


@login_required
@role_required(['trainer'])
def delete_training_view(request, pk):
    """Delete a training session"""
    training = get_object_or_404(TrainingSession, id=pk, created_by=request.user)
    
    if request.method == 'POST':
        training.delete()
        messages.success(request, 'Training session deleted successfully!')
        return redirect('core:trainer_trainings')
    
    return render(request, 'delete_training.html', {'training': training})


# ==================== ORGANIZER VIEWS ====================

@login_required
@role_required(['organizer'])
def create_tournament(request):
    """Create a new tournament"""
    if request.method == 'POST':
        tournament = Tournament.objects.create(
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            sport_type=request.POST.get('sport_type'),
            start_date=request.POST.get('start_date'),
            end_date=request.POST.get('end_date'),
            location=request.POST.get('location'),
            registration_deadline=request.POST.get('registration_deadline'),
            max_teams=request.POST.get('max_teams', 16),
            organizer=request.user,
            status='upcoming'
        )
        messages.success(request, f'Tournament "{tournament.title}" created successfully!')
        return redirect('core:manage_tournaments')
    
    return render(request, 'create_tournament.html')


@login_required
@role_required(['organizer'])
def manage_tournaments(request):
    """Manage tournaments - update status, add/remove teams, delete"""
    user = request.user
    tournaments = user.tournaments.all().order_by('-created_at')
    all_teams = Team.objects.filter(is_active=True)
    
    if request.method == 'POST':
        tournament_id = request.POST.get('tournament_id')
        action = request.POST.get('action')
        tournament = get_object_or_404(Tournament, id=tournament_id, organizer=user)
        
        # Update tournament status
        if action == 'update_status':
            status = request.POST.get('status')
            tournament.status = status
            tournament.save()
            messages.success(request, f'Tournament status updated to {status}')
        
        # Add team to tournament
        elif action == 'add_team':
            team_id = request.POST.get('team_id')
            
            # ✅ FIX: Check if team_id exists before trying to get it
            if team_id:
                try:
                    team = Team.objects.get(id=team_id)
                except Team.DoesNotExist:
                    messages.error(request, 'Team not found!')
                    return redirect('core:manage_tournaments')
                
                if tournament.get_available_slots() > 0:
                    if not tournament.teams_registered.filter(id=team.id).exists():
                        tournament.teams_registered.add(team)
                        messages.success(request, f'Team "{team.name}" added to tournament')
                    else:
                        messages.warning(request, f'Team "{team.name}" is already registered')
                else:
                    messages.error(request, 'Tournament is full!')
            else:
                messages.error(request, 'Please select a team.')
        
        # Remove team from tournament
        elif action == 'remove_team':
            team_id = request.POST.get('team_id')
            
            # ✅ FIX: Check if team_id exists
            if team_id:
                try:
                    team = Team.objects.get(id=team_id)
                except Team.DoesNotExist:
                    messages.error(request, 'Team not found!')
                    return redirect('core:manage_tournaments')
                
                tournament.teams_registered.remove(team)
                messages.success(request, f'Team "{team.name}" removed from tournament')
            else:
                messages.error(request, 'Please select a team.')
        
        # Delete tournament
        elif action == 'delete':
            tournament.delete()
            messages.success(request, 'Tournament deleted successfully!')
            return redirect('core:manage_tournaments')
    
    context = {
        'tournaments': tournaments,
        'all_teams': all_teams,
    }
    return render(request, 'manage_tournaments.html', context)


@login_required
@role_required(['organizer'])
def tournament_requests(request):
    """Manage team join requests for tournaments"""
    user = request.user
    tournaments = user.tournaments.all()
    
    pending_requests = TournamentTeamRequest.objects.filter(
        tournament__in=tournaments,
        status='pending'
    ).select_related('team', 'tournament').order_by('-created_at')
    
    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        action = request.POST.get('action')
        team_request = get_object_or_404(TournamentTeamRequest, id=request_id)
        
        if action == 'approve':
            team_request.status = 'approved'
            team_request.responded_at = timezone.now()
            team_request.save()
            team_request.tournament.teams_registered.add(team_request.team)
            messages.success(request, f'Team "{team_request.team.name}" approved for {team_request.tournament.title}')
        
        elif action == 'reject':
            team_request.status = 'rejected'
            team_request.responded_at = timezone.now()
            team_request.save()
            messages.info(request, f'Team "{team_request.team.name}" rejected for {team_request.tournament.title}')
        
        elif action == 'bulk_approve':
            tournament_id = request.POST.get('tournament_id')
            tournament = get_object_or_404(Tournament, id=tournament_id, organizer=user)
            pending = TournamentTeamRequest.objects.filter(tournament=tournament, status='pending')
            count = pending.count()
            for req in pending:
                req.status = 'approved'
                req.responded_at = timezone.now()
                req.save()
                req.tournament.teams_registered.add(req.team)
            messages.success(request, f'✅ {count} teams approved for {tournament.title}!')
        
        return redirect('core:tournament_requests')
    
    context = {
        'pending_requests': pending_requests,
        'total_pending': pending_requests.count(),
        'tournaments': tournaments,
    }
    return render(request, 'tournament_requests.html', context)


@login_required
@role_required(['organizer'])
def update_match_scores(request):
    """Update scores for matches in organizer's tournaments"""
    user = request.user
    tournaments = user.tournaments.all()
    
    matches = Match.objects.filter(
        tournament__in=tournaments
    ).order_by('-date', 'time')
    
    if request.method == 'POST':
        match = get_object_or_404(Match, id=request.POST.get('match_id'), tournament__organizer=user)
        score_home = request.POST.get('score_home')
        score_away = request.POST.get('score_away')
        
        if score_home is not None and score_away is not None:
            match.score_home = int(score_home)
            match.score_away = int(score_away)
            match.is_played = True
            match.save()
            messages.success(request, f'Score updated: {match.team_home.name} {score_home} - {score_away} {match.team_away.name}')
        else:
            messages.error(request, 'Please provide both scores.')
        
        return redirect('core:update_match_scores')
    
    context = {
        'matches': matches,
        'tournaments': tournaments,
    }
    return render(request, 'update_scores.html', context)


# ==================== CHAT VIEWS ====================

@login_required
def chat_list_view(request):
    """Show all chat rooms for the current user"""
    user = request.user
    chat_rooms = user.chat_rooms.filter(is_active=True).order_by('-updated_at')
    
    for room in chat_rooms:
        room.unread_count = room.get_unread_count(user)
    
    context = {
        'chat_rooms': chat_rooms,
        'user': user,
    }
    return render(request, 'chat_list.html', context)


@login_required
def chat_room_view(request, room_id):
    """Display a specific chat room with messages"""
    user = request.user
    chat_room = get_object_or_404(ChatRoom, id=room_id, participants=user, is_active=True)
    messages_list = chat_room.messages.all().select_related('sender')
    
    for message in messages_list:
        message.mark_as_read(user)
    
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.chat_room = chat_room
            message.sender = user
            message.save()
            chat_room.updated_at = timezone.now()
            chat_room.save()
            return redirect('core:chat_room', room_id=chat_room.id)
    else:
        form = MessageForm()
    
    other_participants = chat_room.participants.exclude(id=user.id)
    
    context = {
        'chat_room': chat_room,
        'messages': messages_list,
        'form': form,
        'other_participants': other_participants,
        'is_direct': chat_room.room_type == 'direct',
        'is_team': chat_room.room_type == 'team',
        'is_tournament': chat_room.room_type == 'tournament',
    }
    return render(request, 'chat_room.html', context)


@login_required
def create_chat_room_view(request):
    """Create a new chat room"""
    user = request.user
    participant_id = request.GET.get('participant')
    team_id = request.GET.get('team')
    
    if request.method == 'POST':
        form = CreateChatRoomForm(request.POST, user=user)
        if form.is_valid():
            chat_room = form.save(commit=False)
            chat_room.created_by = user
            chat_room.save()
            
            participants = form.cleaned_data['participants']
            chat_room.participants.add(user)
            chat_room.participants.add(*participants)
            
            if chat_room.room_type == 'team' and chat_room.team:
                for player in chat_room.team.players.all():
                    if player not in chat_room.participants.all():
                        chat_room.participants.add(player)
            
            messages.success(request, 'Chat room created successfully!')
            return redirect('core:chat_room', room_id=chat_room.id)
    else:
        initial = {}
        if participant_id:
            initial['participants'] = [int(participant_id)]
        if team_id:
            initial['team'] = int(team_id)
            initial['room_type'] = 'team'
        form = CreateChatRoomForm(user=user, initial=initial)
    
    context = {
        'form': form,
    }
    return render(request, 'create_chat_room.html', context)


@login_required
def get_unread_count_view(request):
    """AJAX endpoint to get unread message count"""
    user = request.user
    total_unread = 0
    
    for room in user.chat_rooms.filter(is_active=True):
        total_unread += room.get_unread_count(user)
    
    return JsonResponse({'unread_count': total_unread})


@login_required
def send_message_ajax_view(request):
    """AJAX endpoint to send messages without page reload"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    room_id = request.POST.get('room_id')
    content = request.POST.get('content')
    
    if not room_id or not content:
        return JsonResponse({'error': 'Missing required fields'}, status=400)
    
    chat_room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
    
    message = Message.objects.create(
        chat_room=chat_room,
        sender=request.user,
        content=content,
        message_type='text'
    )
    
    chat_room.updated_at = timezone.now()
    chat_room.save()
    
    return JsonResponse({
        'id': message.id,
        'sender': message.sender.username,
        'content': message.content,
        'created_at': message.created_at.strftime('%H:%M'),
        'is_owner': True
    })

# ==================== TOURNAMENT APPLICATION VIEWS ====================

from django.utils import timezone

@login_required
@role_required(['trainer'])
def tournament_list_for_trainer(request):
    """Show all tournaments with apply button for trainers"""
    tournaments = Tournament.objects.filter(
        status__in=['upcoming', 'ongoing']
    ).order_by('start_date')
    
    trainer_teams = request.user.trainer_teams.filter(is_active=True)
    
    # Get applications
    applications = TournamentApplication.objects.filter(
        team__in=trainer_teams
    )
    
    # Create status dictionary
    status_dict = {}
    for app in applications:
        status_dict[app.tournament_id] = app.status
    
    # Add status and check deadline
    for tournament in tournaments:
        tournament.my_status = status_dict.get(tournament.id, None)
    
    context = {
        'tournaments': tournaments,
        'trainer_teams': trainer_teams,
        'now': timezone.now().date(),  # ✅ Add this
    }
    return render(request, 'tournament_list.html', context)


@login_required
@role_required(['trainer'])
def apply_to_tournament(request, tournament_id):
    """Trainer applies their team to a tournament"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    if request.method == 'POST':
        team_id = request.POST.get('team_id')
        message = request.POST.get('message', '')
        
        # Check if team belongs to this trainer
        team = get_object_or_404(Team, id=team_id, trainer=request.user)
        
        # Check if already applied
        existing = TournamentApplication.objects.filter(
            tournament=tournament,
            team=team
        ).first()
        
        if existing:
            messages.warning(request, f'Team "{team.name}" has already applied to this tournament.')
        else:
            TournamentApplication.objects.create(
                tournament=tournament,
                team=team,
                status='pending',
                message=message
            )
            messages.success(request, f'Team "{team.name}" applied to {tournament.title} successfully!')
        
        return redirect('core:tournament_list_for_trainer')
    
    return redirect('core:tournament_list_for_trainer')


@login_required
@role_required(['organizer'])
def manage_tournament_applications(request, tournament_id):
    """Organizer views and manages applications for a specific tournament"""
    tournament = get_object_or_404(Tournament, id=tournament_id, organizer=request.user)
    
    # Get all applications for this tournament
    applications = TournamentApplication.objects.filter(
        tournament=tournament
    ).select_related('team', 'team__trainer').order_by('-applied_at')
    
    # Statistics
    pending_count = applications.filter(status='pending').count()
    approved_count = applications.filter(status='approved').count()
    rejected_count = applications.filter(status='rejected').count()
    
    if request.method == 'POST':
        application_id = request.POST.get('application_id')
        action = request.POST.get('action')
        
        application = get_object_or_404(TournamentApplication, id=application_id, tournament=tournament)
        
        if action == 'approve':
            application.status = 'approved'
            application.responded_at = timezone.now()
            application.save()
            # Add team to tournament
            tournament.teams_registered.add(application.team)
            messages.success(request, f'Team "{application.team.name}" approved for {tournament.title}!')
        
        elif action == 'reject':
            application.status = 'rejected'
            application.responded_at = timezone.now()
            application.save()
            messages.info(request, f'Team "{application.team.name}" rejected from {tournament.title}.')
        
        elif action == 'bulk_approve':
            # Approve all pending
            pending = applications.filter(status='pending')
            count = pending.count()
            for app in pending:
                app.status = 'approved'
                app.responded_at = timezone.now()
                app.save()
                tournament.teams_registered.add(app.team)
            messages.success(request, f'✅ {count} teams approved for {tournament.title}!')
        
        return redirect('core:manage_tournament_applications', tournament_id=tournament.id)
    
    context = {
        'tournament': tournament,
        'applications': applications,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    return render(request, 'manage_applications.html', context)


@login_required
def tournament_schedule_view(request):
    """View tournament schedules - accessible by all users"""
    if request.user.user_type == 'organizer':
        tournaments = request.user.tournaments.all()
        matches = Match.objects.filter(tournament__in=tournaments).order_by('date', 'time')
    else:
        tournaments = Tournament.objects.filter(status__in=['upcoming', 'ongoing']).order_by('start_date')
        matches = Match.objects.filter(
            tournament__in=tournaments,
            date__gte=timezone.now().date()
        ).order_by('date', 'time')
    
    # For trainers, show if their teams have applied
    if request.user.user_type == 'trainer':
        trainer_teams = request.user.trainer_teams.filter(is_active=True)
        applications = TournamentApplication.objects.filter(
            team__in=trainer_teams
        ).select_related('tournament')
        applied_tournament_ids = [app.tournament.id for app in applications]
    else:
        applied_tournament_ids = []
    
    context = {
        'tournaments': tournaments,
        'matches': matches,
        'user': request.user,
        'applied_tournament_ids': applied_tournament_ids,
    }
    return render(request, 'tournament_schedule.html', context)

# ==================== UPDATE MATCH SCORE ====================

@login_required
@role_required(['organizer'])
def update_match_score(request):
    """Organizer updates match score"""
    if request.method == 'POST':
        match_id = request.POST.get('match_id')
        score_home = request.POST.get('score_home')
        score_away = request.POST.get('score_away')
        
        # Get the match
        match = get_object_or_404(Match, id=match_id, tournament__organizer=request.user)
        
        # Update score
        match.score_home = int(score_home)
        match.score_away = int(score_away)
        match.is_played = True  
        match.save()
        
        messages.success(request, f'Score updated: {match.team_home.name} {score_home} - {score_away} {match.team_away.name}')
        return redirect('core:match_schedule_view')
    
    return redirect('core:match_schedule_view')
# ==================== VIEW MATCH SCHEDULE ====================
@login_required
def match_schedule_view(request):
    """View match schedule + create match form for organizers"""
    user = request.user
    
    if user.user_type == 'organizer':
        tournaments = user.tournaments.all()
        matches = Match.objects.filter(tournament__in=tournaments).order_by('date', 'time')
        all_teams = Team.objects.filter(is_active=True)
    else:
        matches = Match.objects.filter(date__gte=timezone.now().date()).order_by('date', 'time')
        all_teams = []
    
    if user.user_type == 'trainer':
        trainer_teams = user.trainer_teams.all()
        my_team_matches = matches.filter(
            Q(team_home__in=trainer_teams) | Q(team_away__in=trainer_teams)
        )
    elif user.user_type == 'player':
        player_teams = user.player_teams.all()
        my_team_matches = matches.filter(
            Q(team_home__in=player_teams) | Q(team_away__in=player_teams)
        )
    else:
        my_team_matches = None
    
    context = {
        'matches': matches,
        'my_team_matches': my_team_matches,
        'is_organizer': user.user_type == 'organizer',
        'tournaments': user.tournaments.all() if user.user_type == 'organizer' else [],
        'all_teams': all_teams,
        'user': user,
    }
    return render(request, 'match_schedule.html', context)

# ==================== CREATE MATCH ====================

@login_required
@role_required(['organizer'])
def create_match(request):
    """Organizer creates a match between two teams"""
    if request.method == 'POST':
        # Get form data
        tournament_id = request.POST.get('tournament_id')
        team_home_id = request.POST.get('team_home')
        team_away_id = request.POST.get('team_away')
        date = request.POST.get('date')
        time = request.POST.get('time')
        location = request.POST.get('location')
        
        # Validate all fields
        if not all([tournament_id, team_home_id, team_away_id, date, time, location]):
            messages.error(request, 'All fields are required.')
            return redirect('core:match_schedule_view')
        
        # Get tournament
        try:
            tournament = Tournament.objects.get(id=tournament_id, organizer=request.user)
        except Tournament.DoesNotExist:
            messages.error(request, 'Tournament not found.')
            return redirect('core:match_schedule_view')
        
        # Get teams
        try:
            team_home = Team.objects.get(id=team_home_id)
            team_away = Team.objects.get(id=team_away_id)
        except Team.DoesNotExist:
            messages.error(request, 'Team not found.')
            return redirect('core:match_schedule_view')
        
        # Check if teams are registered in tournament
        if team_home not in tournament.teams_registered.all():
            messages.error(request, f'"{team_home.name}" is not registered in this tournament.')
            return redirect('core:match_schedule_view')
            
        if team_away not in tournament.teams_registered.all():
            messages.error(request, f'"{team_away.name}" is not registered in this tournament.')
            return redirect('core:match_schedule_view')
        
        # Check if home and away are different
        if team_home == team_away:
            messages.error(request, 'Home and Away teams cannot be the same.')
            return redirect('core:match_schedule_view')
        
        # Check if match already exists
        existing = Match.objects.filter(
            tournament=tournament,
            team_home=team_home,
            team_away=team_away,
            date=date
        ).exists()
        
        if existing:
            messages.warning(request, 'This match already exists.')
            return redirect('core:match_schedule_view')
        
        # Create match
        Match.objects.create(
            tournament=tournament,
            team_home=team_home,
            team_away=team_away,
            date=date,
            time=time,
            location=location
        )
        
        messages.success(request, f'✅ Match created: {team_home.name} vs {team_away.name}')
        return redirect('core:match_schedule_view')
    
    return redirect('core:match_schedule_view')