# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.core.management.base import BaseCommand

from plane.db.models import WorkspaceMember
from plane.utils.orbit_members import add_user_to_workspace_projects


class Command(BaseCommand):
    help = "Add existing workspace admins and members to all projects. Safe to run more than once."

    def handle(self, *args, **options):
        total = 0
        workspace_members = WorkspaceMember.objects.filter(is_active=True, role__gte=15, member__is_bot=False)
        for workspace_member in workspace_members:
            total += add_user_to_workspace_projects(
                workspace_member.workspace_id, workspace_member.member_id, reactivate=False
            )
        self.stdout.write(self.style.SUCCESS(f"Added {total} project memberships"))
