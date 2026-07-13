from __future__ import annotations

from io import BytesIO
from statistics import median

from fastapi import HTTPException
from PIL import Image, ImageChops, ImageFilter, UnidentifiedImageError

CANVAS_SIZE = (1600, 600)
MAX_LOGO_SIZE = (1200, 300)
ALPHA_THRESHOLD = 8
BACKGROUND_TOLERANCE = 35
EDGE_SAMPLE_STEP = 12
MIN_VISIBLE_PIXELS_PER_LINE = 3


def _alpha_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    alpha = image.getchannel("A")
    mask = alpha.point(lambda value: 255 if value > ALPHA_THRESHOLD else 0)
    raw_bbox = mask.getbbox()
    if not raw_bbox:
        return None

    width, height = mask.size
    pixels = mask.load()

    left = 0
    while left < width and sum(1 for y in range(height) if pixels[left, y]) < MIN_VISIBLE_PIXELS_PER_LINE:
        left += 1

    right = width - 1
    while right >= left and sum(1 for y in range(height) if pixels[right, y]) < MIN_VISIBLE_PIXELS_PER_LINE:
        right -= 1

    top = 0
    while top < height and sum(1 for x in range(left, right + 1) if pixels[x, top]) < MIN_VISIBLE_PIXELS_PER_LINE:
        top += 1

    bottom = height - 1
    while bottom >= top and sum(1 for x in range(left, right + 1) if pixels[x, bottom]) < MIN_VISIBLE_PIXELS_PER_LINE:
        bottom -= 1

    if left > right or top > bottom:
        return raw_bbox
    return (left, top, right + 1, bottom + 1)


def _has_real_transparency(image: Image.Image) -> bool:
    alpha = image.getchannel("A")
    low, high = alpha.getextrema()
    return low < 250 and high > ALPHA_THRESHOLD


def _sample_edge_background(image: Image.Image) -> tuple[int, int, int]:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    samples: list[tuple[int, int, int]] = []
    step = max(1, EDGE_SAMPLE_STEP)

    for x in range(0, width, step):
        samples.append(pixels[x, 0])
        samples.append(pixels[x, height - 1])
    for y in range(0, height, step):
        samples.append(pixels[0, y])
        samples.append(pixels[width - 1, y])
    samples.extend([
        pixels[0, 0],
        pixels[width - 1, 0],
        pixels[0, height - 1],
        pixels[width - 1, height - 1],
    ])

    return (
        int(median(sample[0] for sample in samples)),
        int(median(sample[1] for sample in samples)),
        int(median(sample[2] for sample in samples)),
    )


def _make_solid_background_transparent(image: Image.Image) -> Image.Image:
    """Remove a near-solid edge background, typically black/white logo backdrops."""
    if _has_real_transparency(image):
        return image

    background = _sample_edge_background(image)
    rgb = image.convert("RGB")
    background_layer = Image.new("RGB", rgb.size, background)
    diff = ImageChops.difference(rgb, background_layer).convert("L")

    # Pixels close to the sampled edge color are background. The small median
    # filter removes isolated JPEG/resize speckles without an expensive Python
    # connected-component scan.
    alpha = diff.point(lambda value: 0 if value <= BACKGROUND_TOLERANCE else 255)
    alpha = alpha.filter(ImageFilter.MedianFilter(size=3))

    result = image.convert("RGBA")
    result.putalpha(alpha)
    return result


def _clean_alpha_mask(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    alpha = alpha.point(lambda value: 255 if value > ALPHA_THRESHOLD else 0)
    result = image.convert("RGBA")
    result.putalpha(alpha)
    return result


def normalize_logo_png_bytes(content: bytes) -> bytes:
    if not content:
        raise HTTPException(status_code=400, detail="上传图片为空")
    try:
        with Image.open(BytesIO(content)) as source:
            image = source.convert("RGBA")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="logo.png 不是有效图片") from exc

    image = _make_solid_background_transparent(image)
    image = _clean_alpha_mask(image)
    bbox = _alpha_bbox(image)
    if not bbox:
        raise HTTPException(status_code=400, detail="logo.png 没有可见内容")

    cropped = image.crop(bbox)
    max_width, max_height = MAX_LOGO_SIZE
    scale = min(max_width / cropped.width, max_height / cropped.height)
    target_width = max(1, round(cropped.width * scale))
    target_height = max(1, round(cropped.height * scale))
    resized = cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)

    canvas_width, canvas_height = CANVAS_SIZE
    canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    left = (canvas_width - target_width) // 2
    top = (canvas_height - target_height) // 2
    canvas.alpha_composite(resized, (left, top))

    output = BytesIO()
    canvas.save(output, format="PNG", compress_level=3)
    return output.getvalue()
