"""Build a labeled, time-compressed GIF from six actual UI captures."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

CAPTIONS = [
    "Choose a printed flowchart",
    "Original source loaded",
    "Local model extraction — waiting time compressed",
    "Inspect the extracted nodes and arrows",
    "Rename a node in the workbench",
    "Updated graph and exports — no new model call",
]
DURATIONS = [900, 1500, 900, 2200, 1600, 2800]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=Path, default=Path("artifacts/demo"))
    parser.add_argument("--output", type=Path, default=Path("docs/images/demo.gif"))
    args = parser.parse_args()
    files = sorted(args.frames.glob("*.jpg"))
    if len(files) != 6:
        raise ValueError("Expected exactly six actual UI capture frames.")
    width = 1100
    height = max(round(Image.open(p).height * width / Image.open(p).width) for p in files)
    frames = []
    for file, caption in zip(files, CAPTIONS, strict=True):
        with Image.open(file) as source:
            source = ImageOps.contain(source.convert("RGB"), (width, height))
            canvas = Image.new("RGB", (width, height + 56), "white")
            canvas.paste(source, (0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((0, height, width, height + 56), fill="#17324c")
        draw.text((18, height + 8), caption, font=ImageFont.load_default(size=17), fill="white")
        draw.text(
            (18, height + 33),
            "Actual local UI capture · time-compressed demonstration",
            font=ImageFont.load_default(size=12),
            fill="#dce8f4",
        )
        frames.append(canvas)
    sheet = Image.new("RGB", (width, (height + 56) * len(frames)))
    for index, frame in enumerate(frames):
        sheet.paste(frame, (0, index * (height + 56)))
    palette = sheet.quantize(colors=256)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    indexed[0].save(
        args.output,
        save_all=True,
        append_images=indexed[1:],
        duration=DURATIONS,
        loop=0,
        disposal=2,
        optimize=False,
    )
    with Image.open(args.output) as gif:
        assert gif.n_frames == 6 and gif.info.get("loop") == 0
        elapsed = 0
        for index in range(gif.n_frames):
            gif.seek(index)
            elapsed += gif.info["duration"]
        assert elapsed == sum(DURATIONS)
    print(
        f"Created {args.output}: 6 actual capture frames, {elapsed / 1000:.1f}s loop, {args.output.stat().st_size} bytes."
    )


if __name__ == "__main__":
    main()
