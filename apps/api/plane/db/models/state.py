# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import models
from django.template.defaultfilters import slugify
from django.db.models import Q

# Module imports
from .project import ProjectBaseModel
from plane.db.mixins import SoftDeletionManager

class StateGroup(models.TextChoices):
    BACKLOG = "backlog", "Backlog"
    UNSTARTED = "unstarted", "Unstarted"
    STARTED = "started", "Started"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    TRIAGE = "triage", "Triage"


# Default states
DEFAULT_STATES = [
    # Orbit's standard board, left to right. Board order is the sequence, not the group.
    {
        "name": "Todo",
        "color": "#60646C",
        "sequence": 15000,
        "group": StateGroup.UNSTARTED.value,
        "default": True,
    },
    {
        "name": "Bugs",
        "color": "#E5484D",
        "sequence": 30000,
        "group": StateGroup.UNSTARTED.value,
    },
    {
        "name": "In Progress",
        "color": "#F59E0B",
        "sequence": 45000,
        "group": StateGroup.STARTED.value,
    },
    {
        "name": "Under Deployment",
        "color": "#8E4EC6",
        "sequence": 60000,
        "group": StateGroup.STARTED.value,
    },
    {
        "name": "QA",
        "color": "#3E63DD",
        "sequence": 75000,
        "group": StateGroup.STARTED.value,
    },
    {
        "name": "Done",
        "color": "#46A758",
        "sequence": 90000,
        "group": StateGroup.COMPLETED.value,
    },
    {
        "name": "Blocked",
        "color": "#DC2626",
        "sequence": 105000,
        "group": StateGroup.STARTED.value,
    },
    {
        "name": "Credentials",
        "color": "#9AA4BC",
        "sequence": 120000,
        "group": StateGroup.BACKLOG.value,
    },
    {
        "name": "Triage",
        "color": "#4E5355",
        "sequence": 65000,
        "group": StateGroup.TRIAGE.value,
    },
]


class StateManager(SoftDeletionManager):
    """Default manager - excludes triage states"""

    def get_queryset(self):
        return super().get_queryset().exclude(group=StateGroup.TRIAGE.value)


class TriageStateManager(SoftDeletionManager):
    """Manager for triage states only"""

    def get_queryset(self):
        return super().get_queryset().filter(group=StateGroup.TRIAGE.value)


class State(ProjectBaseModel):
    name = models.CharField(max_length=255, verbose_name="State Name")
    description = models.TextField(verbose_name="State Description", blank=True)
    color = models.CharField(max_length=255, verbose_name="State Color")
    slug = models.SlugField(max_length=100, blank=True)
    sequence = models.FloatField(default=65535)
    group = models.CharField(
        choices=StateGroup.choices,
        default=StateGroup.BACKLOG,
        max_length=20,
    )
    is_triage = models.BooleanField(default=False)
    default = models.BooleanField(default=False)
    external_source = models.CharField(max_length=255, null=True, blank=True)
    external_id = models.CharField(max_length=255, blank=True, null=True)

    objects = StateManager()
    all_state_objects = models.Manager()
    triage_objects = TriageStateManager()

    def __str__(self):
        """Return name of the state"""
        return f"{self.name} <{self.project.name}>"

    class Meta:
        unique_together = ["name", "project", "deleted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "project"],
                condition=Q(deleted_at__isnull=True),
                name="state_unique_name_project_when_deleted_at_null",
            )
        ]
        verbose_name = "State"
        verbose_name_plural = "States"
        db_table = "states"
        ordering = ("sequence",)

    def _orbit_board_sequence(self):
        """Board columns sort by sequence alone, so place a new state after its group."""
        sequences = list(
            State.objects.filter(project=self.project).order_by("sequence").values_list("group", "sequence")
        )
        if not sequences:
            return self.sequence
        groups = [group.value for group in StateGroup if group != StateGroup.TRIAGE]
        if self.group not in groups:
            return sequences[-1][1] + 15000
        same_group = [sequence for group, sequence in sequences if group == self.group]
        earlier = groups[: groups.index(self.group)]
        anchors = same_group or [sequence for group, sequence in sequences if group in earlier]
        if not anchors:
            return sequences[0][1] - 15000
        anchor = max(anchors)
        following = [sequence for _, sequence in sequences if sequence > anchor]
        return (anchor + following[0]) / 2 if following else anchor + 15000

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        if self._state.adding:
            self.sequence = self._orbit_board_sequence()

        return super().save(*args, **kwargs)
