from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.utils import timezone
from pathlib import Path
import io, os

# choose a bundled-safe fallback font if no TTF available
DEFAULT_FONT = str(Path(settings.BASE_DIR) / 'static' / 'fonts' / 'DejaVuSans.ttf')

def generate_certificate_image(template_path, student_name, course, date_str):
    # Open template
    im = Image.open(template_path).convert("RGB")
    W, H = im.size
    draw = ImageDraw.Draw(im)

    # Load fonts (adjust sizes)
    try:
        font_name = ImageFont.truetype(DEFAULT_FONT, size=int(min(W, H) * 0.06))
        font_course = ImageFont.truetype(DEFAULT_FONT, size=int(min(W, H) * 0.045))
        font_date = ImageFont.truetype(DEFAULT_FONT, size=int(min(W, H) * 0.035))
    except Exception:
        font_name = ImageFont.load_default()
        font_course = ImageFont.load_default()
        font_date = ImageFont.load_default()

    # Centered positions
    def center_text(text, y, font):
        w, h = draw.textbbox((0,0), text, font=font)[2:]
        x = (W - w)//2
        draw.text((x, y), text, font=font, fill=(20,20,20))

    center_text(student_name, int(H*0.45), font_name)
    center_text(f"Course: {course}", int(H*0.58), font_course)
    center_text(f"Date: {date_str}", int(H*0.67), font_date)

    return im

def save_certificate(im, out_dir, file_stem):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{file_stem}.pdf"
    im.save(out_path, "PDF", resolution=150.0)
    return str(out_path)
