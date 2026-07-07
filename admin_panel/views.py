from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group, Permission
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, TemplateView
from django.db.models import Count, Q

from .models import AdminActionLog, Profile

User = get_user_model()


class AdminRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    raise_exception = True  # 403 instead of redirect to login if authenticated but unauthorized


# ---------------------------------------------------------------------------
# 0. Admin Dashboard
# ---------------------------------------------------------------------------

class AdminDashboardView(AdminRequiredMixin, TemplateView):
    """Admin dashboard with platform statistics and recent activity."""
    template_name = "dashboard.html"
    permission_required = "auth.change_user"  # Basic admin permission

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        users = User.objects.all()
        
        # Basic stats
        total_users = users.count()
        active_users = users.filter(is_active=True).count()
        pending_users = users.filter(is_active=False).count()
        total_admins = users.filter(is_superuser=True).count()
        
        # User type breakdown
        players = users.filter(user_type='player').count() if hasattr(User, 'user_type') else 0
        trainers = users.filter(user_type='trainer').count() if hasattr(User, 'user_type') else 0
        organizers = users.filter(user_type='organizer').count() if hasattr(User, 'user_type') else 0
        
        # Content stats - import models safely
        try:
            from core.models import Team
            total_teams = Team.objects.count()
        except ImportError:
            total_teams = 0
            
        try:
            from core.models import Tournament
            total_tournaments = Tournament.objects.count()
        except ImportError:
            total_tournaments = 0
            
        # Flagged content - if you have a flagging system
        flagged_content = 0
        try:
            from reports.models import ReportedContent
            flagged_content = ReportedContent.objects.filter(resolved=False).count()
        except ImportError:
            pass
        
        # Recent users (last 10)
        recent_users = users.select_related('profile').order_by('-date_joined')[:10]
        
        # Recent admin actions - FIXED: changed 'timestamp' to 'created_at'
        recent_actions = AdminActionLog.objects.select_related('actor', 'target_user').order_by('-created_at')[:10]
        
        context.update({
            # Stats
            'total_users': total_users,
            'active_users': active_users,
            'pending_users': pending_users,
            'total_admins': total_admins,
            'players': players,
            'trainers': trainers,
            'organizers': organizers,
            'total_teams': total_teams,
            'total_tournaments': total_tournaments,
            'flagged_content': flagged_content,
            
            # Recent items
            'recent_users': recent_users,
            'recent_actions': recent_actions,
            
            # Current date for display
            'current_date': timezone.now(),
        })
        
        return context


# ---------------------------------------------------------------------------
# 1. Deactivate users
# ---------------------------------------------------------------------------

