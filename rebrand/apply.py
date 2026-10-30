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
    r"Plane Software|^\s*import\s|^\s*(//|\*|/\*)|X-Plane|Let Plane collect|how you use Plane|Total number of users in the Plane"
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

EXACT_EDITS = {
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

    for rel, edits in EXACT_EDITS.items():
        path = ROOT / rel
        text = path.read_text(encoding="utf-8", newline="").replace("\r\n", "\n")
        for old, new in edits:
            if old in text:
                text = text.replace(old, new)
            elif new and new not in text:
                raise SystemExit(f"Upstream changed {rel}: cannot find {old!r}")
        path.write_text(text, encoding="utf-8", newline="")

    endpoints = ROOT / "packages/constants/src/endpoints.ts"
    text = endpoints.read_text(encoding="utf-8", newline="")
    text = re.sub(r'\nexport const ORBIT_SOURCE_URL = ".*";\n', "", text)
    endpoints.write_text(text.rstrip("\n") + "\n" + SOURCE_EXPORT, encoding="utf-8", newline="")

    print(f"text files: {changed}, i18n files: {i18n}, assets/overrides: {copied}")


if __name__ == "__main__":
    main()
