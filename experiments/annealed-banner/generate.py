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


WORK_WIDTH = 384
WORK_HEIGHT = 60
SVG_WIDTH = 1280
SVG_HEIGHT = 200


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


@dataclass(frozen=True)
class Preset:
    name: str
    description: str
    crop_center: float
    shapes: int
    steps: int
    seed: int
    mixed: bool = False
    work_height: int = 60
    svg_height: int = 200
    fringe: int = 0
    max_shape_scale: float = 1.0
    mesh_columns: int = 0
    mesh_rows: int = 0
    background: tuple[int, int, int] | None = None


PRESETS = (
    Preset(
        name="skyline-loose",
        description="72 large triangles, focused on the skyline",
        crop_center=0.20,
        shapes=72,
        steps=180,
        seed=1348,
    ),
    Preset(
        name="skyline-dense",
        description="160 smaller triangles, focused on the skyline",
        crop_center=0.20,
        shapes=160,
        steps=150,
        seed=1339,
    ),
    Preset(
        name="skyline-x10",
        description="720 triangles, ten times the loose skyline",
        crop_center=0.20,
        shapes=720,
        steps=48,
        seed=1348,
    ),
    Preset(
        name="skyline-x100",
        description="7,200 triangles, one hundred times the loose skyline",
        crop_center=0.20,
        shapes=7200,
        steps=12,
        seed=1348,
    ),
    Preset(
        name="skyline-blue-dense",
        description="3,000 smaller triangles over a dark blue background",
        crop_center=0.20,
        shapes=3000,
        steps=20,
        seed=1348,
        max_shape_scale=0.70,
        background=(23, 54, 95),
    ),
    Preset(
        name="street",
        description="120 triangles, lowered to include the street and figures",
        crop_center=0.50,
        shapes=120,
        steps=160,
        seed=1338,
    ),
    Preset(
        name="city-mixed-tall",
        description=(
            "3,000 smaller shapes over an opaque triangular foundation"
        ),
        crop_center=0.22,
        shapes=3000,
        steps=20,
        seed=1340,
        mixed=True,
        work_height=84,
        svg_height=280,
        fringe=70,
        max_shape_scale=0.55,
        mesh_columns=32,
        mesh_rows=7,
    ),
)


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


def seed_triangle_mesh(
    target: Image.Image,
    rng: random.Random,
    columns: int,
    rows: int,
    fringe: int,
) -> tuple[Image.Image, int, list[Shape]]:
    """Build an opaque, irregular triangle mosaic instead of a flat rectangle."""
    base = Image.new("RGB", target.size, mean_color(target))
    base_energy = image_energy(base, target)
    shapes: list[Shape] = []
    baseline = WORK_HEIGHT * (SVG_HEIGHT - fringe) / SVG_HEIGHT
    column_width = WORK_WIDTH / columns
    row_height = baseline / rows
    vertices: list[list[tuple[float, float]]] = []

    for row in range(rows + 1):
        vertex_row = []
        for column in range(columns + 1):
            if column == 0:
                x = 0.0
            elif column == columns:
                x = float(WORK_WIDTH)
            else:
                x = column * column_width + rng.uniform(
                    -0.24 * column_width,
                    0.24 * column_width,
                )

            if row == 0:
                y = 0.0
            elif row == rows:
                y = rng.uniform(
                    baseline + 0.10 * (WORK_HEIGHT - baseline),
                    WORK_HEIGHT - 0.4,
                )
            else:
                y = row * row_height + rng.uniform(
                    -0.22 * row_height,
                    0.22 * row_height,
                )
            vertex_row.append((x, y))
        vertices.append(vertex_row)

    for row in range(rows):
        for column in range(columns):
            top_left = vertices[row][column]
            top_right = vertices[row][column + 1]
            bottom_left = vertices[row + 1][column]
            bottom_right = vertices[row + 1][column + 1]
            if (row + column) % 2:
                triangles = (
                    (top_left, top_right, bottom_left),
                    (top_right, bottom_right, bottom_left),
                )
            else:
                triangles = (
                    (top_left, top_right, bottom_right),
                    (top_left, bottom_right, bottom_left),
                )

            for points in triangles:
                evaluated = evaluate(
                    Shape(kind="polygon", points=points, opacity=1.0),
                    base,
                    target,
                    base_energy,
                )
                if evaluated is None:
                    continue
                shapes.append(evaluated.shape)
                base = apply_shape(base, evaluated.shape)
                base_energy = evaluated.energy

    return base, base_energy, shapes


