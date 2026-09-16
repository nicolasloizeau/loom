"""Render a drawdown as woven threads with Blender (Cycles, on the CPU).

Every thread is a 3D tube that rises where it is on top at a crossing and
sinks where it is under, with loose frayed ends, stray fibres, a yarn
shader, and a soft area light, seen from straight above on black.
"""
import math
import os
import warnings

import bpy
import numpy as np
from mathutils import Euler, Vector

from .colors import hex_to_rgb

warnings.filterwarnings("ignore", message=".*use_nodes.*")


def srgb_to_linear(hex_color):
    c = np.array(hex_to_rgb(hex_color)) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def smooth_noise(rng, n_waves=4, min_period=3.0, max_period=15.0):
    """Random smooth 1D noise function (sum of sines), roughly unit amplitude."""
    periods = rng.uniform(min_period, max_period, n_waves)
    phases = rng.uniform(0, 2 * np.pi, n_waves)
    norm = np.sqrt(n_waves / 2)
    return lambda t: (np.sin(2 * np.pi * np.asarray(t)[..., None] / periods
                             + phases).sum(-1) / norm)


def displacement_field(layers, rng, n_modes=24):
    """Smooth random 2D displacement field, as a function of (N, 2) positions.

    Each (scale, amp) layer is a sum of random plane waves with wavelengths
    around `scale`, giving an rms displacement of `amp` along each axis.
    """
    waves = []
    for scale, amp in layers:
        k = 2 * np.pi / scale * rng.uniform(0.7, 1.3, n_modes)
        angle = rng.uniform(0, 2 * np.pi, n_modes)
        K = np.stack([k * np.cos(angle), k * np.sin(angle)], axis=1)
        phases = rng.uniform(0, 2 * np.pi, (2, n_modes))
        waves.append((K, phases, amp * np.sqrt(2 / n_modes)))

    def field(xy):
        d = np.zeros_like(xy)
        for K, phases, a in waves:
            arg = xy @ K.T
            d[:, 0] += a * np.sin(arg + phases[0]).sum(1)
            d[:, 1] += a * np.sin(arg + phases[1]).sum(1)
        return d
    return field


def taper(dist_to_tip, length, amount):
    """Radius factor that thins by `amount` over the last `length` to a tip."""
    if amount <= 0 or length <= 0:
        return np.ones_like(dist_to_tip)
    return 1 - amount * np.clip(1 - dist_to_tip / length, 0, 1) ** 2


def ordered(t, *arrays):
    """Broadcast per-sample arrays to t's shape, with t increasing."""
    arrays = [np.broadcast_to(x, t.shape) for x in arrays]
    if t[-1] < t[0]:
        return (t[::-1], *[x[::-1] for x in arrays])
    return (t, *arrays)


