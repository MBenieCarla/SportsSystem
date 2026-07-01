from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import AuthenticationForm
from . import views

urlpatterns = [
    # === HOME ===
    path('', views.home, name='home'),
    
    # === DASHBOARD ===
    path('dashboard/organiser/', views.tournament_organiser_dashboard, name='tournament_organiser_dashboard'),
    path('dashboard/player/', views.player_dashboard, name='player_dashboard'),
    path('dashboard/trainer/', views.trainer_dashboard, name='trainer_dashboard'),
    
    # === REGISTRATION ===
    path('register/', views.registration_choice, name='registration_choice'),
    path('register/player/', views.player_registration, name='player_registration'),
    path('register/trainer/', views.trainer_registration, name='trainer_registration'),
    path('register/tournament-organiser/', views.tournament_organiser_registration, name='tournament_organiser_registration'),

    # === MATCH SCHEDULE (Both Organiser & Trainer) ===
    path('tournament-schedule/', views.tournament_schedule, name='tournament_schedule'),
    
    # === TOURNAMENT VIEWS (Trainer) ===
    path('tournaments/', views.tournament_list_view, name='tournament_list'),
    path('tournament/<int:tournament_id>/', views.tournament_detail, name='tournament_detail'),
    path('tournament/<int:tournament_id>/apply/', views.apply_to_tournament, name='apply_to_tournament'),
    path('tournament/<int:tournament_id>/timetable/', views.tournament_timetable, name='tournament_timetable'),
    path('tournament/application/<int:application_id>/cancel/', views.cancel_application, name='cancel_application'),
    path('tournament/applications/', views.tournament_applications, name='tournament_applications'),
    
    # === TOURNAMENT ORGANISER MANAGEMENT ===
    path('organiser/tournaments/', views.manage_tournaments, name='manage_tournaments'),
    path('organiser/tournament/create/', views.create_tournament, name='create_tournament'),
    path('organiser/tournament/<int:tournament_id>/schedule/', views.create_tournament_schedule, name='create_tournament_schedule'),
    path('tournament/application/<int:application_id>/review/', views.review_application, name='review_application'),
    path('application/<int:application_id>/update-status/', views.update_application_status, name='update_application_status'),
    
    # === MATCH OPERATIONS ===
    path('match/create/', views.create_match, name='create_match'),
    path('match/edit/<int:match_id>/', views.edit_match, name='edit_match'),
    path('match/delete/<int:match_id>/', views.delete_match, name='delete_match'),
    path('match/<int:match_id>/', views.match_detail, name='match_detail'),
    path('match/<int:match_id>/update-status/', views.update_match_status, name='update_match_status'),
    path('match/<int:match_id>/update-score/', views.update_match_score, name='update_match_score'),
    
    # === ORGANISER ===
    path('organiser-details/', views.organiser_details, name='organiser_details'),
    path('manage-teams/', views.manage_teams, name='manage_teams'),
    path('manage-matches/', views.manage_matches, name='manage_matches'),
    path('profile-settings/', views.profile_settings, name='profile_settings'),
    
    # === PLAYER URLS ===
    path('player/profile/', views.player_profile, name='player_profile'),
    path('player/my-team/', views.my_team, name='my_team'),
    path('player/matches/', views.my_matches, name='my_matches'),
    path('player/standings/', views.team_standings, name='team_standings'),
    path('player/stats/', views.player_stats, name='player_stats'),
    path('player/settings/', views.player_settings, name='player_settings'),
    path('player/available-teams/', views.available_teams, name='available_teams'),
    path('player/join-request/<int:team_id>/', views.request_join_team, name='request_join_team'),
    
    # === TRAINER URLS ===
    path('trainer/profile/', views.trainer_profile, name='trainer_profile'),
    path('trainer/create-team/', views.create_team, name='create_team'),
    path('trainer/my-teams/', views.my_teams, name='my_teams'),
    path('trainer/schedule/', views.trainer_schedule, name='trainer_schedule'),
    path('trainer/performance/', views.team_performance, name='team_performance'),
    path('trainer/development/', views.player_development, name='player_development'),
    path('trainer/sessions/', views.training_sessions, name='training_sessions'),
    path('trainer/sessions/create/', views.create_training_session, name='create_training_session'),
    
    # === TRAINER - JOIN REQUESTS ===
    path('trainer/join-requests/', views.join_requests, name='join_requests'),
    path('trainer/join-requests/accept/<int:request_id>/', views.accept_join_request, name='accept_join_request'),
    path('trainer/join-requests/decline/<int:request_id>/', views.decline_join_request, name='decline_join_request'),
    
    # === CHAT URLS ===
    path('chat/', views.chat_list, name='chat_list'),
    path('chat/room/<int:room_id>/', views.chat_room, name='chat_room'),
    path('chat/start/', views.start_chat, name='start_chat'),
    path('chat/room/<int:room_id>/add-participants/', views.add_participants, name='add_participants'),
    path('chat/delete/<int:room_id>/', views.delete_room, name='delete_room'),
    
    # === AUTHENTICATION ===
    path('login/', auth_views.LoginView.as_view(
        template_name='login.html',
        authentication_form=AuthenticationForm, 
        redirect_authenticated_user=True,
        next_page='home'
    ), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # === PLAYER DEVELOPMENT ===
    path('player-development/', views.player_development, name='player_development'),
    
    # === TRAINING SESSIONS ===
    path('training-sessions/', views.training_sessions, name='training_sessions'),
    path('training-sessions/<int:session_id>/update-status/', views.update_session_status, name='update_session_status'),
    
    # === FEEDBACK URLS ===
    # Trainer feedback list
    path('feedback/list/', views.player_feedback_list, name='player_feedback_list'),
    # Player feedback list
    path('feedback/my-feedback/', views.player_feedback_for_players, name='player_feedback_for_players'),
    # Send feedback
    path('feedback/send/', views.send_player_feedback, name='send_player_feedback'),
    # Feedback detail (shared - marks as read for players)
    path('feedback/<int:feedback_id>/', views.player_feedback_detail, name='player_feedback_detail'),
    # Edit feedback
    path('feedback/<int:feedback_id>/edit/', views.edit_feedback, name='edit_feedback'),
    # Delete feedback
    path('feedback/<int:feedback_id>/delete/', views.delete_feedback, name='delete_feedback'),
    
    # === TEAM ===
    path('team/<int:team_id>/', views.team_detail, name='team_detail'),

    # === TRAINING SESSIONS ===
path('training-sessions/', views.training_sessions, name='training_sessions'),
path('training-sessions/player/', views.player_training_sessions, name='player_training_sessions'),
path('training-sessions/create/', views.create_training_session, name='create_training_session'),
path('training-sessions/<int:session_id>/update-status/', views.update_session_status, name='update_session_status'),
path('tournament/player-view/<int:tournament_id>/', views.player_tournament_view, name='player_tournament_view'),
path('player/tournament-schedule/', views.player_tournament_schedule, name='player_tournament_schedule'),

 path('feedback/development/', views.player_development, name='player_development'),
    path('feedback/list/', views.player_feedback_list, name='player_feedback_list'),
    path('feedback/send/', views.send_player_feedback, name='send_player_feedback'),
    path('feedback/detail/<int:feedback_id>/', views.player_feedback_detail, name='player_feedback_detail'),
    path('feedback/delete/<int:feedback_id>/', views.delete_feedback, name='delete_feedback'),
    path('feedback/edit/<int:feedback_id>/', views.edit_feedback, name='edit_feedback'),
    path('feedback/player/', views.player_feedback_for_players, name='player_feedback_for_players'),
]