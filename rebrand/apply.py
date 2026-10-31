"""Rebrand a clean Plane checkout as Orbit. Safe to re-run. Usage: python rebrand/apply.py"""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent

ORBIT_URL = "https://orbit.thesocialnexus.co.uk"
SOURCE_URL = "https://github.com/Faizy-broski/Orbit"

WORD = re.compile(r"\bPlane\b(?!\.so| Software)")
ARTICLE = re.compile(r"\b([Aa]) Orbit\b")
LOWER = re.compile(r"(?<![\w./@-])plane(?![\w./@-])")

SKIP_LINE = re.compile(
    r"Plane Software|^\s*import\s|^\s*(//|\*|/\*)|X-Plane|Let Plane collect|how you use Plane|based on Plane|Total number of users in the Plane"
)
SKIP_PATH = re.compile(
    r"\.stories\.|/\.storybook/|\.d\.ts$|/billing/|apps/web/core/components/license/|constants/src/payment\.ts$|node_modules|/build/"
)

FRONTEND = [
    ("apps/web", "*.ts"), ("apps/web", "*.tsx"), ("apps/web/public", "*.json"), ("apps/web/public", "*.webmanifest"),
    ("apps/web", "manifest.json"), ("apps/admin", "*.ts"), ("apps/admin", "*.tsx"), ("apps/admin/public", "*.json"),
    ("packages/constants/src", "*.ts"),
]
BACKEND = [
    ("apps/api/templates", "*.html"), ("apps/api/plane/bgtasks", "*.py"), ("apps/api/plane/seeds/data", "*.json"),
    ("apps/api/plane/license/api/views", "configuration.py"), ("apps/api/plane/license/utils", "instance_value.py"),
    ("apps/api/plane/license/management/commands", "register_instance.py"),
]

EMAIL_LOGOS = {
    "https://media.docs.plane.so/logo/new-logo-white.png": f"{ORBIT_URL}/orbit-email-white.png",
    "https://media.docs.plane.so/logo/new-logo-dark.png": f"{ORBIT_URL}/orbit-email-dark.png",
}
SOCIAL_LINK = re.compile(r"<a\b[^>]*>\s*<img\b[^>]*social-icons[^>]*>\s*</a>", re.S)
EARLY_STAGE_BLURB = re.compile(r"<p\b[^>]*>(?:(?!</p>).)*Despite our popularity(?:(?!</p>).)*</p>", re.S)
EMAIL_LINK = re.compile(
    r"https://(?:www\.)?(?:plane\.so/?|forum\.plane\.so|github\.com/makeplane(?:/plane(?:/pulls)?)?|"
    r"x\.com/planepowers|www\.linkedin\.com/company/planepowers/?)(?=[\"'])"
)

def admin_only(name, enum="EUserPermissions"):
    head = f"  const {name} = allowPermissions(\n"
    tail = "\n    EUserPermissionsLevel.WORKSPACE"
    return (f"{head}    [{enum}.ADMIN, {enum}.MEMBER],{tail}", f"{head}    [{enum}.ADMIN],{tail}")


CREATE_PROJECT_CONST = (
    "  const canCreateProject = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.WORKSPACE);\n"
)
ADMIN_DECORATOR = '    @allow_permission([ROLE.ADMIN], level="WORKSPACE")\n'

