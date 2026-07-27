# Annealed banner

The generator approximates a wide crop with translucent triangles. Each new
triangle is fitted with simulated annealing on a small raster, then recorded as
a vector polygon. The result is a compact SVG with no runtime JavaScript.

## Adjust the result

All visual controls are in the `Configuration` section near the top of
`generate.py`. The most useful ones are:

- `CROP_CENTER_Y`: moves the source crop up or down;
- `SHAPE_COUNT`: controls detail, running time, and SVG size;
- `STEPS_PER_SHAPE`: spends more or less time optimizing each shape;
- `MAX_SHAPE_SCALE`: limits the size of the largest shapes;
- `MIXED_SHAPES`: switches between triangles and a mixture of shape types;
- `BACKGROUND_COLOR`: uses the crop's mean color or a chosen RGB foundation;
- `RANDOM_SEED`: produces a different deterministic arrangement.

The working and SVG dimensions are there too, but their aspect ratios should
remain equal.

## Run it

Install the generator's only dependency:

```powershell
.\.venv\Scripts\python.exe -m pip install -r annealed-banner\requirements.txt
```

Then generate the banner:

```powershell
.\.venv\Scripts\python.exe annealed-banner\generate.py annealed-banner\codex-buon-governo-source.jpg
```

This writes `banner.svg`, a supersampled `banner.png` preview, and
`banner-crop.jpg` to `annealed-banner/output/`. Open `preview.html` to see the
result in a mock masthead. A proposed shape is kept only when it improves the
approximation, so the accepted count can be lower than `SHAPE_COUNT`.

To use a result on the site, copy `banner.svg` over
`theme/static/images/banner-annealed.svg`.

## Source used for the first trial

Ambrogio Lorenzetti, *Effects of Good Government in the city* (1338–1339).
The high-resolution Google Art Project reproduction is available from
Wikimedia Commons and is marked there as a faithful reproduction of a
public-domain work:

https://commons.wikimedia.org/wiki/File:Ambrogio_Lorenzetti_-_Effects_of_Good_Government_in_the_city_-_Google_Art_Project.jpg

The local copy is `codex-buon-governo-source.jpg`; it is input to the generator
and is not embedded in the SVG.
