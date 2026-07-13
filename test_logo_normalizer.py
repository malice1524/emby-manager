from io import BytesIO

from PIL import Image

from backend.app.logo_normalizer import normalize_logo_png_bytes


def png_bytes(width: int, height: int, box: tuple[int, int, int, int]) -> bytes:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    left, top, right, bottom = box
    for x in range(left, right):
        for y in range(top, bottom):
            image.putpixel((x, y), (255, 255, 255, 255))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def normalized_bbox(content: bytes) -> tuple[int, int, int, int]:
    image = Image.open(BytesIO(normalize_logo_png_bytes(content)))
    assert image.mode == "RGBA"
    assert image.size == (1600, 600)
    return image.getchannel("A").getbbox()


def test_normalize_logo_fits_wide_artwork_to_max_width():
    assert normalized_bbox(png_bytes(500, 200, (50, 80, 450, 120))) == (200, 240, 1400, 360)


def test_normalize_logo_fits_tall_artwork_to_max_height():
    assert normalized_bbox(png_bytes(300, 500, (120, 50, 180, 450))) == (777, 150, 822, 450)


def test_normalize_logo_removes_solid_black_background():
    image = Image.new("RGB", (500, 300), (0, 0, 0))
    for x in range(150, 350):
        for y in range(110, 190):
            image.putpixel((x, y), (255, 255, 255))
    output = BytesIO()
    image.save(output, format="PNG")

    normalized = Image.open(BytesIO(normalize_logo_png_bytes(output.getvalue())))
    assert normalized.size == (1600, 600)
    assert normalized.mode == "RGBA"
    assert normalized.getpixel((0, 0))[3] == 0
    assert normalized.getchannel("A").getbbox() == (425, 150, 1175, 450)


def test_normalize_logo_converts_jpeg_with_solid_background_to_transparent_png():
    image = Image.new("RGB", (500, 300), (0, 0, 0))
    for x in range(150, 350):
        for y in range(110, 190):
            image.putpixel((x, y), (255, 255, 255))
    output = BytesIO()
    image.save(output, format="JPEG", quality=95)

    normalized = Image.open(BytesIO(normalize_logo_png_bytes(output.getvalue())))
    assert normalized.format == "PNG"
    assert normalized.mode == "RGBA"
    assert normalized.size == (1600, 600)
    assert normalized.getpixel((0, 0))[3] == 0
    bbox = normalized.getchannel("A").getbbox()
    assert bbox[1] == 150
    assert bbox[3] == 450
    assert 420 <= bbox[0] <= 430
    assert 1170 <= bbox[2] <= 1180


def test_normalize_logo_removes_tiny_corner_noise_before_cropping():
    image = Image.new("RGBA", (500, 300), (0, 0, 0, 0))
    image.putpixel((2, 2), (255, 255, 255, 255))
    for x in range(150, 350):
        for y in range(110, 190):
            image.putpixel((x, y), (255, 255, 255, 255))
    output = BytesIO()
    image.save(output, format="PNG")

    assert normalized_bbox(output.getvalue()) == (425, 150, 1175, 450)