def thread_strands(on_top, s, rng):
    """Strands making up one thread, each as (t, lateral, z, rw, rh) arrays.

    The thread is parametrised by t in crossing units, crossing k at t = k.
    It is raised by `amp` where it is on top and lowered where it is under,
    with a cosine transition. Past the cloth edge it flattens out, curls and
    kinks. With `fray`, the last part of each end splits into thin plies that
    splay apart; `fray_fibres` adds stray fibres around each end.
    """
    n = len(on_top)
    z_c = np.where(on_top, s.amp, -s.amp)
    curl = rng.normal(0, s.loose, 2)
    offset = rng.normal(0, s.wobble)
    wobble, kink, width = (smooth_noise(rng), smooth_noise(rng, 3, 1.5, 4.0),
                           smooth_noise(rng))
    base_rw = (1 - s.gap) / 2 * (1 + rng.normal(0, s.width_jitter))

    def centre(t):
        tc = np.clip(t, 0, n - 1)
        j = np.minimum(tc.astype(int), max(n - 2, 0))
        w = (1 - np.cos(np.pi * (tc - j))) / 2
        z = z_c[j] * (1 - w) + z_c[np.minimum(j + 1, n - 1)] * w
        past = np.maximum(-t, t - (n - 1)).clip(min=0)  # distance past edge
        z = z * np.exp(-past / 0.5)
        lat = (offset + s.wobble * wobble(t)
               + np.where(t < 0, curl[0], curl[1]) * past ** 2
               + s.wiggle * (past / s.fringe) * kink(t))
        return lat, z, base_rw * (1 + s.slub * width(t))

    def samples(length, density=1.0):
        return max(4, int(round(length * s.samples_along * density)) + 1)

    ends = s.fringe * (1 + s.fringe_jitter * rng.uniform(-1, 1, 2))
    fray = np.minimum(s.fray * rng.uniform(0.6, 1.4, 2), ends - 0.3)
    t_lo, t_hi = -ends[0], n - 1 + ends[1]
    a, b = t_lo + fray[0], t_hi - fray[1]  # the intact part of the thread

    t = np.linspace(a, b, samples(b - a))
    lat, z, rw = centre(t)
    k = taper(np.minimum(t - t_lo, t_hi - t), 0.8,
              s.taper if s.fray <= 0 else 0)
    strands = [ordered(t, lat, z, rw * k, s.half_height * k)]

    for start, sign, fr in ((a, -1, fray[0]), (b, 1, fray[1])):
        if s.fray > 0:
            base_ang = rng.uniform(0, 2 * np.pi)
            for p in range(s.fray_plies):
                ang = (base_ang + 2 * np.pi * p / s.fray_plies
                       + rng.normal(0, 0.3))
                length = fr * rng.uniform(0.6, 1.1)
                d = np.linspace(-0.3, length, samples(length + 0.3))
                tt = start + sign * d
                lat, z, rw = centre(tt)
                grow = (d.clip(min=0) / fr) ** 1.5
                spread = s.fray_spread * rng.uniform(0.5, 1.5) * grow
                lat = (lat + (0.5 * rw + spread) * np.cos(ang)
                       + 0.05 * grow * smooth_noise(rng, 3, 0.8, 2.5)(d))
                z = z + 0.5 * s.half_height * np.sin(ang)
                k = 0.55 * taper(length - d, 0.5 * length, 0.7)
                strands.append(ordered(tt, lat, z, rw * k, s.half_height * k))
        for _ in range(s.fray_fibres):
            begin = rng.uniform(-0.5, 0.5) * max(fr, 0.5)
            length = max(fr, 0.8) * rng.uniform(0.4, 1.2)
            d = np.linspace(begin, begin + length, samples(length, 1.5))
            tt = start + sign * d
            lat, z, rw = centre(tt)
            rel = d - begin
            ang = np.clip(rng.normal(0, 0.5), -1.0, 1.0)
            lat = (lat + rng.uniform(-0.6, 0.6) * rw + np.tan(ang) * rel
                   + 0.08 * rel * smooth_noise(rng, 3, 0.5, 2.0)(d))
            z = z + rng.uniform(-0.3, 0.8) * s.half_height
            r = rng.uniform(0.02, 0.045) * taper(length - rel, 0.5 * length,
                                                 0.8)
            strands.append(ordered(tt, lat, z, r, r))
    return strands


