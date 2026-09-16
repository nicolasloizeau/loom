"""Render settings (the "render.style" block of a settings file).

The defaults are the chosen look. Lengths are in thread spacings (the
distance between two neighbouring threads). This module does not import
Blender, so the settings can be read without it.
"""
from dataclasses import dataclass


@dataclass
class Style:
    # thread geometry
    gap: float = -0.04           # empty space between neighbouring threads
                                 # (negative: they overlap slightly)
    half_height: float = 0.17    # thread half-thickness
    amp: float = 0.19            # how far a thread rises / sinks at a crossing
    wobble: float = 0.04         # lateral waviness of each thread
    width_jitter: float = 0.04   # per-thread width variation
    slub: float = 0.03           # thickness variation along a thread
    distort: tuple = ((40, 0.3),)  # smooth displacement of the whole cloth:
                                   # [[scale, amplitude], ...]
    drape: tuple = ()            # smooth height undulation of the cloth,
                                 # same format as distort
    # dangling ends
    fringe: float = 2.5          # length of the dangling ends
    fringe_jitter: float = 0.2   # relative randomness of that length
    loose: float = 0.03          # curl of the dangling ends
    wiggle: float = 0.05         # small kinks along the dangling ends
    fray: float = 0.5            # length of the unravelled tip, 0 = clean cut
    fray_plies: int = 3          # plies the tip splits into
    fray_spread: float = 0.12    # how far the plies splay apart
    fray_fibres: int = 3         # stray fibres around each end
    taper: float = 0.0           # 0..1, thinning of unfrayed ends
    # yarn surface
    twist_angle: float = 60.0    # angle of the ply stripes to the thread,
                                 # degrees (90: rings, 0: lengthwise)
    twist_spacing: float = 0.32  # distance between stripes
    twist_contrast: float = 0.35
    fibre_contrast: float = 0.8
    fibre_stretch: float = 20.0  # how elongated the fibre streaks are
    bump: float = 0.6
    roughness: float = 0.8
    sheen: float = 0.6
    color_jitter: float = 0.2    # per-thread brightness variation
    hue_jitter: float = 0.013    # per-thread hue variation (1 = full circle)
    # stray fibres
    fuzz: float = 80.0           # stray fibres per thread spacing of thread
    fuzz_length: float = 0.25    # typical stray fibre length
    fuzz_lift: float = 1.6       # how far fibres lean out of the thread
    fuzz_curl: float = 2.5       # how curly the fibres are
    fuzz_thickness: float = 1.0  # fibre thickness
    # other realism options (tried, off)
    ply_count: int = 0           # 0: one tube; 2 or 3: twisted plies
                                 # (use samples_along ~16)
    subsurface: float = 0.0      # light scattering into the fibres, 0..1
    specular: float = 0.5        # shiny reflection
    heather: float = 0.0         # fibre-level colour variation, 0..1
    saturation: float = 1.0      # colour saturation multiplier
    # lighting
    lighting: str = "area"       # key light: "sun", "area", "spot" or "none"
    light_tilt: float = 50.0     # key light angle from vertical, degrees
    light_azimuth: float = -150.0  # -135: from the top-left, -90: the left
    light_strength: float = 5.64  # irradiance at the light's target
    light_softness: float = 4.0  # sun angular size, degrees
    light_distance: float = 200.0  # area / spot: distance to the target
    light_size: float = 160.0    # area: size; spot: radius
    light_target: tuple = (0.0, 0.0)  # aim point, as a fraction of the
                                      # image half-size from the centre
    spot_angle: float = 60.0     # spot cone angle, degrees
    spot_blend: float = 0.8      # spot edge softness, 0..1
    light_color: tuple = (1.0, 1.0, 1.0)
    fill: float = 0.4            # soft sun from the opposite side
    fill_color: tuple = (1.0, 1.0, 1.0)
    hdri: str = ""               # Blender studio light (e.g. "interior") that
                                 # lights the cloth; the background stays black
    hdri_strength: float = 0.5
    hdri_rotation: float = 0.0   # degrees
    # camera and quality
    view_transform: str = "Standard"  # "AgX": photographic tone mapping
    exposure: float = 0.0        # stops
    samples: int = 64            # Cycles samples
    denoise: bool = True
    margin: float = None         # border around the fringe; None: automatic
                                 # (same share of the image at any width)
    samples_along: int = 8       # mesh rings per crossing along a thread
    samples_around: int = 12     # mesh vertices around a thread
