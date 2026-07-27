#!/usr/bin/env python3
"""Extract a small set of representative colors from the rendered banner."""

from __future__ import annotations

import argparse
import colorsys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageEnhance


@dataclass(frozen=True)
class Swatch:
    count: int
    color: tuple[int, int, int]
    hue: float
    lightness: float
    saturation: float

    @property
    def hex(self) -> str:
        return "#" + "".join(f"{channel:02x}" for channel in self.color)


def extract(image_path: Path) -> list[Swatch]:
    image = Image.open(image_path).convert("RGB")

    # Match the filter used by the masthead CSS.
    image = ImageEnhance.Brightness(image).enhance(0.78)
    image = ImageEnhance.Color(image).enhance(0.94)
    image.thumbnail((640, 100))

    quantized = image.quantize(colors=64, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()
    swatches = []

    for count, index in quantized.getcolors() or []:
        offset = index * 3
        color = tuple(palette[offset : offset + 3])
        hue, lightness, saturation = colorsys.rgb_to_hls(
            *(channel / 255 for channel in color)
        )
        swatches.append(
            Swatch(
                count,
                color,
                hue * 360,
                lightness,
                saturation,
            )
        )

    return swatches


def choose(
    swatches: list[Swatch],
    *,
    hue: tuple[float, float] | None = None,
    lightness: tuple[float, float] = (0.0, 1.0),
    saturation: tuple[float, float] = (0.0, 1.0),
) -> Swatch:
    candidates = [
        swatch
        for swatch in swatches
        if (hue is None or hue[0] <= swatch.hue <= hue[1])
        and lightness[0] <= swatch.lightness <= lightness[1]
        and saturation[0] <= swatch.saturation <= saturation[1]
    ]
    if not candidates:
        raise ValueError("no color matched one of the requested swatch roles")

    return max(
        candidates,
        key=lambda swatch: swatch.count * (0.35 + swatch.saturation),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "image",
        nargs="?",
        type=Path,
        default=Path(__file__).with_name("output") / "banner.png",
    )
    args = parser.parse_args()
    swatches = extract(args.image)
    roles = {
        "lapis": choose(
            swatches,
            hue=(190, 250),
            lightness=(0.08, 0.32),
            saturation=(0.20, 1.0),
        ),
        "clay": choose(
            swatches,
            hue=(10, 32),
            lightness=(0.30, 0.50),
            saturation=(0.25, 1.0),
        ),
        "ochre": choose(
            swatches,
            hue=(32, 55),
            lightness=(0.28, 0.50),
            saturation=(0.20, 1.0),
        ),
        "stone": choose(
            swatches,
            lightness=(0.30, 0.58),
            saturation=(0.0, 0.18),
        ),
    }

    for name, swatch in roles.items():
        print(
            f"{name:>6}: {swatch.hex}  "
            f"H {swatch.hue:5.1f}°  "
            f"L {swatch.lightness:.2f}  "
            f"S {swatch.saturation:.2f}"
        )


if __name__ == "__main__":
    main()