# The server rules are what enforce this; the web edits only keep the screens honest.
ADMIN_ONLY_EDITS = {
    "apps/api/plane/app/views/project/base.py": [
        ('    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")\n    def create(self, request, slug):',
         f"{ADMIN_DECORATOR}    def create(self, request, slug):"),
    ],
    "apps/api/plane/api/views/project.py": [
        ("from plane.app.permissions import ProjectBasePermission, WorkSpaceAdminPermission\n",
         "from plane.app.permissions import ROLE, ProjectBasePermission, WorkSpaceAdminPermission, allow_permission\n"),
        ('    )\n    def post(self, request, slug):\n        """Create project',
         f'    )\n{ADMIN_DECORATOR}    def post(self, request, slug):\n        """Create project'),
    ],
    "apps/api/plane/app/views/workspace/invite.py": [
        ("from plane.app.permissions import WorkSpaceAdminPermission\n",
         "from plane.app.permissions import ROLE, WorkSpaceAdminPermission, allow_permission\n"),
        ('    def create(self, request, slug):\n        emails = request.data.get("emails", [])',
         f'{ADMIN_DECORATOR}    def create(self, request, slug):\n        emails = request.data.get("emails", [])'),
        ("    def destroy(self, request, slug, pk):\n        workspace_member_invite =",
         f"{ADMIN_DECORATOR}    def destroy(self, request, slug, pk):\n        workspace_member_invite ="),
    ],
    # Accepting a project invite also adds the person to the workspace.
    "apps/api/plane/app/views/project/invite.py": [
        ("    @allow_permission([ROLE.ADMIN])\n    def create(self, request, slug, project_id):",
         f"{ADMIN_DECORATOR}    def create(self, request, slug, project_id):"),
    ],
    "apps/web/core/components/project/header.tsx": [admin_only("isAuthorizedUser")],
    "apps/web/core/components/project/card-list.tsx": [admin_only("canPerformEmptyStateActions")],
    "apps/web/core/components/workspace/sidebar/projects-list.tsx": [admin_only("isAuthorizedUser")],
    "apps/web/app/(all)/[workspaceSlug]/(projects)/extended-project-sidebar.tsx": [admin_only("isAuthorizedUser")],
    "apps/web/core/components/home/widgets/empty-states/no-projects.tsx": [admin_only("canCreateProject")],
    "apps/web/core/components/power-k/config/creation/command.ts": [admin_only("canCreateProject")],
    "apps/web/app/(all)/[workspaceSlug]/(projects)/analytics/[tabId]/page.tsx": [
        admin_only("canPerformEmptyStateActions")
    ],
    "apps/web/core/components/issues/workspace-draft/root.tsx": [
        admin_only("hasMemberLevelPermission", "EUserWorkspaceRoles")
    ],
    # hasMemberLevelPermission also guards creating work items here, so it stays as it is.
    "apps/web/core/components/issues/issue-layouts/empty-states/global-view.tsx": [
        ("  // derived values\n  const hasMemberLevelPermission",
         "  // derived values\n"
         "  const canCreateProject = allowPermissions([EUserWorkspaceRoles.ADMIN], EUserPermissionsLevel.WORKSPACE);\n"
         "  const hasMemberLevelPermission"),
        ("              toggleCreateProjectModal(true);\n            },\n            disabled: !hasMemberLevelPermission,",
         "              toggleCreateProjectModal(true);\n            },\n            disabled: !canCreateProject,"),
    ],
    "apps/web/app/(all)/[workspaceSlug]/(settings)/settings/projects/page.tsx": [
        ('import { PROJECT_TRACKER_ELEMENTS } from "@plane/constants";\n',
         'import { EUserPermissions, EUserPermissionsLevel, PROJECT_TRACKER_ELEMENTS } from "@plane/constants";\n'),
        ('import { useCommandPalette } from "@/hooks/store/use-command-palette";\n',
         'import { useCommandPalette } from "@/hooks/store/use-command-palette";\n'
         'import { useUserPermissions } from "@/hooks/store/user";\n'),
        ("  const { toggleCreateProjectModal } = useCommandPalette();\n",
         "  const { toggleCreateProjectModal } = useCommandPalette();\n"
         f"  const {{ allowPermissions }} = useUserPermissions();\n{CREATE_PROJECT_CONST}"),
        ("        <Button\n          onClick={() => toggleCreateProjectModal(true)}",
         "        <Button\n          disabled={!canCreateProject}\n          onClick={() => toggleCreateProjectModal(true)}"),
    ],
    "apps/web/core/components/onboarding/tour/root.tsx": [
        ('import { Button } from "@plane/propel/button";\n',
         'import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";\n'
         'import { Button } from "@plane/propel/button";\n'),
        ('import { useUser } from "@/hooks/store/user";\n', 'import { useUser, useUserPermissions } from "@/hooks/store/user";\n'),
        ("  const { data: currentUser } = useUser();\n",
         f"  const {{ data: currentUser }} = useUser();\n  const {{ allowPermissions }} = useUserPermissions();\n{CREATE_PROJECT_CONST}"),
        ("{currentStepIndex === TOUR_STEPS.length - 1 && (\n                  <Button",
         "{currentStepIndex === TOUR_STEPS.length - 1 && canCreateProject && (\n                  <Button"),
    ],
}

