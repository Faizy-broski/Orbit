# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Orbit: only workspace admins may create projects or bring new people into a workspace."""

from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    APIToken,
    Issue,
    Project,
    ProjectMember,
    ProjectMemberInvite,
    State,
    User,
    WorkspaceMember,
    WorkspaceMemberInvite,
)

ADMIN, MEMBER, GUEST = 20, 15, 5


def _user_in_workspace(workspace, email, role):
    user = User.objects.create(email=email, username=email.split("@")[0])
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role, is_active=True)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def member(workspace):
    return _user_in_workspace(workspace, "member@orbit.test", MEMBER)


@pytest.fixture
def project(workspace, create_user):
    project = Project.objects.create(name="Team", identifier="TEAM", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(workspace=workspace, project=project, member=create_user, role=ADMIN)
    return project


@pytest.mark.contract
@pytest.mark.django_db
class TestBoardStatesAreProjectAdminOnly:
    @pytest.fixture
    def state(self, workspace, project):
        return State.objects.create(name="Todo", group="unstarted", color="#000000", project=project, workspace=workspace)

    def _project_member(self, workspace, project, role):
        user = _user_in_workspace(workspace, "state-user@orbit.test", MEMBER)
        ProjectMember.objects.create(workspace=workspace, project=project, member=user, role=role)
        return user

    def test_member_cannot_rename_in_app(self, workspace, project, state):
        client = _client(self._project_member(workspace, project, MEMBER))
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/states/{state.id}/"
        assert client.patch(url, {"name": "Ready"}, format="json").status_code == status.HTTP_403_FORBIDDEN
        state.refresh_from_db()
        assert state.name == "Todo"

    def test_project_admin_can_rename_and_add_in_app(self, workspace, project, state):
        client = _client(self._project_member(workspace, project, ADMIN))
        base = f"/api/workspaces/{workspace.slug}/projects/{project.id}/states/"
        assert client.patch(f"{base}{state.id}/", {"name": "Ready"}, format="json").status_code == status.HTTP_200_OK
        payload = {"name": "In Review", "group": "started", "color": "#f59e0b"}
        assert client.post(base, payload, format="json").status_code == status.HTTP_200_OK
        state.refresh_from_db()
        assert state.name == "Ready"
        assert State.objects.filter(project=project, name="In Review", group="started").exists()

    def test_project_admin_can_reorder_and_delete_empty_state(self, workspace, project, state):
        client = _client(self._project_member(workspace, project, ADMIN))
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/states/{state.id}/"
        assert client.patch(url, {"sequence": 12345.5}, format="json").status_code == status.HTTP_200_OK
        state.refresh_from_db()
        assert state.sequence == 12345.5
        assert client.delete(url).status_code == status.HTTP_204_NO_CONTENT
        assert not State.objects.filter(pk=state.pk).exists()

    def test_state_with_work_items_cannot_be_deleted(self, workspace, project, state):
        Issue.objects.create(name="Keep me", project=project, workspace=workspace, state=state)
        client = _client(self._project_member(workspace, project, ADMIN))
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/states/{state.id}/"
        assert client.delete(url).status_code == status.HTTP_400_BAD_REQUEST
        assert State.objects.filter(pk=state.pk).exists()

    def test_member_cannot_delete_state(self, workspace, project, state):
        user = self._project_member(workspace, project, MEMBER)
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/states/{state.id}/"
        assert _client(user).delete(url).status_code == status.HTTP_403_FORBIDDEN
        token = APIToken.objects.create(user=user, label="member token", token="orbit-delete-token")
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=token.token)
        v1_url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/states/{state.id}/"
        assert client.delete(v1_url).status_code == status.HTTP_403_FORBIDDEN
        assert State.objects.filter(pk=state.pk).exists()

    def test_member_cannot_change_states_with_api_token(self, workspace, project, state):
        user = self._project_member(workspace, project, MEMBER)
        token = APIToken.objects.create(user=user, label="member token", token="orbit-state-token")
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=token.token)
        base = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/states/"
        assert client.patch(f"{base}{state.id}/", {"name": "Ready"}, format="json").status_code == status.HTTP_403_FORBIDDEN
        payload = {"name": "In Review", "group": "started", "color": "#f59e0b"}
        assert client.post(base, payload, format="json").status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.contract
