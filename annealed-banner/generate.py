#!/usr/bin/env python3
"""Approximate a panoramic image with simulated-annealed translucent shapes.

The optimization happens on a deliberately tiny raster.  The final result is
written as SVG, so the website receives a small, resolution-independent asset
rather than a bitmap or a JavaScript animation.
"""

from __future__ import annotations

import argparse
import html
import math
import random
from dataclasses import dataclass, replace
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat


# Configuration
# -----------------------------------------------------------------------------
# Edit these values, then run the script again.  The defaults reproduce the
# Skyline ×100 result currently used by the website.

# Output geometry.  WORK_* controls optimization cost; SVG_* controls only the
# final vector dimensions.  Keep both pairs at the same aspect ratio.
WORK_WIDTH = 384
WORK_HEIGHT = 60
SVG_WIDTH = 1280
SVG_HEIGHT = 200

# Vertical center of the source crop, from 0.0 (top) to 1.0 (bottom).
CROP_CENTER_Y = 0.25

# More shapes add detail and increase running time and SVG size.
SHAPE_COUNT = 3600

# More steps improve each proposed shape but increase running time.
STEPS_PER_SHAPE = 12

# Change this to explore another deterministic arrangement.
RANDOM_SEED = 546

# Values below 1.0 constrain the largest early shapes.
MAX_SHAPE_SCALE = 1.0

# False uses triangles only.  True also permits quadrilaterals and ellipses.
MIXED_SHAPES = False

# None samples a neutral base from the crop.  An RGB tuple such as
# (23, 54, 95) creates a deliberate colored foundation.
BACKGROUND_COLOR: tuple[int, int, int] | None = None

# Names the generated SVG, PNG preview, and source-crop JPEG.
OUTPUT_NAME = "banner"


@dataclass(frozen=True)
class Shape:
    kind: str
    points: tuple[tuple[float, float], ...]
    opacity: float
    color: tuple[int, int, int] = (0, 0, 0)


@dataclass(frozen=True)
class Evaluated:
    shape: Shape
    energy: int


def image_energy(left: Image.Image, right: Image.Image) -> int:
    difference = ImageChops.difference(left, right)
    return int(sum(ImageStat.Stat(difference).sum2))


