"""Generate Orbit logo assets at the same sizes as the Plane originals. Run once; output is committed."""
import math
import shutil
import subprocess
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "assets"
INDIGO = (91, 91, 214, 255)
WHITE = (255, 255, 255, 255)
INK = (28, 28, 40, 255)
FONT = r"C:\Windows\Fonts\seguisb.ttf"
SS = 4


def mark(size, color, gap_color=None, angle=-45.0):
    """Ring with a satellite dot. gap_color cuts a halo around the dot; None means transparent."""
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = s * 0.14
    width = max(1, round(s * 0.13))
    d.ellipse([pad, pad, s - pad, s - pad], outline=color, width=width)
    radius = (s - 2 * pad) / 2 - width / 2
    cx = s / 2 + radius * math.cos(math.radians(angle))
    cy = s / 2 + radius * math.sin(math.radians(angle))
    halo, dot = s * 0.17, s * 0.105
    box = lambda r: [cx - r, cy - r, cx + r, cy + r]
    if gap_color is None:
        hole = Image.new("L", (s, s), 255)
        ImageDraw.Draw(hole).ellipse(box(halo), fill=0)
        img.putalpha(Image.composite(img.getchannel("A"), Image.new("L", (s, s), 0), hole))
        d = ImageDraw.Draw(img)
    else:
        d.ellipse(box(halo), fill=gap_color)
    d.ellipse(box(dot), fill=color)
    return img.resize((size, size), Image.LANCZOS)