@pytest.mark.django_db
class TestBoardColumnOrder:
    @pytest.fixture
    def states(self, workspace, project):
        rows = [("Backlog", "backlog"), ("Todo", "unstarted"), ("Doing", "started"), ("Done", "completed")]
        for position, (name, group) in enumerate(rows, start=1):
            state = State.objects.create(name=name, group=group, color="#000000", project=project, workspace=workspace)
            State.objects.filter(pk=state.pk).update(sequence=position * 15000)
        return {state.name: state for state in State.objects.filter(project=project)}

    def _board(self, project):
        return list(State.objects.filter(project=project).order_by("sequence").values_list("name", flat=True))

    def test_new_state_lands_after_its_own_group(self, workspace, project, states):
        State.objects.create(name="Review", group="started", color="#000000", project=project, workspace=workspace)
        assert self._board(project) == ["Backlog", "Todo", "Doing", "Review", "Done"]

    def test_new_state_in_empty_group_follows_earlier_groups(self, workspace, project, states):
        State.objects.create(name="Dropped", group="cancelled", color="#000000", project=project, workspace=workspace)
        assert self._board(project) == ["Backlog", "Todo", "Doing", "Done", "Dropped"]

    def test_move_across_groups_keeps_group(self, workspace, session_client, project, states):
        ProjectMember.objects.filter(project=project).update(role=ADMIN)
        todo = states["Todo"]
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/states/{todo.id}/"
        assert session_client.patch(url, {"sequence": 70000}, format="json").status_code == status.HTTP_200_OK
        todo.refresh_from_db()
        assert todo.group == "unstarted"
        assert self._board(project) == ["Backlog", "Doing", "Done", "Todo"]

    def test_new_project_gets_the_orbit_columns_in_order(self, workspace, session_client):
        response = session_client.post(
            f"/api/workspaces/{workspace.slug}/projects/", {"name": "Fresh", "identifier": "FRESH"}, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        project = Project.objects.get(identifier="FRESH")
        assert self._board(project) == [
            "Todo", "Bugs", "In Progress", "Under Deployment", "QA", "Done", "Blocked", "Credentials",
        ]
        assert State.objects.get(project=project, default=True).name == "Todo"

    def test_normalize_command_restores_group_order(self, project, states):
        State.objects.filter(pk=states["Todo"].pk).update(sequence=99000)
        call_command("orbit_normalize_board_order", stdout=StringIO())
        assert self._board(project) == ["Backlog", "Todo", "Doing", "Done"]


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectCreationIsAdminOnly:
    payload = {"name": "New", "identifier": "NEW"}

    @pytest.mark.parametrize("role", [MEMBER, GUEST])
    def test_non_admin_cannot_create_in_app(self, workspace, role):
        user = _user_in_workspace(workspace, "user@orbit.test", role)
        response = _client(user).post(f"/api/workspaces/{workspace.slug}/projects/", self.payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not Project.objects.filter(identifier="NEW").exists()

    def test_member_cannot_create_with_api_token(self, workspace, member):
        token = APIToken.objects.create(user=member, label="member token", token="orbit-member-token")
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=token.token)
        response = client.post(f"/api/v1/workspaces/{workspace.slug}/projects/", self.payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not Project.objects.filter(identifier="NEW").exists()

    def test_admin_can_create(self, workspace, session_client):
        response = session_client.post(f"/api/workspaces/{workspace.slug}/projects/", self.payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.contract
@pytest.mark.django_db
class TestInvitesAreAdminOnly:
    payload = {"emails": [{"email": "outsider@example.com", "role": MEMBER}]}

    def test_member_cannot_invite_to_workspace(self, workspace, member):
        response = _client(member).post(f"/api/workspaces/{workspace.slug}/invitations/", self.payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not WorkspaceMemberInvite.objects.filter(email="outsider@example.com").exists()

    def test_member_cannot_cancel_invite(self, workspace, member):
        invite = WorkspaceMemberInvite.objects.create(workspace=workspace, email="pending@example.com", role=MEMBER)
        response = _client(member).delete(f"/api/workspaces/{workspace.slug}/invitations/{invite.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert WorkspaceMemberInvite.objects.filter(pk=invite.pk).exists()

    @patch("plane.app.views.workspace.invite.track_event.delay")
    @patch("plane.app.views.workspace.invite.workspace_invitation.delay")
    def test_admin_can_invite_to_workspace(self, _send, _track, workspace, session_client):
        response = session_client.post(f"/api/workspaces/{workspace.slug}/invitations/", self.payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert WorkspaceMemberInvite.objects.filter(email="outsider@example.com").exists()

    def test_project_admin_cannot_email_outsiders(self, workspace, project, member):
        """Accepting a project invite adds the person to the workspace, so it must not bypass the rule above."""
        ProjectMember.objects.create(workspace=workspace, project=project, member=member, role=ADMIN)
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/invitations/"
        response = _client(member).post(url, self.payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not ProjectMemberInvite.objects.filter(email="outsider@example.com").exists()

    def test_project_admin_can_still_add_existing_staff(self, workspace, project, member):
        colleague = _user_in_workspace(workspace, "colleague@orbit.test", MEMBER)
        ProjectMember.objects.create(workspace=workspace, project=project, member=member, role=ADMIN)
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/members/"
        payload = {"members": [{"member_id": str(colleague.id), "role": MEMBER}]}
        response = _client(member).post(url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert ProjectMember.objects.filter(project=project, member=colleague, is_active=True).exists()
