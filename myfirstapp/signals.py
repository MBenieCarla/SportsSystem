from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Player, Team

@receiver(post_save, sender=Player)
def update_team_members_on_save(sender, instance, **kwargs):
    """Update team member count when a player is saved"""
    if instance.team:
        instance.team.current_members = instance.team.players.count()
        instance.team.save()

@receiver(post_delete, sender=Player)
def update_team_members_on_delete(sender, instance, **kwargs):
    """Update team member count when a player is deleted"""
    if instance.team:
        instance.team.current_members = instance.team.players.count()
        instance.team.save()