EXACT_EDITS = {
    **ADMIN_ONLY_EDITS,
    "apps/web/core/components/navigation/top-navigation-root.tsx": [
        ('import { StarUsOnGitHubLink } from "@/app/(all)/[workspaceSlug]/(projects)/star-us-link";\n', ""),
        ("        <StarUsOnGitHubLink />\n", ""),
    ],
    "apps/web/app/(all)/workspace-invitations/page.tsx": [
        ('import { Boxes, Share2, Star, User2 } from "lucide-react";', 'import { Boxes, User2 } from "lucide-react";'),
        ('              <EmptySpaceItem Icon={Star} title="Star us on GitHub" href="https://github.com/makeplane" />\n', ""),
        ('              <EmptySpaceItem\n                Icon={Share2}\n                title="Join our community of active creators"\n'
         '                href="https://forum.plane.so"\n              />\n', ""),
    ],
    "packages/constants/src/settings/workspace.ts": [('    WORKSPACE_SETTINGS["billing-and-plans"],\n', "")],
    "apps/web/core/components/workspace/sidebar/help-section/root.tsx": [
        ('import { useTranslation } from "@plane/i18n";\n',
         'import { ORBIT_SOURCE_URL } from "@plane/constants";\nimport { useTranslation } from "@plane/i18n";\n'),
        ('window.open("mailto:sales@plane.so", "_blank")', 'window.open(ORBIT_SOURCE_URL, "_blank", "noopener,noreferrer")'),
        ('{t("contact_sales")}', "Source code (based on Plane, AGPL-3.0)"),
    ],
    "packages/constants/src/endpoints.ts": [
        ('process.env.VITE_WEBSITE_URL || "https://plane.so"', f'process.env.VITE_WEBSITE_URL || "{ORBIT_URL}"'),
    ],
}
HOST_IMPORT = "from plane.utils.host import base_host\n"
PROJECT_HELPER = "add_workspace_members_to_project"
USER_HELPER = "add_user_to_workspace_projects"

# Every path that creates a project or activates a workspace member calls a helper in plane/utils/orbit_members.py.
AUTO_MEMBER_EDITS = {
    "apps/api/plane/app/views/project/base.py": [
        (HOST_IMPORT, f"{HOST_IMPORT}from plane.utils.orbit_members import {PROJECT_HELPER}\n"),
        ('            project = self.get_queryset().filter(pk=serializer.data["id"]).first()\n\n            # Create the model activity',
         f'            {PROJECT_HELPER}(serializer.instance)\n\n'
         '            project = self.get_queryset().filter(pk=serializer.data["id"]).first()\n\n            # Create the model activity'),
    ],
    "apps/api/plane/api/views/project.py": [
        (HOST_IMPORT, f"{HOST_IMPORT}from plane.utils.orbit_members import {PROJECT_HELPER}\n"),
        ("                    project = self.get_queryset().filter(pk=serializer.instance.id).first()\n",
         f"                    {PROJECT_HELPER}(serializer.instance)\n\n"
         "                    project = self.get_queryset().filter(pk=serializer.instance.id).first()\n"),
    ],
    "apps/api/plane/app/views/workspace/invite.py": [
        (HOST_IMPORT, f"{HOST_IMPORT}from plane.utils.orbit_members import {USER_HELPER}\n"),
        ("                    # Set the user last_workspace_id to the accepted workspace\n",
         f"                    {USER_HELPER}(workspace_invite.workspace_id, user.id)\n\n"
         "                    # Set the user last_workspace_id to the accepted workspace\n"),
        ("        # Delete joined workspace invites\n",
         "        for invitation in workspace_invitations:\n"
         f"            {USER_HELPER}(invitation.workspace_id, request.user.id)\n\n"
         "        # Delete joined workspace invites\n"),
    ],
    "apps/api/plane/authentication/utils/workspace_project_join.py": [
        ("from plane.utils.cache import invalidate_cache_directly\n",
         "from plane.utils.cache import invalidate_cache_directly\n"
         f"from plane.utils.orbit_members import {USER_HELPER}\n"),
        ("    # Delete all the invites\n",
         "    for invite in [*workspace_member_invites, *project_member_invites]:\n"
         f"        {USER_HELPER}(invite.workspace_id, user.id)\n\n"
         "    # Delete all the invites\n"),
    ],
}

