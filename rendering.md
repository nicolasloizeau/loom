# Rendering: what we tried and what we chose

> History of the exploration. The scripts named below (`render.py` as it
> was, `variants.py`, `densities.py`, `realism.py`, `grain.py`, ...) were
> replaced by the `loom/` package on 2026-09-16; the chosen look is now the
> set of defaults described in `README.md`. `Style.warp` is now `distort`,
> and the `out/` folders of results named below were removed.

A crossing matrix (`order`, 0 = horizontal thread on top, 1 = vertical on top)
plus a list of horizontal and a list of vertical colours is turned into an
image of woven threads.

## Pipeline

| file | role |
|---|---|
| `weave.py` | flat numpy renderer: one pixel per crossing, 3-cell fringe of loose threads. `save_pattern()` writes `order`, `h_colors`, `v_colors` to `.npz`. |
| `ca.py`, `ca_all.py`, `layers.py`, `ca_more.py` | pattern generators; each writes a `.npz` next to its PNGs. |
| `render.py` | standalone Blender (bpy 5.1, Cycles) renderer for a `.npz`. All look parameters live in the `Style` dataclass; the defaults are the chosen look. |
| `variants.py` | renders sets of `Style` variants on one pattern and builds contact sheets (`--set styles, warps, warps_large, handmade, lighting, stripes, lighting2`). Earlier sets are pinned to the defaults they were rendered with, so they still reproduce. |
| `densities.py` | renders one pattern at several threads-per-edge in the 4:5 format, keeping the black margin at the same share of the image. |

The renderer is kept separate from the generators on purpose: the generators
only gained a `save_pattern()` call.

## How the Blender renderer works

- **Geometry.** Every thread is a real 3D tube with an elliptical cross
  section. Along its length it rises by `amp` at crossings where it is on top
  and sinks where it is under, with a cosine transition, so floats and dips
  come out naturally. Tubes are built as numpy meshes (8 rings per crossing,
  12 vertices around).
- **Loose ends.** Past the cloth edge a thread flattens, curls (`loose`) and
  kinks (`wiggle`). The tip unravels into thin plies that splay apart and
  taper (`fray`, `fray_plies`, `fray_spread`), with a few stray fibres
  (`fray_fibres`).
- **Irregularity.** Per thread: lateral wobble, width, thickness along the
  length (`slub`), brightness and hue. Over the whole cloth: a smooth random
  displacement field (`warp`) that moves every crossing coherently, and an
  optional height field (`drape`).
- **Yarn shader.** Object colour with helical ply stripes (`twist_angle`,
  `twist_spacing`), fibre streaks stretched along the thread, bump, sheen.
- **Scene.** Orthographic camera straight down, black world, Cycles on the
  CPU at 64 samples with denoising, Standard view transform.
- **Randomness.** One seed drives the thread irregularity, fraying, stray
  fibres, warp and drape. `render()` / `render.py` pick a new seed for every
  render (printed, reproduce with `--seed N`), so no two images share the
  same details. `variants.py` and `densities.py` fix `seed=0` so their
  comparisons differ only by the parameter being compared.

## What we tuned, round by round

| round | options tried | chosen |
|---|---|---|
| Approach | flat numpy shading vs. Blender | Blender, "closer to real" |
| First renders | gaps between threads vs. packed | both kept as options |
| Ends and style, 20 variants (`out/variants`) | clean cut, subtle / wild fray, long / short fringe, tapered, calm ends, thin / chunky / flat-ribbon threads, fuzzy, tight twist, glossy, raking / overhead light, handmade | ends: **short fringe + subtle fray**; rendering: **packed** and **flat ribbon**, with a gap as an option |
| Warp 1 (`out/variants_warps`) | scales 3 to 60, amplitudes 0.06 to 2, multi-scale | strong warps disliked; large scale is right |
| Warp 2 (`out/variants_warps_large`) | scales 20 / 40 / 60 x amplitudes 0.05 to 0.3 | **scale 40, amplitude 0.3** |
| Handmade pass (`out/variants_handmade`) | wobble, width / slub, shade jitter, hue jitter, combinations | **light wobble + 1/3 of the shade jitter + 1/3 of the hue jitter** |
| Lighting 1 (`out/variants_lighting`) | sun, warm / cool sun, window area lights, skylight, spot pool, raking spot, studio / interior HDRI, window + HDRI, drape | **skylight** (big soft area light) |
| Stripes (`out/variants_stripes`) | angle 90 (rings), 60, 45, 30, 15, 0 (lengthwise), -45; spacing 0.18 / 0.32 / 0.5 | **60 degrees, spacing 0.32** |
| Lighting 2 (`out/variants_lighting2`) | skylight too close (hot top-left) and not angled enough: tilt 40 / 50 / 60 x distance 80 / 120 / 200, sharper light, off-centre aim | **tilt 50, distance 200** |
| Format | | **Instagram portrait 4:5, 1080 x 1350** |
| Fringe | | **one thread spacing longer** (1.5 -> 2.5) |
| Density (`out/densities`) | 16, 24, 32, 48, 64, 96, 128 threads across | **48 across** (48 x 62 in 4:5) |
| Randomness | | a **new seed per render** (fixed only for comparison sets) |
| Against the "playdough" look (`out/realism`) | twisted ply geometry, stray fibre fuzz, AgX + 256 samples without denoising, subsurface + heathered colour + desaturation | **fuzz only**; the others looked worse |
| Fuzz (`out/realism_fuzz`) | density 40 / 80 / 150, long, short, thin, thick, wild (curly, standing out), flat | **80 wild**: `fuzz=80, fuzz_curl=2.5, fuzz_lift=1.6` |
| Background (`out/grain/background`, post-process in `grain.py`) | pure black; lifted to 8, 14, 20, 26 / 255; with light, strong or coarse grain; warm charcoal | **lift 26 with grain** (`level=26, grain=0.025`): charcoal instead of pure black; `grain.BG`, applied after the film grain |
| Grain (`out/grain`, post-process in `grain.py`) | fine, fine strong, soft film, coarse film, colour, midtone film, midtone colour | **midtone film**: `amount=0.07, size=1.5, midtones=1` (soft grain on the cloth, pure black stays clean); `grain.FILM`, applied by `render_best.py` |

