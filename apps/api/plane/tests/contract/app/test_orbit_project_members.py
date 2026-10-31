# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Orbit: workspace admins and members belong to every project automatically."""

from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APIClient

from plane.authentication.utils.workspace_project_join import process_workspace_project_invitations
from plane.db.models import (
    APIToken,
    Project,
    ProjectMember,
    ProjectUserProperty,
    User,
    WorkspaceMember,
    WorkspaceMemberInvite,
)
from plane.utils.orbit_members import add_user_to_workspace_projects

ADMIN, MEMBER, GUEST = 20, 15, 5


def _user(email, **kwargs):
    return User.objects.create(email=email, username=email.split("@")[0], **kwargs)


def _join(workspace, email, role, **kwargs):
    user = _user(email, **kwargs)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role, is_active=True)
    return user


def _is_member(project, user):
    return ProjectMember.objects.filter(project=project, member=user, is_active=True).exists()


@pytest.fixture
def project(workspace, create_user):
    project = Project.objects.create(name="Team", identifier="TEAM", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=ADMIN)
    return project


@pytest.mark.contract
@pytest.mark.django_db
class TestNewProjectIncludesEveryone:
    def _assert_membership(self, project, member, second_admin, guest, bot):
        assert ProjectMember.objects.get(project=project, member=member).role == MEMBER
        assert ProjectMember.objects.get(project=project, member=second_admin).role == ADMIN
        assert ProjectUserProperty.objects.filter(project=project, user=member).exists()
        assert not _is_member(project, guest)
        assert not _is_member(project, bot)

    def _people(self, workspace):
        return (
            _join(workspace, "member@orbit.test", MEMBER),
            _join(workspace, "admin2@orbit.test", ADMIN),
            _join(workspace, "guest@orbit.test", GUEST),
            _join(workspace, "bot@orbit.test", MEMBER, is_bot=True),
        )

    def test_app_create(self, workspace, session_client):
        people = self._people(workspace)
        response = session_client.post(
            f"/api/workspaces/{workspace.slug}/projects/", {"name": "New", "identifier": "NEW"}, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        self._assert_membership(Project.objects.get(identifier="NEW"), *people)

    def test_api_token_create(self, workspace, create_user):
        people = self._people(workspace)
        token = APIToken.objects.create(user=create_user, label="admin token", token="orbit-admin-token")
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=token.token)
        response = client.post(
            f"/api/v1/workspaces/{workspace.slug}/projects/", {"name": "New", "identifier": "NEW"}, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        self._assert_membership(Project.objects.get(identifier="NEW"), *people)


@pytest.mark.contract
@pytest.mark.django_db
class TestJoiningWorkspaceAddsToProjects:
    def test_accepting_invite_in_app(self, workspace, project):
        user = _user("joiner@orbit.test")
        invite = WorkspaceMemberInvite.objects.create(workspace=workspace, email=user.email, role=MEMBER, accepted=True)
        client = APIClient()
        client.force_authenticate(user=user)
        with patch("plane.app.views.workspace.invite.track_event.delay"):
            response = client.post("/api/users/me/workspaces/invitations/", {"invitations": [str(invite.id)]}, format="json")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert _is_member(project, user)

    def test_invite_processed_at_sign_in(self, workspace, project):
        user = _user("signin@orbit.test")
        WorkspaceMemberInvite.objects.create(workspace=workspace, email=user.email, role=MEMBER, accepted=True)
        with patch("plane.authentication.utils.workspace_project_join.track_event.delay"):
            process_workspace_project_invitations(user)
        assert _is_member(project, user)

    def test_guest_is_not_added(self, workspace, project):
        guest = _join(workspace, "guest@orbit.test", GUEST)
        assert add_user_to_workspace_projects(workspace.id, guest.id) == 0
        assert not _is_member(project, guest)

    def test_rejoining_restores_access(self, workspace, project):
        user = _join(workspace, "back@orbit.test", MEMBER)
        ProjectMember.objects.create(project=project, member=user, role=MEMBER, is_active=False)
        add_user_to_workspace_projects(workspace.id, user.id)
        assert _is_member(project, user)

    def test_archived_project_is_skipped(self, workspace, project):
        from django.utils import timezone

        Project.objects.filter(pk=project.pk).update(archived_at=timezone.now())
        user = _join(workspace, "new@orbit.test", MEMBER)
        add_user_to_workspace_projects(workspace.id, user.id)
        assert not _is_member(project, user)


@pytest.mark.contract
@pytest.mark.django_db
class TestBoardIsTheDefaultLayout:
    def test_new_project_view_opens_on_board(self, workspace, project, session_client):
        ProjectUserProperty.objects.filter(project=project).delete()
        response = session_client.get(f"/api/workspaces/{workspace.slug}/projects/{project.id}/user-properties/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["display_filters"]["layout"] == "kanban"
        assert response.data["display_filters"]["group_by"] == "state"

    def test_command_switches_list_views_only(self, workspace, project, create_user):
        ProjectUserProperty.objects.filter(project=project, user=create_user).update(
            display_filters={"layout": "list", "group_by": None, "order_by": "-created_at"}
        )
        calendar_user = _join(workspace, "calendar@orbit.test", MEMBER)
        ProjectMember.objects.create(project=project, member=calendar_user, role=MEMBER)
        ProjectUserProperty.objects.filter(project=project, user=calendar_user).update(
            display_filters={"layout": "calendar", "group_by": None}
        )

        call_command("orbit_default_board_layout", stdout=StringIO())

        switched = ProjectUserProperty.objects.get(project=project, user=create_user).display_filters
        assert switched["layout"] == "kanban"
        assert switched["group_by"] == "state"
        assert switched["order_by"] == "-created_at"
        untouched = ProjectUserProperty.objects.get(project=project, user=calendar_user).display_filters
        assert untouched["layout"] == "calendar"


@pytest.mark.contract
@pytest.mark.django_db
class TestBackfillCommand:
    def test_adds_existing_staff_and_keeps_removals(self, workspace, project):
        staff = _join(workspace, "staff@orbit.test", MEMBER)
        removed = _join(workspace, "removed@orbit.test", MEMBER)
        ProjectMember.objects.create(project=project, member=removed, role=MEMBER, is_active=False)

        call_command("orbit_sync_project_members", stdout=StringIO())
        call_command("orbit_sync_project_members", stdout=StringIO())

        assert _is_member(project, staff)
        assert ProjectMember.objects.filter(project=project, member=staff).count() == 1
        assert not _is_member(project, removed)
