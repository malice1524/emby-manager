from __future__ import annotations

from collections import deque
from io import BytesIO

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

CANVAS_SIZE = (1600, 600)
MAX_LOGO_SIZE = (1200, 300)
ALPHA_THRESHOLD = 8
SMALL_COMPONENT_AREA = 80


def _remove_small_alpha_components(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    width, height = image.size
    alpha = image.getchannel("A")
    alpha_pixels = alpha.load()
    visited = bytearray(width * height)
    keep = bytearray(width * height)
    directions = ((1, 0), (-1, 0), (0, 1), (0, -1))

    for y in range(height):
        for x in range(width):
            index = y * width + x
            if visited[index] or alpha_pixels[x, y] <= ALPHA_THRESHOLD:
                continue
            queue = deque([(x, y)])
            visited[index] = 1
            points: list[tuple[int, int]] = []
            while queue:
                current_x, current_y = queue.popleft()
                points.append((current_x, current_y))
                for dx, dy in directions:
                    next_x = current_x + dx
                    next_y = current_y + dy
                    if 0 <= next_x < width and 0 <= next_y < height:
                        next_index = next_y * width + next_x
                        if not visited[next_index] and alpha_pixels[next_x, next_y] > ALPHA_THRESHOLD:
                            visited[next_index] = 1
                            queue.append((next_x, next_y))
            if len(points) >= SMALL_COMPONENT_AREA:
                for point_x, point_y in points:
                    keep[point_y * width + point_x] = 1

    if not any(keep):
        return image

    pixels = image.load()
    for y in range(height):
        for x in range(width):
            if alpha_pixels[x, y] > 0 and not keep[y * width + x]:
                red, green, blue, _alpha = pixels[x, y]
                pixels[x, y] = (red, green, blue, 0)
    return image


def _alpha_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    alpha = image.getchannel("A")
    mask = alpha.point(lambda value: 255 if value > ALPHA_THRESHOLD else 0)
    return mask.getbbox()


def normalize_logo_png_bytes(content: bytes) -> bytes:
    if not content:
        raise HTTPException(status_code=400, detail="上传图片为空")
    try:
        with Image.open(BytesIO(content)) as source:
            image = source.convert("RGBA")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="logo.png 不是有效图片") from exc

    image = _remove_small_alpha_components(image)
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
    canvas.save(output, format="PNG", optimize=True)
    return output.getvalue()