KANBAN = "apps/web/core/components/issues/issue-layouts/kanban"

# Rename and add states from the board; the same rules as the States settings page apply.
BOARD_STATE_EDITS = {
    "apps/api/plane/app/views/state/base.py": [
        ("    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])\n    def partial_update(self, request, slug, project_id, pk):",
         "    @allow_permission([ROLE.ADMIN])\n    def partial_update(self, request, slug, project_id, pk):"),
    ],
    "apps/api/plane/api/views/state.py": [
        ("from plane.app.permissions import ProjectEntityPermission\n",
         "from plane.app.permissions import ROLE, ProjectEntityPermission, allow_permission\n"),
        ('    )\n    def post(self, request, slug, project_id):\n        """Create state',
         '    )\n    @allow_permission([ROLE.ADMIN])\n    def post(self, request, slug, project_id):\n        """Create state'),
        ('    )\n    def patch(self, request, slug, project_id, state_id):\n        """Update state',
         '    )\n    @allow_permission([ROLE.ADMIN])\n    def patch(self, request, slug, project_id, state_id):\n        """Update state'),
        ("    )\n    def delete(self, request, slug, project_id, state_id):",
         "    )\n    @allow_permission([ROLE.ADMIN])\n    def delete(self, request, slug, project_id, state_id):"),
    ],
    f"{KANBAN}/headers/group-by-card.tsx": [
        ('import { CreateUpdateEpicModal } from "@/components/epic-modal";\n',
         'import { CreateUpdateEpicModal } from "@/components/epic-modal";\n'
         'import { KanbanStateColumnMenu } from "./state-column-menu";\n'
         'import { KanbanColumnTitle } from "./state-column-title";\n'),
        ("        {!disableIssueCreation &&\n          (renderExistingIssueModal ? (",
         '        {group_by === "state" && !sub_group_by && !verticalAlignPosition && !isEpic && (\n'
         "          <KanbanStateColumnMenu stateId={column_id} />\n"
         "        )}\n\n"
         "        {!disableIssueCreation &&\n          (renderExistingIssueModal ? ("),
        ("    sub_group_by,\n    column_id,\n", "    sub_group_by,\n    group_by,\n    column_id,\n"),
        ("          <div\n"
         "            className={`line-clamp-1 inline-block truncate overflow-hidden font-medium text-primary ${\n"
         "              verticalAlignPosition ? `max-h-[400px] vertical-lr` : ``\n"
         "            }`}\n"
         "          >\n"
         "            {title}\n"
         "          </div>\n",
         "          <KanbanColumnTitle\n"
         "            stateId={column_id}\n"
         "            title={title}\n"
         '            canRename={group_by === "state" && !sub_group_by && !verticalAlignPosition && !isEpic}\n'
         "            className={`line-clamp-1 inline-block truncate overflow-hidden font-medium text-primary ${\n"
         "              verticalAlignPosition ? `max-h-[400px] vertical-lr` : ``\n"
         "            }`}\n"
         "          />\n"),
    ],
    f"{KANBAN}/default.tsx": [
        ('import { HeaderGroupByCard } from "./headers/group-by-card";\n',
         'import { KanbanAddStateColumn } from "./headers/add-state-column";\n'
         'import { HeaderGroupByCard } from "./headers/group-by-card";\n'),
        ("          );\n        })}\n    </ContentWrapper>",
         "          );\n        })}\n"
         '      {group_by === "state" && sub_group_by === null && !isEpic && !isWorkspaceLevel(storeType) && (\n'
         "        <KanbanAddStateColumn />\n      )}\n"
         "    </ContentWrapper>"),
    ],
}

