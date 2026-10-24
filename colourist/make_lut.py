"""Warm storybook look as a 33 point 3D LUT (look.cube).
Made by Nathaniel (AI agent). Input and output: Rec.709 video levels as 0..1 RGB (applied by ffmpeg lut3d).
Steps: gentle lift of shadows (no crushed blacks), soft highlight roll off (no clipping), warm white balance,
golden tint in highlights and a hint of teal kept out of shadows, mild S contrast, saturation +12 percent with
skin hues protected and a soft cap so greens and skies stay rich but not neon."""
import numpy as np, colorsys
N = 33
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
def grade(rgb):
    r, g, b = rgb
    # 1. warm white balance (about +350K feel)
    r, g, b = r * 1.045, g * 1.01, b * 0.92
    # 2. luminance and gentle contrast: S curve around 0.45 with soft toe and shoulder
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    yc = np.clip(y, 0, 1.2)
    s = 0.45 + (yc - 0.45) * 1.08                    # mild contrast
    s = 0.035 + (1 - 0.035) * s                       # lift: black never below 0.035
    s = np.where(s > 0.80, 0.80 + (1 - np.exp(-(s - 0.80) / 0.17)) * 0.17, s)  # shoulder: max about 0.97
    k = s / max(y, 1e-4)
    r, g, b = r * k, g * k, b * k
    # 3. split tone: golden highlights, faintly warm shadows
    hi = smoothstep(0.45, 0.95, s); lo = 1 - smoothstep(0.05, 0.35, s)
    r += 0.030 * hi + 0.008 * lo; g += 0.016 * hi + 0.004 * lo; b -= 0.020 * hi
    # 4. saturation with skin protection and soft cap
    rr, gg, bb = [float(np.clip(v, 0, 1)) for v in (r, g, b)]
    h, l, sat = colorsys.rgb_to_hls(rr, gg, bb)
    deg = h * 360
    skin = np.exp(-((deg - 25) / 18) ** 2)            # orange skin hues around 25 degrees
    boost = 1.12 * (1 - skin) + 1.03 * skin
    sat2 = sat * boost
    sat2 = np.where(sat2 > 0.70, 0.70 + (1 - np.exp(-(sat2 - 0.70) / 0.25)) * 0.25, sat2)  # anti neon cap
    rr, gg, bb = colorsys.hls_to_rgb(h, l, float(sat2))
    return [min(max(v, 0.03), 0.975) for v in (rr, gg, bb)]
with open("look.cube", "w") as f:
    f.write('TITLE "Warm storybook by Nathaniel"\n# 33 point 3D LUT, Rec.709 in and out, made by an AI agent\nLUT_3D_SIZE 33\nDOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n')
    for bi in range(N):
        for gi in range(N):
            for ri in range(N):   # red changes fastest (cube standard)
                o = grade((ri / (N - 1), gi / (N - 1), bi / (N - 1)))
                f.write("%.6f %.6f %.6f\n" % tuple(o))
print("ok")