## The chosen look (`Style()` defaults)

Units are thread spacings unless noted.

| group | parameter | value | meaning |
|---|---|---|---|
| threads | `gap` | -0.04 | packed, slight overlap (`--gap 0.15` adds space) |
| | `half_height` | 0.17 | thread half-thickness |
| | `amp` | 0.19 | rise / sink at crossings |
| | preset `RIBBON` | `half_height=0.1, amp=0.12, twist_contrast=0.1` | flat-ribbon alternative (`--style ribbon`) |
| irregularity | `wobble` | 0.04 | lateral waviness per thread |
| | `width_jitter`, `slub` | 0.04, 0.03 | width per thread / along the thread |
| | `color_jitter` | 0.2 | brightness variation per thread |
| | `hue_jitter` | 0.013 | hue variation per thread (1 = full circle) |
| | `warp` | `((40, 0.3),)` | smooth displacement: (scale, rms amplitude) |
| ends | `fringe` | 2.5 | length of the loose ends (+-20%) |
| | `loose`, `wiggle` | 0.03, 0.05 | curl and kinks of the ends |
| | `fray`, `fray_plies`, `fray_spread` | 0.5, 3, 0.12 | unravelled tip |
| | `fray_fibres` | 3 | stray fibres per end |
| stripes | `twist_angle`, `twist_spacing` | 60 deg, 0.32 | ply stripes on each thread |
| fibres | `fuzz`, `fuzz_curl`, `fuzz_lift` | 80, 2.5, 1.6 | stray fibres along every thread (hair curves), "80 wild" |
| | `twist_contrast`, `fibre_contrast`, `bump` | 0.35, 0.8, 0.6 | stripe / fibre strength, relief |
| | `roughness`, `sheen` | 0.8, 0.6 | matte cloth with sheen |
| lighting | `lighting` | `"area"` | one big soft area light |
| | `light_tilt`, `light_azimuth` | 50 deg, -150 deg | from the top-left, 50 deg from vertical |
| | `light_distance`, `light_size` | 200, 160 | far and large: even, soft, no hotspot |
| | `light_strength` | 5.64 | irradiance at the centre |
| | `fill` | 0.4 | soft sun from the opposite side |
| framing | `margin` | 2.5 | black border around the fringe |

Render command for the chosen output:

```
python3 render.py pattern.npz --crop 48x62 --aspect 4:5 --size 1350
```

About 35 to 40 s per image on this machine (8 CPU cores, 64 samples).

## Lessons along the way

- A pixel image cannot be turned back into a crossing matrix when the two
  palettes share colours, hence the `.npz` files.
- Strong width or slub variation opens black slivers between packed threads.
- Warp amplitudes above about 0.4 at small scales make the cloth fold over
  itself; large scales at small amplitudes read as natural.
- A nearby area light gives a hotspot on the near corner; moving it far away
  (size growing with distance) keeps the angle and softness without it.
- With the light further and lower, its strength must rise (by
  cos 25 / cos tilt) to keep the same brightness.
- Contact sheets above about 6 MB fail to upload; JPEG copies are sent.

## Not decided yet

- Palettes: suggested 3 to 4 colours per direction, different counts across
  and down, and no colours shared between the two sets so the pattern reads.