def frames(points, side):
    """Tangent, horizontal side and up directions along a path."""
    T = np.gradient(points, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    U = np.cross(T, side)
    U /= np.linalg.norm(U, axis=1, keepdims=True)
    return T, np.cross(U, T), U


def tube(points, side, rw, rh, u, n_around):
    """Sweep an elliptical cross-section (half-axes rw, rh) along `points`.

    `side` is the horizontal direction across the thread. The ring seam is
    at the bottom of the thread, where it is never seen.
    Returns vertices, quad faces and per-vertex (u, v) coordinates, with u
    along the thread and v around it.
    """
    _, S, U = frames(points, side)
    theta = np.linspace(-np.pi / 2, 1.5 * np.pi, n_around + 1)
    verts = (points[:, None, :]
             + S[:, None, :] * (rw[:, None] * np.cos(theta))[:, :, None]
             + U[:, None, :] * (rh[:, None] * np.sin(theta))[:, :, None])

    m, r = len(points), n_around + 1
    i, k = np.meshgrid(np.arange(m - 1), np.arange(n_around), indexing="ij")
    a = (i * r + k).ravel()
    faces = np.stack([a, a + 1, a + r + 1, a + r], axis=1)

    uv = np.stack(np.broadcast_arrays(u[:, None], (theta + np.pi / 2)
                                      / (2 * np.pi)), axis=-1)
    return verts.reshape(-1, 3), faces, uv.reshape(-1, 2)


def plies(points, side, rw, rh, t, s):
    """Split a thread into s.ply_count helical plies twisted at
    s.twist_angle, together filling the thread's cross-section.
    Returns (centre points, half-width, half-height) per ply."""
    n = s.ply_count
    q = 0.55 if n == 2 else 0.5  # ply size relative to the thread
    _, S, U = frames(points, side)
    off_w, off_h = rw * (1 - q), rh * (1 - q)
    tan = math.tan(math.radians(s.twist_angle))
    tan = tan if abs(tan) > 1e-3 else 1e-3
    pitch = 2 * np.pi * off_w.mean() / tan  # length of one full turn
    parts = []
    for p in range(n):
        phi = 2 * np.pi * (t / pitch + p / n)
        centre = (points + S * (off_w * np.cos(phi))[:, None]
                  + U * (off_h * np.sin(phi))[:, None])
        parts.append((centre, rw * q, rh * q))
    return parts


def fuzz_curves(points, side, rw, rh, t, s, rng, n_points=4):
    """Stray fibres rooted on a thread's surface: mostly along the thread,
    leaning out of it, curled. Returns positions (n, n_points, 3) and radii
    (n, n_points)."""
    n = rng.poisson(s.fuzz * (t[-1] - t[0]))
    T, S, U = frames(points, side)
    i = rng.integers(0, len(t), n)
    theta = rng.uniform(0, 2 * np.pi, n)
    out = S[i] * np.cos(theta)[:, None] + U[i] * np.sin(theta)[:, None]
    root = (points[i] + S[i] * (rw[i] * np.cos(theta))[:, None]
            + U[i] * (rh[i] * np.sin(theta))[:, None])
    d = (T[i] * rng.uniform(-1, 1, n)[:, None]
         + out * (s.fuzz_lift * rng.uniform(0.3, 1.0, n))[:, None]
         + rng.normal(0, 0.3, (n, 3)))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    length = s.fuzz_length * rng.uniform(0.4, 1.6, n)[:, None, None]
    f = np.linspace(0, 1, n_points)[None, :, None]
    curl = s.fuzz_curl * rng.normal(0, 0.3, (n, 1, 3))
    pos = root[:, None, :] + length * (d[:, None, :] * f + curl * f ** 2)
    radius = (s.fuzz_thickness * rng.uniform(0.006, 0.012, (n, 1))
              * (1 - 0.7 * f[:, :, 0]))
    return pos, radius


def thread_mesh(strands, to_xyz, side, s):
    """Merge the tubes of all strands of a thread into one mesh. With
    ply_count, the thread body (the first strand) is built from plies."""
    verts, faces, uvs, offset = [], [], [], 0
    for k, (t, lat, z, rw, rh) in enumerate(strands):
        points = to_xyz(t, lat, z)
        parts = ([(points, rw, rh)] if k or s.ply_count < 2
                 else plies(points, side, rw, rh, t, s))
        for pts, pw, ph in parts:
            n_around = s.samples_around if pw.max() > 0.1 else 6
            v, f, uv = tube(pts, side, pw, ph, t, n_around)
            verts.append(v)
            faces.append(f + offset)
            uvs.append(uv)
            offset += len(v)
    return np.concatenate(verts), np.concatenate(faces), np.concatenate(uvs)


def add_mesh(name, verts, faces, uv, color, mat, collection):
    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(len(verts))
    mesh.vertices.foreach_set("co", verts.astype(np.float32).ravel())
    mesh.loops.add(faces.size)
    mesh.loops.foreach_set("vertex_index", faces.astype(np.int32).ravel())
    mesh.polygons.add(len(faces))
    mesh.polygons.foreach_set("loop_start",
                              np.arange(0, faces.size, 4, dtype=np.int32))
    layer = mesh.uv_layers.new(name="UVMap")
    layer.data.foreach_set("uv", uv[faces.ravel()].astype(np.float32).ravel())
    mesh.update(calc_edges=True)
    mesh.shade_smooth()
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    obj.color = (*color, 1.0)
    collection.objects.link(obj)


def add_curves(name, pos, radius, color, mat, collection):
    """Add thin fibres as a hair curves object, rendered natively by Cycles."""
    n, k, _ = pos.shape
    if n == 0:
        return
    curves = bpy.data.hair_curves.new(name)
    curves.add_curves([k] * n)
    curves.position_data.foreach_set("vector", pos.astype(np.float32).ravel())
    rad = curves.attributes.new("radius", "FLOAT", "POINT")
    rad.data.foreach_set("value", radius.astype(np.float32).ravel())
    curves.materials.append(mat)
    obj = bpy.data.objects.new(name, curves)
    obj.color = (*color, 1.0)
    collection.objects.link(obj)


def thread_material(s):
    """Yarn shader: object color with ply twist, fibre streaks and sheen."""
    mat = bpy.data.materials.new("thread")
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]

    def op(operation, a, b=None):
        n = nodes.new("ShaderNodeMath")
        n.operation = operation
        for k, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                n.inputs[k].default_value = x
            else:
                links.new(x, n.inputs[k])
        return n.outputs[0]

    def lerp01(x, contrast):
        """Map x in [0, 1] to [1 - contrast/2, 1 + contrast/2]."""
        return op("ADD", op("MULTIPLY", x, contrast), 1 - contrast / 2)

    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(nodes.new("ShaderNodeTexCoord").outputs["UV"], sep.inputs[0])
    u, v = sep.outputs["X"], sep.outputs["Y"]
    info = nodes.new("ShaderNodeObjectInfo")
    rand = info.outputs["Random"]

    # Ply stripes at twist_angle to the thread, twist_spacing apart, with a
    # random phase per thread. `around` need not be an integer: the seam is
    # hidden under the thread.
    a, b = (1 - s.gap) / 2, s.half_height
    perimeter = math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))
    angle = math.radians(s.twist_angle)
    along = math.sin(angle) / s.twist_spacing
    around = perimeter * math.cos(angle) / s.twist_spacing
    phase = op("ADD", op("ADD", op("MULTIPLY", u, along),
                         op("MULTIPLY", v, around)),
               op("MULTIPLY", rand, 10.0))
    twist = op("ADD", op("MULTIPLY", op("SINE", op("MULTIPLY", phase,
                                                     2 * math.pi)), 0.5), 0.5)

    # Fibre streaks: noise stretched along the thread.
    comb = nodes.new("ShaderNodeCombineXYZ")
    links.new(op("MULTIPLY", u, 1.5), comb.inputs[0])
    links.new(op("MULTIPLY", v, 1.5 * s.fibre_stretch), comb.inputs[1])
    links.new(op("MULTIPLY", rand, 100.0), comb.inputs[2])
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.0
    noise.inputs["Detail"].default_value = 6.0
    links.new(comb.outputs[0], noise.inputs["Vector"])
    fibre = noise.outputs["Fac"]

    shade = op("MULTIPLY",
               op("MULTIPLY", lerp01(twist, s.twist_contrast),
                  lerp01(fibre, s.fibre_contrast)),
               lerp01(rand, s.color_jitter))
    color = nodes.new("ShaderNodeVectorMath")
    color.operation = "SCALE"
    links.new(info.outputs["Color"], color.inputs[0])
    links.new(shade, color.inputs["Scale"])

    # Per-thread hue shift, from a second random number derived from `rand`.
    rand2 = op("FRACT", op("MULTIPLY", rand, 97.31))
    hsv = nodes.new("ShaderNodeHueSaturation")
    links.new(op("ADD", op("MULTIPLY", op("SUBTRACT", rand2, 0.5),
                           s.hue_jitter), 0.5), hsv.inputs["Hue"])
    links.new(color.outputs[0], hsv.inputs["Color"])
    links.new(hsv.outputs["Color"], bsdf.inputs["Base Color"])

    # Heathered yarn: fibre-level variation of saturation and brightness,
    # from fine noise streaks along the thread; plus overall saturation.
    comb2 = nodes.new("ShaderNodeCombineXYZ")
    links.new(op("MULTIPLY", u, 4.0), comb2.inputs[0])
    links.new(op("MULTIPLY", v, 80.0), comb2.inputs[1])
    links.new(op("MULTIPLY", rand, 50.0), comb2.inputs[2])
    noise2 = nodes.new("ShaderNodeTexNoise")
    noise2.inputs["Scale"].default_value = 1.0
    noise2.inputs["Detail"].default_value = 2.0
    links.new(comb2.outputs[0], noise2.inputs["Vector"])
    fleck = op("SUBTRACT", noise2.outputs["Fac"], 0.5)
    links.new(op("MULTIPLY", op("ADD", op("MULTIPLY", fleck, 2 * s.heather),
                                1.0), s.saturation), hsv.inputs["Saturation"])
    links.new(op("ADD", op("MULTIPLY", fleck, s.heather), 1.0),
              hsv.inputs["Value"])

    bsdf.inputs["Subsurface Weight"].default_value = s.subsurface
    bsdf.inputs["Subsurface Scale"].default_value = 0.05
    bsdf.inputs["Specular IOR Level"].default_value = s.specular

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = s.bump
    bump.inputs["Distance"].default_value = 0.03
    links.new(op("ADD", op("MULTIPLY", twist, 0.6), op("MULTIPLY", fibre, 0.6)),
              bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    bsdf.inputs["Roughness"].default_value = s.roughness
    bsdf.inputs["Sheen Weight"].default_value = s.sheen
    bsdf.inputs["Sheen Roughness"].default_value = 0.35
    return mat


def new_scene(ext_x, ext_y, size, s):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = s.samples
    scene.cycles.use_denoising = s.denoise
    scene.cycles.max_bounces = 4
    longest = max(ext_x, ext_y)
    scene.render.resolution_x = round(size * ext_x / longest)
    scene.render.resolution_y = round(size * ext_y / longest)
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = s.view_transform
    scene.view_settings.exposure = s.exposure

    world = bpy.data.worlds.new("black")
    world.color = (0, 0, 0)
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    nodes, links = world.node_tree.nodes, world.node_tree.links
    black = nodes.get("Background") or nodes.new("ShaderNodeBackground")
    black.inputs["Strength"].default_value = 0
    out = nodes.get("World Output") or nodes.new("ShaderNodeOutputWorld")
    links.new(black.outputs[0], out.inputs["Surface"])
    if s.hdri:
        # The studio light lights the cloth, but camera rays see black.
        env = nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(os.path.join(
            bpy.utils.system_resource("DATAFILES", path="studiolights/world"),
            s.hdri + ".exr"))
        mapping = nodes.new("ShaderNodeMapping")
        mapping.inputs["Rotation"].default_value[2] = math.radians(
            s.hdri_rotation)
        links.new(nodes.new("ShaderNodeTexCoord").outputs["Generated"],
                  mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], env.inputs["Vector"])
        lit = nodes.new("ShaderNodeBackground")
        lit.inputs["Strength"].default_value = s.hdri_strength
        links.new(env.outputs["Color"], lit.inputs["Color"])
        mix = nodes.new("ShaderNodeMixShader")
        links.new(nodes.new("ShaderNodeLightPath").outputs["Is Camera Ray"],
                  mix.inputs["Fac"])
        links.new(lit.outputs[0], mix.inputs[1])
        links.new(black.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], out.inputs["Surface"])
    scene.world = world

    cam = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = longest
    cam.location = (0, 0, 10)
    scene.collection.objects.link(cam)
    scene.camera = cam

    def add_light(name, kind, energy, color, location, rotation):
        light = bpy.data.lights.new(name, kind)
        light.energy = energy
        light.color = color
        obj = bpy.data.objects.new(name, light)
        obj.location = location
        obj.rotation_euler = rotation
        scene.collection.objects.link(obj)
        return light

    key = Euler((math.radians(s.light_tilt), 0, math.radians(s.light_azimuth)))
    if s.lighting == "sun":
        sun = add_light("key", "SUN", s.light_strength, s.light_color,
                        (0, 0, 0), key)
        sun.angle = math.radians(s.light_softness)
    elif s.lighting in ("area", "spot"):
        # A light at a finite distance: brightness and angle vary across
        # the cloth. Power is set for an irradiance of light_strength at the
        # target.
        target = Vector((s.light_target[0] * ext_x / 2,
                         s.light_target[1] * ext_y / 2, 0))
        loc = target + key.to_matrix() @ Vector((0, 0, s.light_distance))
        aim = (target - loc).to_track_quat("-Z", "Y").to_euler()
        d2 = s.light_distance ** 2
        if s.lighting == "area":
            light = add_light("key", "AREA", s.light_strength * math.pi * d2,
                              s.light_color, loc, aim)
            light.size = s.light_size
        else:
            light = add_light("key", "SPOT",
                              s.light_strength * 4 * math.pi * d2,
                              s.light_color, loc, aim)
            light.spot_size = math.radians(s.spot_angle)
            light.spot_blend = s.spot_blend
            light.shadow_soft_size = s.light_size
    if s.fill > 0:
        fill = add_light("fill", "SUN", s.fill, s.fill_color, (0, 0, 0),
                         (math.radians(20), 0,
                          math.radians(s.light_azimuth + 180)))
        fill.angle = math.radians(40)
    return scene