class UserListView(AdminRequiredMixin, ListView):
    """Admin dashboard: list users with active/role status."""
    model = User
    template_name = "user_list.html"
    context_object_name = "users"
    permission_required = "auth.change_user"
    paginate_by = 25

    def get_queryset(self):
        qs = User.objects.all().select_related("profile").order_by("username")
        
        # Filter by user type if provided
        user_type = self.request.GET.get('user_type')
        if user_type and hasattr(User, 'user_type'):
            qs = qs.filter(user_type=user_type)
            
        # Filter by active status
        active_status = self.request.GET.get('active_status')
        if active_status == 'active':
            qs = qs.filter(is_active=True)
        elif active_status == 'inactive':
            qs = qs.filter(is_active=False)
            
        # Search by username or email
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(
                Q(username__icontains=search) | 
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
            
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add user type filter options
        context['user_type_choices'] = []
        if hasattr(User, 'USER_TYPE_CHOICES'):
            context['user_type_choices'] = User.USER_TYPE_CHOICES
        context['current_filters'] = self.request.GET.dict()
        
        # Add all groups for role assignment
        context['all_groups'] = Group.objects.all()
        return context


class UserDeactivateView(AdminRequiredMixin, View):
    permission_required = "auth.change_user"

    def post(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        reason = request.POST.get("reason", "")

        # Prevent self-deactivation
        if target == request.user:
            messages.error(request, "You cannot deactivate your own account.")
            return redirect("admin_panel:user_list")

        target.is_active = False
        target.save(update_fields=["is_active"])

        AdminActionLog.objects.create(
            actor=request.user,
            target_user=target,
            action=AdminActionLog.ActionType.DEACTIVATE_USER,
            reason=reason,
            request_ip=request.META.get('REMOTE_ADDR', ''),
        )
        messages.success(request, f"Deactivated user '{target.username}'.")
        return redirect("admin_panel:user_list")


class UserReactivateView(AdminRequiredMixin, View):
    permission_required = "auth.change_user"

    def post(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)

        target.is_active = True
        target.save(update_fields=["is_active"])

        AdminActionLog.objects.create(
            actor=request.user,
            target_user=target,
            action=AdminActionLog.ActionType.REACTIVATE_USER,
            request_ip=request.META.get('REMOTE_ADDR', ''),
        )
        messages.success(request, f"Reactivated user '{target.username}'.")
        return redirect("admin_panel:user_list")


# ---------------------------------------------------------------------------
# 2. Role-based access permissions (Django Groups + Permissions)
# ---------------------------------------------------------------------------

class RoleListView(AdminRequiredMixin, ListView):
    """List all roles (Groups) and the permissions attached to each."""
    model = Group
    template_name = "role_list.html"
    context_object_name = "roles"
    permission_required = "auth.change_group"

    def get_queryset(self):
        return Group.objects.prefetch_related("permissions").order_by("name")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Count users in each role
        for role in context['roles']:
            role.user_count = role.user_set.count()
        return context


class RoleCreateView(AdminRequiredMixin, View):
    """Create a new role (Group)."""
    permission_required = "auth.change_group"

    def get(self, request):
        all_permissions = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'codename')
        return render(request, "role_form.html", {
            'group': None,
            'all_permissions': all_permissions,
            'assigned_ids': set(),
            'is_create': True
        })

    def post(self, request):
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, "Role name is required.")
            return redirect("admin_panel:role_create")
        
        if Group.objects.filter(name=name).exists():
            messages.error(request, f"Role '{name}' already exists.")
            return redirect("admin_panel:role_create")
        
        group = Group.objects.create(name=name)
        permission_ids = request.POST.getlist("permissions")
        group.permissions.set(Permission.objects.filter(id__in=permission_ids))
        
        AdminActionLog.objects.create(
            actor=request.user,
            action=AdminActionLog.ActionType.ASSIGN_ROLE,
            reason=f"Created new role '{group.name}'",
            request_ip=request.META.get('REMOTE_ADDR', ''),
        )
        messages.success(request, f"Created role '{group.name}'.")
        return redirect("admin_panel:role_list")


class RoleDeleteView(AdminRequiredMixin, View):
    """Delete a role (Group)."""
    permission_required = "auth.change_group"

    def post(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id)
        group_name = group.name
        
        # Remove all users from this group first
        group.user_set.clear()
        group.delete()
        
        AdminActionLog.objects.create(
            actor=request.user,
            action=AdminActionLog.ActionType.REMOVE_ROLE,
            reason=f"Deleted role '{group_name}'",
            request_ip=request.META.get('REMOTE_ADDR', ''),
        )
        messages.success(request, f"Deleted role '{group_name}'.")
        return redirect("admin_panel:role_list")


class RolePermissionUpdateView(AdminRequiredMixin, View):
    """Set the full permission list for a role (Group)."""
    permission_required = "auth.change_group"

    def get(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id)
        all_permissions = Permission.objects.select_related("content_type").order_by(
            "content_type__app_label", "codename"
        )
        # Group permissions by app label for better display
        permissions_by_app = {}
        for perm in all_permissions:
            app_label = perm.content_type.app_label
            if app_label not in permissions_by_app:
                permissions_by_app[app_label] = []
            permissions_by_app[app_label].append(perm)
        
        return render(request, "role_form.html", {
            "group": group,
            "all_permissions": all_permissions,
            "permissions_by_app": permissions_by_app,
            "assigned_ids": set(group.permissions.values_list("id", flat=True)),
            "is_create": False
        })

    def post(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id)
        permission_ids = request.POST.getlist("permissions")

        group.permissions.set(Permission.objects.filter(id__in=permission_ids))

        AdminActionLog.objects.create(
            actor=request.user,
            target_user=None,
            action=AdminActionLog.ActionType.ASSIGN_ROLE,
            reason=f"Updated permissions for role '{group.name}'",
            request_ip=request.META.get('REMOTE_ADDR', ''),
        )
        messages.success(request, f"Updated permissions for role '{group.name}'.")
        return redirect("admin_panel:role_list")


