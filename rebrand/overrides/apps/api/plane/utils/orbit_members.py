# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Orbit: every workspace admin and member belongs to every project in the workspace.

Guests and bots are left out. ProjectMember rows are created because permissions and
assignee checks across the app depend on them. Members are added one at a time since
ProjectMember.save() also creates the ProjectUserProperty row that bulk_create would skip.
"""

from plane.db.models import Project, ProjectMember, WorkspaceMember

ADMIN, MEMBER = 20, 15


def _project_role(workspace_role):
    return ADMIN if workspace_role == ADMIN else MEMBER


def add_workspace_members_to_project(project):
    existing = ProjectMember.objects.filter(project=project).values_list("member_id", flat=True)
    workspace_members = (
        WorkspaceMember.objects.filter(
            workspace_id=project.workspace_id,
            is_active=True,
            role__gte=MEMBER,
            member__is_bot=False,
        )
        .exclude(member_id__in=list(existing))
        .select_related("member")
    )
    for workspace_member in workspace_members:
        ProjectMember.objects.create(
            project=project,
            member=workspace_member.member,
            role=_project_role(workspace_member.role),
        )


def add_user_to_workspace_projects(workspace_id, user_id, reactivate=True):
    """Returns how many projects the user gained. reactivate=False respects earlier removals."""
    workspace_member = (
        WorkspaceMember.objects.filter(
            workspace_id=workspace_id,
            member_id=user_id,
            is_active=True,
            role__gte=MEMBER,
            member__is_bot=False,
        )
        .select_related("member")
        .first()
    )
    if workspace_member is None:
        return 0

    role = _project_role(workspace_member.role)
    memberships = {
        membership.project_id: membership
        for membership in ProjectMember.objects.filter(workspace_id=workspace_id, member_id=user_id)
    }
    added = 0
    for project in Project.objects.filter(workspace_id=workspace_id, archived_at__isnull=True):
        membership = memberships.get(project.id)
        if membership is None:
            ProjectMember.objects.create(project=project, member=workspace_member.member, role=role)
            added += 1
        elif reactivate and not membership.is_active:
            membership.is_active = True
            membership.role = role
            membership.save()
            added += 1
    return added