def render(drawdown, warp, weft, path, style, size, aspect, seed):
    """Render a drawdown (1 = warp on top) to the image file `path`.

    `warp` / `weft` are the vertical / horizontal thread colours, repeated
    across the columns / down the rows. `size` is the longest image side in
    pixels; `aspect` (width / height) pads the frame to that ratio. `seed`
    drives every random detail (thread irregularity, fraying, fibres,
    distortion, drape).
    """
    s = style
    rng = np.random.default_rng(seed)
    distort = displacement_field(s.distort, np.random.default_rng(seed + 1))
    drape = displacement_field(s.drape, np.random.default_rng(seed + 2))
    fuzz_rng = np.random.default_rng(seed + 3)
    H, W = drawdown.shape
    border = s.fringe + s.margin + 2 * sum(amp for _, amp in s.distort)
    ext_x = W - 1 + 2 * border
    ext_y = H - 1 + 2 * border
    if aspect:
        if ext_x / ext_y < aspect:
            ext_x = ext_y * aspect
        else:
            ext_y = ext_x / aspect
    scene = new_scene(ext_x, ext_y, size, s)
    mat = thread_material(s)
    weft_lin = [srgb_to_linear(c) for c in weft]
    warp_lin = [srgb_to_linear(c) for c in warp]
    x0, y0 = -(W - 1) / 2, (H - 1) / 2
    across_weft = np.array([0.0, 1.0, 0.0])
    across_warp = np.array([1.0, 0.0, 0.0])

    def deform(p):
        """Apply the distortion and drape fields to (n, 3) points, in place."""
        xy = p[:, :2].copy()
        p[:, :2] += distort(xy)
        p[:, 2] += drape(xy)[:, 0]

    def add_thread(name, strands, to_xyz, across, color):
        verts, faces, uv = thread_mesh(strands, to_xyz, across, s)
        deform(verts)
        add_mesh(name, verts, faces, uv, color, mat, scene.collection)
        if s.fuzz > 0:
            t, lat, z, rw, rh = strands[0]
            pos, radius = fuzz_curves(to_xyz(t, lat, z), across, rw, rh, t,
                                      s, fuzz_rng)
            deform(pos.reshape(-1, 3))
            add_curves(name + "_fuzz", pos, radius, color, mat,
                       scene.collection)

    for i in range(H):  # weft threads, top row first
        add_thread(f"weft{i}", thread_strands(drawdown[i] == 0, s, rng),
                   lambda t, lat, z: np.stack([x0 + t, y0 - i + lat, z],
                                              axis=1),
                   across_weft, weft_lin[i % len(weft_lin)])
    for j in range(W):  # warp threads, left column first
        add_thread(f"warp{j}", thread_strands(drawdown[:, j] == 1, s, rng),
                   lambda t, lat, z: np.stack([x0 + j + lat, y0 - t, z],
                                              axis=1),
                   across_warp, warp_lin[j % len(warp_lin)])

    scene.render.filepath = os.path.abspath(path)
    bpy.ops.render.render(write_still=True)