def anneal(
    target: Image.Image,
    shape_count: int,
    steps: int,
    seed: int,
    mixed: bool,
    max_shape_scale: float,
    mesh_columns: int,
    mesh_rows: int,
    fringe: int,
    base_color: tuple[int, int, int] | None,
) -> tuple[Image.Image, list[Shape]]:
    rng = random.Random(seed)
    if mesh_columns and mesh_rows:
        base, base_energy, shapes = seed_triangle_mesh(
            target,
            rng,
            mesh_columns,
            mesh_rows,
            fringe,
        )
        print(f"  seeded {len(shapes)} opaque mesh triangles", flush=True)
    else:
        base = Image.new("RGB", target.size, base_color or mean_color(target))
        base_energy = image_energy(base, target)
        shapes = []
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


def fringe_mode(shape: Shape, fringe: int) -> str:
    """Keep the body solid and allow only complete triangles into the fringe."""
    if fringe <= 0:
        return "normal"

    baseline = WORK_HEIGHT * (SVG_HEIGHT - fringe) / SVG_HEIGHT
    minimum = min(point[1] for point in shape.points)
    maximum = max(point[1] for point in shape.points)
    if maximum <= baseline:
        return "normal"
    if (
        shape.kind == "polygon"
        and len(shape.points) == 3
        and minimum < baseline
        and maximum <= WORK_HEIGHT
    ):
        return "tip"
    return "skip"


def write_svg(
    path: Path,
    background: tuple[int, int, int] | None,
    shapes: list[Shape],
    title: str,
    fringe: int,
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
    if background is not None:
        background_color = "#" + "".join(
            f"{channel:02x}" for channel in background
        )
        lines.append(
            f'  <rect width="{SVG_WIDTH}" height="{SVG_HEIGHT - fringe}" '
            f'fill="{background_color}"/>'
        )
    for shape in shapes:
        edge = fringe_mode(shape, fringe)
        if edge == "skip":
            continue
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
    background: tuple[int, int, int] | None,
    shapes: list[Shape],
    path: Path,
    fringe: int,
) -> None:
    """Render a supersampled PNG that closely matches the browser SVG."""
    supersampling = 2
    width = SVG_WIDTH * supersampling
    height = SVG_HEIGHT * supersampling
    scale_x = width / WORK_WIDTH
    scale_y = height / WORK_HEIGHT
    canvas = Image.new("RGBA", (width, height))
    if background is not None:
        background_height = height - fringe * supersampling
        ImageDraw.Draw(canvas).rectangle(
            (0, 0, width, background_height),
            fill=(*background, 255),
        )

    for shape in shapes:
        edge = fringe_mode(shape, fringe)
        if edge == "skip":
            continue
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


def run_preset(source: Image.Image, preset: Preset, output_dir: Path) -> None:
    global WORK_HEIGHT, SVG_HEIGHT

    WORK_HEIGHT = preset.work_height
    SVG_HEIGHT = preset.svg_height
    print(f"{preset.name}: {preset.description}", flush=True)
    target = crop_banner(source, preset.crop_center)
    _, shapes = anneal(
        target,
        preset.shapes,
        preset.steps,
        preset.seed,
        preset.mixed,
        preset.max_shape_scale,
        preset.mesh_columns,
        preset.mesh_rows,
        preset.fringe,
        preset.background,
    )
    background = preset.background or mean_color(target)
    svg_background = None if preset.mesh_columns else background
    write_svg(
        output_dir / f"{preset.name}.svg",
        svg_background,
        shapes,
        (
            "An annealed geometric interpretation of Ambrogio Lorenzetti's "
            "Effects of Good Government in the City"
        ),
        preset.fringe,
    )
    render_preview(
        svg_background,
        shapes,
        output_dir / f"{preset.name}.png",
        preset.fringe,
    )
    target.resize((SVG_WIDTH, SVG_HEIGHT), Image.Resampling.LANCZOS).save(
        output_dir / f"{preset.name}-crop.jpg",
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
        help="directory for SVG and PNG comparisons",
    )
    parser.add_argument(
        "--preset",
        action="append",
        choices=[preset.name for preset in PRESETS],
        help="generate only this preset; may be repeated",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    source = Image.open(args.source).convert("RGB")
    selected = set(args.preset or ())
    presets = [preset for preset in PRESETS if not selected or preset.name in selected]

    for preset in presets:
        run_preset(source, preset, args.output_dir)


if __name__ == "__main__":
    main()
