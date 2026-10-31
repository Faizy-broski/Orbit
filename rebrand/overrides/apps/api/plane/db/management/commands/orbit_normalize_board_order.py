# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.core.management.base import BaseCommand

from plane.db.models import Project, State

GROUPS = ["backlog", "unstarted", "started", "completed", "cancelled"]


class Command(BaseCommand):
    help = (
        "Run ONCE when enabling free board column order: it keeps today's left-to-right order. "
        "Running it later resets columns people have moved back into group order."
    )

    def handle(self, *args, **options):
        updated = 0
        for project in Project.objects.all():
            states = sorted(
                State.objects.filter(project=project),
                key=lambda state: (GROUPS.index(state.group), state.sequence),
            )
            for position, state in enumerate(states, start=1):
                sequence = position * 15000
                if state.sequence != sequence:
                    State.objects.filter(pk=state.pk).update(sequence=sequence)
                    updated += 1
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} states"))
