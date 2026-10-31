# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.core.management.base import BaseCommand

from plane.db.models import ProjectUserProperty


class Command(BaseCommand):
    help = (
        "Run ONCE: switch existing project views from List to Board. "
        "Running it later also switches people who have since chosen List."
    )

    def handle(self, *args, **options):
        updated = 0
        for properties in ProjectUserProperty.objects.filter(display_filters__layout="list"):
            properties.display_filters["layout"] = "kanban"
            properties.display_filters["group_by"] = properties.display_filters.get("group_by") or "state"
            properties.save(update_fields=["display_filters"])
            updated += 1
        self.stdout.write(self.style.SUCCESS(f"Switched {updated} project views to Board"))
