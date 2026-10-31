# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Orbit: only workspace admins may create projects or bring new people into a workspace."""

from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    APIToken,
    Project,
    ProjectMember,
    ProjectMemberInvite,
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
