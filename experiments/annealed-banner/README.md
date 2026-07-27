# Annealed banner experiment

This is an isolated visual experiment. It does not change the live Pelican
theme.

The generator approximates a wide crop with translucent triangles. Each new
triangle is fitted with simulated annealing on a small raster, then recorded as
a vector polygon. The result is a compact SVG with no runtime JavaScript.

The approach sits between the two reference implementations:

- like `shapeme`, it uses general shapes and emits SVG;
- like `zxfy`, it evaluates only the pixels affected by a mutation rather than
  comparing the whole image every time.

## Run it

Install the experiment-only dependency:

```powershell
.\.venv\Scripts\python.exe -m pip install -r experiments\annealed-banner\requirements.txt
```

Generate all candidates:

```powershell
.\.venv\Scripts\python.exe experiments\annealed-banner\generate.py SOURCE.jpg
```

Generate just one:

```powershell
.\.venv\Scripts\python.exe experiments\annealed-banner\generate.py SOURCE.jpg --preset skyline-dense
```

The generated SVG, a supersampled PNG preview, and the corresponding source
crop are written to `output/`.

The `skyline-x10` and `skyline-x100` presets attempt 720 and 7,200 triangles.
They use fewer annealing steps per triangle and progressively smaller geometry,
so their running time and SVG size remain practical. A triangle is kept only
when it improves the approximation, so the final accepted count can be lower
than the preset's search budget.

`skyline-blue-dense` uses a deliberate dark-blue foundation and attempts 3,000
smaller triangles. It keeps a clean rectangular edge while allowing blue to
remain visible between the reconstructed architectural forms.

`city-mixed-tall` uses triangles, quadrilaterals and ellipses on a taller crop.
It starts with a tessellated foundation of opaque triangles instead of a
uniform background rectangle, then anneals 3,000 smaller shapes over it. The
foundation has an irregular lower boundary; only complete triangles that cross
into the transparent fringe are kept. No fringe triangle is clipped at the
bottom.

## Source used for the first trial

Ambrogio Lorenzetti, *Effects of Good Government in the city* (1338–1339).
The high-resolution Google Art Project reproduction is available from
Wikimedia Commons and is marked there as a faithful reproduction of a
public-domain work:

https://commons.wikimedia.org/wiki/File:Ambrogio_Lorenzetti_-_Effects_of_Good_Government_in_the_city_-_Google_Art_Project.jpg

The 4.55 MB source photograph is deliberately not copied into this repository.
