"""Screenshot Annotator — adds callout boxes, arrows, and highlights to screenshots.

Uses Pillow to overlay annotations on captured screenshots for the report's
messaging teardown and visual analysis sections.
"""

import base64
import io
import logging
from typing import Any

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Brand colors for annotations
ANNOTATION_COLORS = {
    "red": (239, 68, 68),       # --red / problem callout
    "green": (34, 197, 94),     # --green / strength callout
    "accent": (87, 94, 207),    # --accent / neutral callout
    "yellow": (251, 191, 36),   # --yellow / warning callout
    "blue": (96, 165, 250),     # --blue / info callout
}

# Semi-transparent overlay fill (RGBA)
OVERLAY_ALPHA = 50
BORDER_WIDTH = 3
LABEL_PADDING = 6
FONT_SIZE = 14
NUMBERED_CIRCLE_RADIUS = 14


def annotate_screenshot(
    image_data: bytes | str,
    annotations: list[dict[str, Any]],
) -> bytes:
    """Add callout boxes, arrows, and highlights to a screenshot.

    Args:
        image_data: Raw PNG bytes or base64-encoded string.
        annotations: List of annotation dicts, each with:
            - x, y: Top-left position (pixels)
            - width, height: Dimensions of the region
            - label: Text label for the callout
            - color: Key from ANNOTATION_COLORS (default "red")
            - type: "callout_box" | "highlight" | "numbered" (default "callout_box")
            - number: (for type="numbered") The number to display in the circle

    Returns:
        Annotated PNG image as bytes.
    """
    # Decode input
    if isinstance(image_data, str):
        image_data = base64.b64decode(image_data)

    img = Image.open(io.BytesIO(image_data)).convert("RGBA")

    # Create overlay layer for semi-transparent fills
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    # Main draw for borders and text
    draw = ImageDraw.Draw(img)

    # Try to load a nice font, fall back to default
    font = _get_font(FONT_SIZE)
    small_font = _get_font(FONT_SIZE - 2)

    for i, ann in enumerate(annotations):
        x = int(ann.get("x", 0))
        y = int(ann.get("y", 0))
        w = int(ann.get("width", 100))
        h = int(ann.get("height", 50))
        label = ann.get("label", "")
        color_key = ann.get("color", "red")
        ann_type = ann.get("type", "callout_box")
        number = ann.get("number", i + 1)

        color = ANNOTATION_COLORS.get(color_key, ANNOTATION_COLORS["red"])
        fill_rgba = (*color, OVERLAY_ALPHA)

        # Clamp to image bounds
        x = max(0, min(x, img.width - 10))
        y = max(0, min(y, img.height - 10))
        w = min(w, img.width - x)
        h = min(h, img.height - y)

        if ann_type == "highlight":
            # Semi-transparent filled rectangle only
            overlay_draw.rectangle(
                [x, y, x + w, y + h],
                fill=fill_rgba,
            )
            # Thin border
            draw.rectangle(
                [x, y, x + w, y + h],
                outline=color,
                width=2,
            )

        elif ann_type == "numbered":
            # Numbered circle at top-left of region + border
            overlay_draw.rectangle(
                [x, y, x + w, y + h],
                fill=fill_rgba,
            )
            draw.rectangle(
                [x, y, x + w, y + h],
                outline=color,
                width=BORDER_WIDTH,
            )
            # Draw numbered circle
            _draw_numbered_circle(draw, x - 5, y - 5, number, color, small_font)

        else:
            # callout_box: border + label badge at top
            overlay_draw.rectangle(
                [x, y, x + w, y + h],
                fill=fill_rgba,
            )
            draw.rectangle(
                [x, y, x + w, y + h],
                outline=color,
                width=BORDER_WIDTH,
            )

            if label:
                _draw_label_badge(draw, x, y, label, color, font)

    # Composite overlay onto image
    img = Image.alpha_composite(img, overlay)

    # Convert back to bytes
    output = io.BytesIO()
    img.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()


def annotate_screenshot_b64(
    base64_data: str,
    annotations: list[dict[str, Any]],
) -> str:
    """Convenience wrapper: takes and returns base64 strings."""
    result_bytes = annotate_screenshot(base64_data, annotations)
    return base64.b64encode(result_bytes).decode("utf-8")


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a system font at the given size, with fallback to default."""
    font_paths = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _draw_label_badge(
    draw: ImageDraw.Draw,
    x: int,
    y: int,
    label: str,
    color: tuple[int, int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """Draw a colored badge with text label above the annotation region."""
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    badge_w = text_w + LABEL_PADDING * 2
    badge_h = text_h + LABEL_PADDING * 2

    # Position badge above the region, aligned to left edge
    badge_x = x
    badge_y = max(0, y - badge_h - 2)

    draw.rectangle(
        [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
        fill=color,
    )
    draw.text(
        (badge_x + LABEL_PADDING, badge_y + LABEL_PADDING),
        label,
        fill=(255, 255, 255),
        font=font,
    )


def _draw_numbered_circle(
    draw: ImageDraw.Draw,
    x: int,
    y: int,
    number: int,
    color: tuple[int, int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """Draw a filled circle with a number inside it."""
    r = NUMBERED_CIRCLE_RADIUS
    cx = max(r, x)
    cy = max(r, y)

    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=color,
        outline=(255, 255, 255),
        width=2,
    )

    text = str(number)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(
        (cx - text_w // 2, cy - text_h // 2),
        text,
        fill=(255, 255, 255),
        font=font,
    )
