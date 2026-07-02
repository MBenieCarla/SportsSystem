from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # ==================== HOME ====================
    path('', views.home_view, name='home'),
    
    
    # ==================== PLAYER URLS ====================
    path('player/my-team/', views.my_team_view, name='my_team'),
    path('player/tournaments/', views.player_tournaments_view, name='player_tournaments'),
    path('player/tournament-schedule/', views.player_tournament_schedule_view, name='player_tournament_schedule'),
    path('player/trainings/', views.player_trainings_view, name='player_trainings'),
    path('player/feedback/', views.player_feedback_view, name='player_feedback'),
    
    
    # ==================== TRAINER URLS ====================
    path('trainer/create-training/', views.create_training_view, name='create_training'),
    path('trainer/manage-teams/', views.manage_teams_view, name='manage_teams'),
    path('trainer/manage-join-requests/', views.manage_join_requests_view, name='manage_join_requests'),
    path('trainer/training-sessions/', views.trainer_trainings_view, name='trainer_trainings'),
    path('trainer/training/<int:pk>/edit/', views.edit_training_view, name='edit_training'),
    path('trainer/training/<int:pk>/delete/', views.delete_training_view, name='delete_training'),
    
    
    # ==================== MATCH SCHEDULE (Shared) ====================
    path('match-schedule/', views.match_schedule_view, name='match_schedule'),
    
    
    # ==================== CHAT URLS ====================
    path('chat/', views.chat_list_view, name='chat_list'),
    path('chat/<int:room_id>/', views.chat_room_view, name='chat_room'),
    path('chat/create/', views.create_chat_room_view, name='create_chat_room'),
    path('chat/unread-count/', views.get_unread_count_view, name='unread_count'),
    path('chat/send-ajax/', views.send_message_ajax_view, name='send_message_ajax'),

    path('organizer/create-tournament/', views.create_tournament, name='create_tournament'),
    path('organizer/manage-tournaments/', views.manage_tournaments, name='manage_tournaments'),
    path('organizer/tournament-requests/', views.tournament_requests, name='tournament_requests'),
    path('organizer/update-scores/', views.update_match_scores, name='update_match_scores'),

    # Add these URLs
path('trainer/tournaments/', views.tournament_list_for_trainer, name='tournament_list_for_trainer'),
path('trainer/apply/<int:tournament_id>/', views.apply_to_tournament, name='apply_to_tournament'),
path('organizer/applications/<int:tournament_id>/', views.manage_tournament_applications, name='manage_tournament_applications'),
path('tournament-schedule/', views.tournament_schedule_view, name='tournament_schedule'),
]