class UserRoleAssignView(AdminRequiredMixin, View):
    """Assign or remove a user's membership in a role (Group)."""
    permission_required = "auth.change_user"

    def post(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        group_id = request.POST.get("group_id")
        action = request.POST.get("action")  # "add" or "remove"
        group = get_object_or_404(Group, pk=group_id)

        if action == "add":
            target.groups.add(group)
            log_action = AdminActionLog.ActionType.ASSIGN_ROLE
        else:
            target.groups.remove(group)
            log_action = AdminActionLog.ActionType.REMOVE_ROLE

        AdminActionLog.objects.create(
            actor=request.user,
            target_user=target,
            action=log_action,
            reason=f"Role '{group.name}'",
            request_ip=request.META.get('REMOTE_ADDR', ''),
        )
        messages.success(request, f"Updated roles for '{target.username}'.")
        return redirect("admin_panel:user_list")


# ---------------------------------------------------------------------------
# 3. Remove inappropriate content from profiles
# ---------------------------------------------------------------------------

class ProfileModerateView(AdminRequiredMixin, View):
    """Clear a single field or the whole profile."""
    permission_required = "admin_panel.change_profile"

    def post(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        profile, _ = Profile.objects.get_or_create(user=target)
        field = request.POST.get("field")  # "bio" | "display_name" | "avatar_url" | "all"
        reason = request.POST.get("reason", "")

        if field == "all":
            profile.clear_content(reason=reason)
            # Also clear any other sensitive fields
            profile.bio = ""
            profile.display_name = ""
            profile.avatar_url = ""
            profile.is_moderated = True
            profile.moderated_reason = f"Full profile cleared: {reason}"
            profile.moderated_at = timezone.now()
            profile.save()
        elif field in {"bio", "display_name", "avatar_url"}:
            setattr(profile, field, "")
            profile.is_moderated = True
            profile.moderated_reason = f"Field '{field}' cleared: {reason}"
            profile.moderated_at = timezone.now()
            profile.save()
        else:
            messages.error(request, "Unknown profile field.")
            return redirect("admin_panel:user_list")

        AdminActionLog.objects.create(
            actor=request.user,
            target_user=target,
            action=AdminActionLog.ActionType.MODERATE_PROFILE,
            reason=f"field={field}; {reason}",
            request_ip=request.META.get('REMOTE_ADDR', ''),
        )
        messages.success(request, f"Removed content from '{target.username}'s profile.")
        return redirect("admin_panel:user_list")


# ---------------------------------------------------------------------------
# 4. Audit log
# ---------------------------------------------------------------------------

class AuditLogView(AdminRequiredMixin, ListView):
    model = AdminActionLog
    template_name = "audit_log.html"
    context_object_name = "log_entries"
    permission_required = "admin_panel.view_adminactionlog"
    paginate_by = 50
    
    def get_queryset(self):
        qs = AdminActionLog.objects.select_related('actor', 'target_user')
        
        # Filter by action type
        action_type = self.request.GET.get('action_type')
        if action_type:
            qs = qs.filter(action=action_type)
            
        # Filter by actor
        actor_id = self.request.GET.get('actor_id')
        if actor_id:
            qs = qs.filter(actor_id=actor_id)
            
        # Search by reason
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(reason__icontains=search)
            
        # FIXED: Changed from 'timestamp' to 'created_at'
        return qs.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action_types'] = AdminActionLog.ActionType.choices
        context['current_filters'] = self.request.GET.dict()
        return context


# ---------------------------------------------------------------------------
# 5. User detail view (for viewing a single user)
# ---------------------------------------------------------------------------

class UserDetailView(AdminRequiredMixin, View):
    """View a single user's details and activity."""
    permission_required = "auth.change_user"

    def get(self, request, user_id):
        user = get_object_or_404(User.objects.select_related('profile'), pk=user_id)
        
        # Get user's groups
        groups = user.groups.all()
        
        # Get user's action history - FIXED: Changed from 'timestamp' to 'created_at'
        actions = AdminActionLog.objects.filter(
            Q(actor=user) | Q(target_user=user)
        ).select_related('actor', 'target_user').order_by('-created_at')[:20]
        
        context = {
            'target_user': user,
            'groups': groups,
            'actions': actions,
            'all_groups': Group.objects.all(),
        }
        return render(request, "user_detail.html", context)