def crop_banner(source: Image.Image, center_y: float) -> Image.Image:
    target_ratio = WORK_WIDTH / WORK_HEIGHT
    crop_width = source.width
    crop_height = round(crop_width / target_ratio)

    if crop_height > source.height:
        crop_height = source.height
        crop_width = round(crop_height * target_ratio)

    center = round(center_y * source.height)
    left = (source.width - crop_width) // 2
    top = max(0, min(source.height - crop_height, center - crop_height // 2))
    crop = source.crop((left, top, left + crop_width, top + crop_height))
    return crop.resize((WORK_WIDTH, WORK_HEIGHT), Image.Resampling.LANCZOS)


def mean_color(image: Image.Image) -> tuple[int, int, int]:
    return tuple(round(channel) for channel in ImageStat.Stat(image).mean)


def random_shape(
    rng: random.Random,
    progress: float,
    shape_count: int,
    mixed: bool,
    max_shape_scale: float,
) -> Shape:
    cx = rng.uniform(0, WORK_WIDTH)
    cy = rng.uniform(0, WORK_HEIGHT)

    density_scale = max(0.08, math.sqrt(72 / shape_count))
    remaining = (1.0 - progress) ** 3
    horizontal_min = max(0.75, WORK_WIDTH * 0.035 * density_scale)
    horizontal_max = max(
        horizontal_min * 1.5,
        WORK_WIDTH
        * (0.18 * remaining + 0.06 * density_scale)
        * max_shape_scale,
    )
    vertical_min = max(0.55, WORK_HEIGHT * 0.14 * density_scale)
    vertical_max = max(
        vertical_min * 1.5,
        WORK_HEIGHT
        * (0.70 * remaining + 0.24 * density_scale)
        * max_shape_scale,
    )
    horizontal = rng.uniform(horizontal_min, horizontal_max)
    vertical = rng.uniform(vertical_min, vertical_max)
    choice = rng.random() if mixed else 0.0

    if choice < 0.48:
        kind = "polygon"
        rotation = rng.uniform(0, math.tau)
        points = []
        for corner in range(3):
            angle = rotation + corner * math.tau / 3 + rng.uniform(-0.55, 0.55)
            radius = rng.uniform(0.65, 1.20)
            points.append(
                (
                    cx + math.cos(angle) * horizontal * radius,
                    cy + math.sin(angle) * vertical * radius,
                )
            )
    elif choice < 0.90:
        kind = "polygon"
        rotation = rng.gauss(0, 0.16)
        cosine = math.cos(rotation)
        sine = math.sin(rotation)
        points = []
        for x_sign, y_sign in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            x = x_sign * horizontal
            y = y_sign * vertical
            points.append(
                (
                    cx + x * cosine - y * sine,
                    cy + x * sine + y * cosine,
                )
            )
    else:
        kind = "ellipse"
        points = [
            (cx - horizontal, cy - vertical),
            (cx + horizontal, cy + vertical),
        ]

    return Shape(
        kind=kind,
        points=tuple(points),
        opacity=rng.uniform(0.48, 0.92),
    )


def shape_bounds(shape: Shape) -> tuple[int, int, int, int] | None:
    xs = [point[0] for point in shape.points]
    ys = [point[1] for point in shape.points]
    left = max(0, math.floor(min(xs)))
    top = max(0, math.floor(min(ys)))
    right = min(WORK_WIDTH, math.ceil(max(xs)) + 1)
    bottom = min(WORK_HEIGHT, math.ceil(max(ys)) + 1)
    if right - left < 2 or bottom - top < 2:
        return None
    return left, top, right, bottom


def draw_shape(
    image: Image.Image,
    shape: Shape,
    offset: tuple[float, float],
    fill: int,
) -> None:
    offset_x, offset_y = offset
    points = [(x - offset_x, y - offset_y) for x, y in shape.points]
    drawing = ImageDraw.Draw(image)
    if shape.kind == "ellipse":
        left = min(points[0][0], points[1][0])
        top = min(points[0][1], points[1][1])
        right = max(points[0][0], points[1][0])
        bottom = max(points[0][1], points[1][1])
        drawing.ellipse((left, top, right, bottom), fill=fill)
    else:
        drawing.polygon(points, fill=fill)


def evaluate(
    shape: Shape,
    base: Image.Image,
    target: Image.Image,
    base_energy: int,
) -> Evaluated | None:
    bounds = shape_bounds(shape)
    if bounds is None:
        return None

    left, top, right, bottom = bounds
    width = right - left
    height = bottom - top

    binary_mask = Image.new("L", (width, height))
    draw_shape(binary_mask, shape, (left, top), 255)
    if binary_mask.getbbox() is None:
        return None

    base_crop = base.crop(bounds)
    target_crop = target.crop(bounds)
    target_mean = ImageStat.Stat(target_crop, binary_mask).mean
    base_mean = ImageStat.Stat(base_crop, binary_mask).mean

    alpha = shape.opacity
    color = tuple(
        round(max(0, min(255, (target_mean[i] - (1 - alpha) * base_mean[i]) / alpha)))
        for i in range(3)
    )
    alpha_mask = binary_mask.point(lambda value: round(value * alpha))
    candidate_crop = Image.composite(
        Image.new("RGB", (width, height), color),
        base_crop,
        alpha_mask,
    )

    local_before = image_energy(base_crop, target_crop)
    local_after = image_energy(candidate_crop, target_crop)
    energy = base_energy - local_before + local_after
    return Evaluated(replace(shape, color=color), energy)


def clamp_point(point: tuple[float, float]) -> tuple[float, float]:
    margin_x = WORK_WIDTH * 0.12
    margin_y = WORK_HEIGHT * 0.25
    return (
        max(-margin_x, min(WORK_WIDTH + margin_x, point[0])),
        max(-margin_y, min(WORK_HEIGHT + margin_y, point[1])),
    )


def mutate(
    shape: Shape,
    rng: random.Random,
    heat: float,
) -> Shape:
    points = list(shape.points)
    span_x = max(point[0] for point in points) - min(point[0] for point in points)
    span_y = max(point[1] for point in points) - min(point[1] for point in points)
    choice = rng.random()

    if choice < 0.58:
        vertex = rng.randrange(len(points))
        x, y = points[vertex]
        points[vertex] = clamp_point(
            (
                x + rng.gauss(0, span_x * 0.22 * heat + 0.25),
                y + rng.gauss(0, span_y * 0.22 * heat + 0.18),
            )
        )
    elif choice < 0.83:
        dx = rng.gauss(0, span_x * 0.16 * heat + 0.20)
        dy = rng.gauss(0, span_y * 0.16 * heat + 0.15)
        points = [clamp_point((x + dx, y + dy)) for x, y in points]
    else:
        opacity = max(
            0.32,
            min(0.98, shape.opacity + rng.gauss(0, 0.12 * heat + 0.01)),
        )
        return replace(shape, opacity=opacity)

    return replace(
        shape,
        points=tuple(points),
    )


def apply_shape(base: Image.Image, shape: Shape) -> Image.Image:
    result = base.copy()
    bounds = shape_bounds(shape)
    if bounds is None:
        return result

    left, top, right, bottom = bounds
    size = (right - left, bottom - top)
    mask = Image.new("L", size)
    draw_shape(mask, shape, (left, top), round(255 * shape.opacity))
    region = Image.composite(
        Image.new("RGB", size, shape.color),
        result.crop(bounds),
        mask,
    )
    result.paste(region, (left, top))
    return result


def anneal(
    target: Image.Image,
    shape_count: int,
    steps: int,
    seed: int,
    mixed: bool,
    max_shape_scale: float,
    base_color: tuple[int, int, int] | None,
) -> tuple[Image.Image, list[Shape]]:
    rng = random.Random(seed)
    base = Image.new("RGB", target.size, base_color or mean_color(target))
    base_energy = image_energy(base, target)
    shapes: list[Shape] = []
    starting_candidates = 7 if shape_count <= 200 else 4 if shape_count <= 1000 else 2
    report_every = max(12, shape_count // 20)

    for shape_index in range(shape_count):
        progress = shape_index / max(1, shape_count - 1)
        starts = []
        for _ in range(starting_candidates):
            evaluated = evaluate(
                random_shape(
                    rng,
                    progress,
                    shape_count,
                    mixed,
                    max_shape_scale,
                ),
                base,
                target,
                base_energy,
            )
            if evaluated is not None:
                starts.append(evaluated)
        if not starts:
            continue

        current = min(starts, key=lambda item: item.energy)
        best = current
        initial_temperature = max(80.0, abs(base_energy - current.energy) * 0.32)

        for step in range(steps):
            fraction = step / max(1, steps - 1)
            heat = max(0.04, (1.0 - fraction) ** 1.7)
            proposal = evaluate(
                mutate(current.shape, rng, heat),
                base,
                target,
                base_energy,
            )
            if proposal is None:
                continue

            delta = proposal.energy - current.energy
            temperature = max(12.0, initial_temperature * heat)
            accept = delta <= 0 or rng.random() < math.exp(-delta / temperature)
            if accept:
                current = proposal
                if current.energy < best.energy:
                    best = current

        if best.energy < base_energy:
            shapes.append(best.shape)
            base = apply_shape(base, best.shape)
            base_energy = best.energy

        if (
            (shape_index + 1) % report_every == 0
            or shape_index + 1 == shape_count
        ):
            mean_squared_error = base_energy / (WORK_WIDTH * WORK_HEIGHT * 3)
            print(
                f"  {shape_index + 1:>3}/{shape_count} shapes; "
                f"MSE {mean_squared_error:8.1f}",
                flush=True,
            )

    return base, shapes


def write_svg(
    path: Path,
    background: tuple[int, int, int],
    shapes: list[Shape],
    title: str,
) -> None:
    scale_x = SVG_WIDTH / WORK_WIDTH
    scale_y = SVG_HEIGHT / WORK_HEIGHT
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}" '
            f'preserveAspectRatio="none" role="img" '
            f'aria-labelledby="title">'
        ),
        f"  <title id=\"title\">{html.escape(title)}</title>",
    ]
    background_color = "#" + "".join(
        f"{channel:02x}" for channel in background
    )
    lines.append(
        f'  <rect width="{SVG_WIDTH}" height="{SVG_HEIGHT}" '
        f'fill="{background_color}"/>'
    )
    for shape in shapes:
        color = "#" + "".join(f"{channel:02x}" for channel in shape.color)
        opacity = f"{shape.opacity:.2f}".lstrip("0")
        if shape.kind == "ellipse":
            first, second = shape.points
            center_x = round((first[0] + second[0]) * scale_x / 2)
            center_y = round((first[1] + second[1]) * scale_y / 2)
            radius_x = round(abs(second[0] - first[0]) * scale_x / 2)
            radius_y = round(abs(second[1] - first[1]) * scale_y / 2)
            lines.append(
                f'  <ellipse cx="{center_x}" cy="{center_y}" '
                f'rx="{radius_x}" ry="{radius_y}" fill="{color}" '
                f'opacity="{opacity}"/>'
            )
        else:
            points = " ".join(
                f"{round(x * scale_x)},{round(y * scale_y)}"
                for x, y in shape.points
            )
            lines.append(
                f'  <polygon points="{points}" fill="{color}" '
                f'opacity="{opacity}"/>'
            )

    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_preview(
    background: tuple[int, int, int],
    shapes: list[Shape],
    path: Path,
) -> None:
    """Render a supersampled PNG that closely matches the browser SVG."""
    supersampling = 2
    width = SVG_WIDTH * supersampling
    height = SVG_HEIGHT * supersampling
    scale_x = width / WORK_WIDTH
    scale_y = height / WORK_HEIGHT
    canvas = Image.new("RGBA", (width, height), (*background, 255))

    for shape in shapes:
        points = [(x * scale_x, y * scale_y) for x, y in shape.points]
        left = max(0, math.floor(min(point[0] for point in points)))
        top = max(0, math.floor(min(point[1] for point in points)))
        right = min(width, math.ceil(max(point[0] for point in points)) + 1)
        bottom = min(height, math.ceil(max(point[1] for point in points)) + 1)
        if right - left < 2 or bottom - top < 2:
            continue

        size = (right - left, bottom - top)
        mask = Image.new("L", size)
        scaled_shape = replace(shape, points=tuple(points))
        draw_shape(
            mask,
            scaled_shape,
            (left, top),
            255,
        )
        overlay = Image.new(
            "RGBA",
            size,
            (*shape.color, round(255 * shape.opacity)),
        )
        overlay.putalpha(
            Image.eval(
                mask,
                lambda value: round(value * shape.opacity),
            )
        )
        region = canvas.crop((left, top, right, bottom))
        region.alpha_composite(overlay)
        canvas.paste(region, (left, top))

    canvas.resize((SVG_WIDTH, SVG_HEIGHT), Image.Resampling.LANCZOS).save(path)


