import pytest
from PIL import Image

from diagram2graph.images import load_image


def test_normalize_alpha_and_orientation(tmp_path):
    path = tmp_path / "alpha.png"
    Image.new("RGBA", (20, 10), (255, 0, 0, 0)).save(path)
    assert load_image(path).getpixel((0, 0)) == (255, 255, 255)
    path = tmp_path / "rotated.jpg"
    image = Image.new("RGB", (20, 10), "blue")
    exif = image.getexif()
    exif[274] = 6
    image.save(path, exif=exif)
    assert load_image(path).size == (10, 20)


def test_reject_corrupt_and_unsupported_images(tmp_path):
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not an image")
    with pytest.raises(ValueError):
        load_image(bad)
    gif = tmp_path / "animated.gif"
    Image.new("RGB", (10, 10)).save(
        gif, save_all=True, append_images=[Image.new("RGB", (10, 10), "red")]
    )
    with pytest.raises(ValueError):
        load_image(gif)


def test_reject_oversized_dimension_before_decode(tmp_path):
    path = tmp_path / "wide.png"
    Image.new("RGB", (4097, 1)).save(path)
    with pytest.raises(ValueError):
        load_image(path)


def test_reject_large_file_before_open(tmp_path):
    path = tmp_path / "large.png"
    with path.open("wb") as f:
        f.truncate(10 * 1024 * 1024 + 1)
    with pytest.raises(ValueError):
        load_image(path)


@pytest.mark.parametrize("corruption", ["missing_iend", "bad_crc"])
def test_png_container_integrity_is_verified(tmp_path, corruption):
    path = tmp_path / "corrupt.png"
    Image.new("RGB", (10, 10), "blue").save(path)
    data = bytearray(path.read_bytes())
    if corruption == "missing_iend":
        data = data[:-12]
    else:
        start = data.index(b"IDAT")
        length = int.from_bytes(data[start - 4 : start], "big")
        data[start + 4 + length] ^= 1
    path.write_bytes(data)
    with pytest.raises(ValueError):
        load_image(path)