def tile(size):
    """App icon: white mark on a rounded indigo square."""
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([0, 0, s - 1, s - 1], radius=s * 0.22, fill=INDIGO)
    inner = round(size * 0.86)
    m = mark(inner, WHITE, gap_color=INDIGO).resize((inner * SS, inner * SS), Image.LANCZOS)
    img.alpha_composite(m, ((s - m.width) // 2, (s - m.height) // 2))
    return img.resize((size, size), Image.LANCZOS)


def lockup(w, h, text_color):
    """Mark + wordmark, fitted and centred inside w x h."""
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    mark_h = round(h * 0.82)
    m = mark(mark_h, INDIGO).resize((mark_h * SS, mark_h * SS), Image.LANCZOS)
    font = ImageFont.truetype(FONT, round(mark_h * 0.72) * SS)
    tw = font.getbbox("Orbit")[2]
    gap = round(mark_h * 0.22) * SS
    total = m.width + gap + tw
    if total > img.width:
        scaled = lockup(round(w * total / img.width) + 1, round(h * total / img.width) + 1, text_color)
        return scaled.resize((w, h), Image.LANCZOS)
    x = (img.width - total) // 2
    img.alpha_composite(m, (x, (img.height - m.height) // 2))
    d = ImageDraw.Draw(img)
    d.text((x + m.width + gap, img.height // 2), "Orbit", font=font, fill=text_color, anchor="lm")
    return img.resize((w, h), Image.LANCZOS)


def centered(w, h, side):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    m = mark(side, INDIGO)
    img.alpha_composite(m, ((w - side) // 2, (h - side) // 2))
    return img


def spinner(path, w, h):
    frames = []
    side = round(min(w, h) * 0.5)
    for i in range(36):
        canvas = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        m = mark(side, INDIGO, angle=-90 + i * 10)
        canvas.alpha_composite(m, ((w - side) // 2, (h - side) // 2))
        alpha = canvas.getchannel("A").point(lambda a: 255 if a > 110 else 0)
        out = canvas.convert("RGB").quantize(colors=16, method=Image.Quantize.FASTOCTREE)
        out.paste(255, Image.eval(alpha, lambda a: 255 - a))
        frames.append(out)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=40, loop=0, transparency=255, disposal=2)


def original_size(rel):
    data = subprocess.check_output(["git", "show", f"v1.4.3:{rel}"], cwd=ROOT)
    return Image.open(BytesIO(data)).size


def save(rel, img):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    img.save(p)


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    tiles = """apps/admin/app/assets/favicon/apple-touch-icon.png apps/admin/app/assets/favicon/favicon-16x16.png
    apps/admin/app/assets/favicon/favicon-32x32.png apps/admin/public/favicon/android-chrome-192x192.png
    apps/admin/public/favicon/android-chrome-512x512.png apps/web/app/assets/favicon/apple-touch-icon.png
    apps/web/app/assets/favicon/favicon-16x16.png apps/web/app/assets/favicon/favicon-32x32.png
    apps/web/app/assets/icons/icon-180x180.png apps/web/app/assets/icons/icon-512x512.png
    apps/web/public/favicon/android-chrome-192x192.png apps/web/public/favicon/android-chrome-512x512.png
    apps/web/public/icons/icon-192x192.png apps/web/public/icons/icon-348x348.png
    apps/web/public/icons/icon-512x512.png apps/web/public/plane-logos/plane-mobile-pwa.png""".split()
    for rel in tiles:
        save(rel, tile(original_size(rel)[0]))

    for app in ("web", "admin"):
        rel = f"apps/{app}/app/assets/favicon/favicon.ico"
        (OUT / rel).parent.mkdir(parents=True, exist_ok=True)
        tile(64).save(OUT / rel, sizes=[(16, 16), (32, 32), (48, 48)])
        for name in ("logo-spinner-dark", "logo-spinner-light"):
            rel = f"apps/{app}/app/assets/images/{name}.gif"
            (OUT / rel).parent.mkdir(parents=True, exist_ok=True)
            spinner(OUT / rel, *original_size(rel))

    for rel in ("apps/web/app/assets/auth/gradient-logo.webp", "apps/web/app/assets/auth/gradient-bg-logo.webp",
                "apps/web/app/assets/plane-takeoff.png", "apps/admin/app/assets/images/plane-takeoff.png"):
        w, h = original_size(rel)
        save(rel, centered(w, h, round(min(w, h) * 0.6)))

    save("apps/web/app/assets/plane-logos/blue-without-text.png", mark(276, INDIGO))
    save("apps/web/app/assets/plane-logos/black-horizontal-with-blue-logo.png", lockup(269, 60, INK))
    save("apps/web/app/assets/plane-logos/white-horizontal-with-blue-logo.png", lockup(269, 60, WHITE))

    save("apps/web/public/orbit-email-dark.png", lockup(320, 72, INK))
    save("apps/web/public/orbit-email-white.png", lockup(320, 72, WHITE))

    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">'
           '<circle cx="12" cy="12" r="8.2" stroke="#5B5BD6" stroke-width="3"/>'
           '<circle cx="17.8" cy="6.2" r="3.9" fill="{gap}"/><circle cx="17.8" cy="6.2" r="2.4" fill="#5B5BD6"/></svg>')
    for name, gap in (("takeoff-icon-light", "#FFFFFF"), ("takeoff-icon-dark", "#1C1C28")):
        p = OUT / f"apps/admin/app/assets/logos/{name}.svg"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(svg.format(gap=gap))
    white = '<svg xmlns="http://www.w3.org/2000/svg" width="269" height="60" viewBox="0 0 269 60"><text x="134" y="44" text-anchor="middle" font-family="system-ui,sans-serif" font-size="40" font-weight="600" fill="#fff">Orbit</text></svg>'
    p = OUT / "apps/web/app/assets/plane-logos/white-horizontal.svg"
    p.write_text(white)

    preview = Image.new("RGBA", (760, 300), (245, 245, 250, 255))
    preview.alpha_composite(tile(180), (20, 20))
    preview.alpha_composite(mark(120, INDIGO), (220, 50))
    preview.alpha_composite(lockup(320, 72, INK), (360, 40))
    dark = Image.new("RGBA", (340, 100), (28, 28, 40, 255))
    dark.alpha_composite(lockup(320, 72, WHITE), (10, 14))
    preview.alpha_composite(dark, (350, 130))
    x = 20
    for sz in (16, 32, 48):
        preview.alpha_composite(tile(sz), (x, 225))
        x += sz + 20
    preview.save(Path(__file__).resolve().parent / "preview.png")
    print("assets:", sum(1 for f in OUT.rglob("*") if f.is_file()))


if __name__ == "__main__":
    sys.exit(main())