def validate_configuration() -> None:
    if not 0.0 <= CROP_CENTER_Y <= 1.0:
        raise ValueError("CROP_CENTER_Y must be between 0.0 and 1.0")
    if min(WORK_WIDTH, WORK_HEIGHT, SVG_WIDTH, SVG_HEIGHT) <= 0:
        raise ValueError("image dimensions must be positive")
    if SHAPE_COUNT <= 0 or STEPS_PER_SHAPE <= 0:
        raise ValueError("SHAPE_COUNT and STEPS_PER_SHAPE must be positive")
    if MAX_SHAPE_SCALE <= 0:
        raise ValueError("MAX_SHAPE_SCALE must be positive")
    if BACKGROUND_COLOR is not None and (
        len(BACKGROUND_COLOR) != 3
        or any(not 0 <= channel <= 255 for channel in BACKGROUND_COLOR)
    ):
        raise ValueError("BACKGROUND_COLOR must be None or an RGB tuple")


def generate(source: Image.Image, output_dir: Path) -> None:
    print(
        f"{SHAPE_COUNT} shapes, {STEPS_PER_SHAPE} steps each, "
        f"seed {RANDOM_SEED}",
        flush=True,
    )
    target = crop_banner(source, CROP_CENTER_Y)
    _, shapes = anneal(
        target,
        SHAPE_COUNT,
        STEPS_PER_SHAPE,
        RANDOM_SEED,
        MIXED_SHAPES,
        MAX_SHAPE_SCALE,
        BACKGROUND_COLOR,
    )
    background = BACKGROUND_COLOR or mean_color(target)
    write_svg(
        output_dir / f"{OUTPUT_NAME}.svg",
        background,
        shapes,
        (
            "An annealed geometric interpretation of Ambrogio Lorenzetti's "
            "Effects of Good Government in the City"
        ),
    )
    render_preview(
        background,
        shapes,
        output_dir / f"{OUTPUT_NAME}.png",
    )
    target.resize((SVG_WIDTH, SVG_HEIGHT), Image.Resampling.LANCZOS).save(
        output_dir / f"{OUTPUT_NAME}-crop.jpg",
        quality=88,
        optimize=True,
    )
    print(f"  wrote {len(shapes)} SVG shapes", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="source photograph")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).with_name("output"),
        help="directory for the generated SVG, PNG, and crop",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_configuration()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    source = Image.open(args.source).convert("RGB")
    generate(source, args.output_dir)


if __name__ == "__main__":
    main()
