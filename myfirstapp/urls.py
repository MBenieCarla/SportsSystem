from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    
    # Dashboard URLs
    path('dashboard/organiser/', views.tournament_organiser_dashboard, name='tournament_organiser_dashboard'),
    path('dashboard/player/', views.player_dashboard, name='player_dashboard'),
    path('dashboard/trainer/', views.trainer_dashboard, name='trainer_dashboard'),
    
    # Registration
    path('register/', views.registration_choice, name='registration_choice'),
    path('register/player/', views.player_registration, name='player_registration'),
    path('register/trainer/', views.trainer_registration, name='trainer_registration'),
    path('register/tournament-organiser/', views.tournament_organiser_registration, name='tournament_organiser_registration'),
    
    # Tournament Management
    path('tournament-schedule/', views.tournament_schedule, name='tournament_schedule'),
    path('manage-teams/', views.manage_teams, name='manage_teams'),
    path('manage-matches/', views.manage_matches, name='manage_matches'),
    path('tournaments/', views.tournament_list, name='tournament_list'),
    
    # Match Operations
    path('match/edit/<int:match_id>/', views.edit_match, name='edit_match'),
    path('match/delete/<int:match_id>/', views.delete_match, name='delete_match'),
    path('match/<int:match_id>/', views.match_detail, name='match_detail'),
    
    # Organiser
    path('organiser-details/', views.organiser_details, name='organiser_details'),
    path('reports/', views.reports, name='reports'),
    path('profile-settings/', views.profile_settings, name='profile_settings'),
    
    # Player
    path('player/profile/', views.player_profile, name='player_profile'),
    path('player/my-team/', views.my_team, name='my_team'),
    path('player/matches/', views.my_matches, name='my_matches'),
    path('player/standings/', views.team_standings, name='team_standings'),
    path('player/stats/', views.player_stats, name='player_stats'),
    path('player/settings/', views.player_settings, name='player_settings'),

    # Trainer
    path('trainer/profile/', views.trainer_profile, name='trainer_profile'),
    path('trainer/create-team/', views.create_team, name='create_team'),
    path('trainer/my-teams/', views.my_teams, name='my_teams'),
    path('trainer/schedule/', views.trainer_schedule, name='trainer_schedule'),
    path('trainer/performance/', views.team_performance, name='team_performance'),
    path('trainer/development/', views.player_development, name='player_development'),
    path('trainer/sessions/', views.training_sessions, name='training_sessions'),
    path('trainer/settings/', views.trainer_settings, name='trainer_settings'),

    path('chat/', views.chat_list, name='chat_list'),
    path('chat/start/', views.start_chat, name='start_chat'),
    path('chat/room/<int:room_id>/', views.chat_room, name='chat_room'),
    path('chat/delete/<int:room_id>/', views.delete_room, name='delete_room'),
    path('chat/add-participants/<int:room_id>/', views.add_participants, name='add_participants'),
    path('chat/get-new-messages/<int:room_id>/', views.get_new_messages, name='get_new_messages'),
    path('chat/get-unread-counts/', views.get_unread_counts, name='get_unread_counts'),
    
    path('trainer/join-requests/', views.join_requests, name='join_requests'),
    path('trainer/join-requests/accept/<int:request_id>/', views.accept_join_request, name='accept_join_request'),
    path('trainer/join-requests/decline/<int:request_id>/', views.decline_join_request, name='decline_join_request'),
    path('trainer/sessions/create/', views.create_training_session, name='create_training_session'),
    path('trainer/tournament/apply/', views.apply_tournament, name='apply_tournament'),
    path('trainer/tournament/applications/', views.tournament_applications, name='tournament_applications'),
    path('trainer/feedback/send/', views.send_player_feedback, name='send_player_feedback'),
    path('trainer/feedback/', views.player_feedback_list, name='player_feedback_list'),
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
]