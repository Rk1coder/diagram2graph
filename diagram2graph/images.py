import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError


def load_image(path: str | Path) -> Image.Image:
    try:
        path = Path(path)
        if path.stat().st_size > 10 * 1024 * 1024:
            raise ValueError("Screenshot exceeds the 10 MiB limit.")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as source:
                if source.format not in {"PNG", "JPEG"} or getattr(source, "n_frames", 1) != 1:
                    raise ValueError("Upload one non-animated PNG or JPEG screenshot.")
                w, h = source.size
                if max(w, h) > 4096 or w * h > 12_000_000:
                    raise ValueError(
                        "Screenshot must fit 4096 pixels per edge and 12 million pixels."
                    )
                if source.format == "PNG":
                    with path.open("rb") as stream:
                        stream.seek(-12, 2)
                        if stream.read() != b"\x00\x00\x00\x00IEND\xaeB`\x82":
                            raise ValueError("PNG container is incomplete or malformed.")
                source.verify()
            with Image.open(path) as verified:
                image = ImageOps.exif_transpose(verified).convert("RGBA")
                background = Image.new("RGBA", image.size, "white")
                return Image.alpha_composite(background, image).convert("RGB")
    except (
        OSError,
        SyntaxError,
        TypeError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise ValueError("Cannot read this screenshot. Upload a valid PNG or JPEG.") from exc