SOURCE_EXPORT = f'\nexport const ORBIT_SOURCE_URL = "{SOURCE_URL}";\n'


def swap_line(line, lower=False):
    if SKIP_LINE.search(line):
        return line
    line = WORD.sub("Orbit", line)
    line = LOWER.sub("Orbit", line) if lower else line
    return ARTICLE.sub(r"\1n Orbit", line)


def swap_text(path, lower=False):
    text = path.read_text(encoding="utf-8", newline="")
    new = "".join(swap_line(l, lower) for l in text.splitlines(keepends=True))
    if path.suffix == ".html":
        for old, logo in EMAIL_LOGOS.items():
            new = new.replace(old, logo)
        new = new.replace("Plane Software, Inc.", "Orbit").replace('title="@planepowers"', 'title="Orbit"')
        new = SOCIAL_LINK.sub("", new)
        new = EARLY_STAGE_BLURB.sub("", new)
        new = EMAIL_LINK.sub(ORBIT_URL, new)
    if new != text:
        path.write_text(new, encoding="utf-8", newline="")
        return 1
    return 0


def swap_json_values(node):
    if isinstance(node, str):
        if "Let Plane collect" in node:
            return node
        return ARTICLE.sub(r"\1n Orbit", LOWER.sub("Orbit", WORD.sub("Orbit", node)))
    if isinstance(node, dict):
        return {k: swap_json_values(v) for k, v in node.items()}
    if isinstance(node, list):
        return [swap_json_values(v) for v in node]
    return node


def rebrand_i18n():
    count = 0
    for path in sorted((ROOT / "packages/i18n/src/locales/en").glob("*.json")):
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        new = swap_json_values(data)
        if new != data:
            indent = 2 if raw.startswith('{\n  "') else 4
            path.write_text(json.dumps(new, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8", newline="\n")
            count += 1
    return count


def copy_tree(src):
    n = 0
    for f in src.rglob("*"):
        if f.is_file():
            dest = ROOT / f.relative_to(src)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, dest)
            n += 1
    return n


def main():
    changed = 0
    for base, pattern in FRONTEND + BACKEND:
        for path in sorted((ROOT / base).rglob(pattern)):
            rel = path.relative_to(ROOT).as_posix()
            if path.is_file() and not SKIP_PATH.search(rel):
                changed += swap_text(path, lower=base.startswith("apps/web") and "onboarding" in rel)

    i18n = rebrand_i18n()
    copied = copy_tree(HERE / "assets") + copy_tree(HERE / "overrides")

    for rel, edits in [*EXACT_EDITS.items(), *AUTO_MEMBER_EDITS.items(), *BOARD_STATE_EDITS.items()]:
        path = ROOT / rel
        text = path.read_text(encoding="utf-8", newline="").replace("\r\n", "\n")
        for old, new in edits:
            if new and new in text:
                continue
            if old in text:
                text = text.replace(old, new)
            elif new:
                raise SystemExit(f"Upstream changed {rel}: cannot find {old!r}")
        path.write_text(text, encoding="utf-8", newline="")

    endpoints = ROOT / "packages/constants/src/endpoints.ts"
    text = endpoints.read_text(encoding="utf-8", newline="")
    text = re.sub(r'\nexport const ORBIT_SOURCE_URL = ".*";\n', "", text)
    endpoints.write_text(text.rstrip("\n") + "\n" + SOURCE_EXPORT, encoding="utf-8", newline="")

    print(f"text files: {changed}, i18n files: {i18n}, assets/overrides: {copied}")


if __name__ == "__main__":
    main()
