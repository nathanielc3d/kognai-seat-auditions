"""Sky replacement, made by Nathaniel (AI agent). Needs python3 with opencv-python-headless and numpy, plus ffmpeg.
in:  before.mp4 (plate, 25 fps) and sky.png (one frame of a CC0 cloud clip, drifting slowly)   out: after.mp4 (same length and frame rate)
1. matte: the overcast sky is bright, low saturation and blue leaning; key it per frame and keep only regions
   connected to the top edge. In a 7 px band around every edge each pixel is unmixed between the local
   foreground colour and the old sky colour, and the old sky's share is swapped for the new sky (no halo).
2. track: corners on the tower and wall are followed frame to frame (Lucas Kanade) and chained into a
   similarity transform against frame 0; the sky plate gets the same transform so it moves with the camera.
3. light: the new sky gets a haze gradient toward the horizon and a soft light wrap at the edges; the
   foreground pixels themselves are left as they are. Thin details (rod, weathervane) are kept with a median difference test."""
import cv2, numpy as np, subprocess, sys

def frames(path):
    cap = cv2.VideoCapture(path)
    while True:
        ok, f = cap.read()
        if not ok: return
        yield f

plate = list(frames("before.mp4"))
sky_still = cv2.imread("sky.png")  # one frame of the CC0 cloud clip; real skies barely move in 7 s
H, W = plate[0].shape[:2]
n = len(plate)

def hard_matte(f):
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV).astype(np.float32)
    b, r = f[..., 0].astype(np.float32), f[..., 2].astype(np.float32)
    m = ((hsv[..., 2] > 185) & (hsv[..., 1] < 90) & (b - r > 8)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    # keep only sky regions that touch the top edge (removes bright spots on the walls)
    num, lab = cv2.connectedComponents(m)
    top = set(np.unique(lab[0, :])) - {0}
    m = np.isin(lab, list(top)).astype(np.uint8)
    # thin details (spire rod, weathervane): anything that stands out from a 31 px median of the frame
    d = np.abs(f.astype(np.float32) - cv2.medianBlur(f, 31).astype(np.float32)).max(2)
    thin = cv2.dilate((d > 12).astype(np.uint8), np.ones((3, 3), np.uint8))
    m = m & (1 - thin)
    # drop tiny foreground specks left floating in the sky (compression noise)
    num, lab, st, _ = cv2.connectedComponentsWithStats(1 - m)
    for j in range(1, num):
        if st[j, cv2.CC_STAT_AREA] < 40:
            m[lab == j] = 1
    return m

def norm_blur(img, w, sigma):
    num = cv2.GaussianBlur(img * w[..., None], (0, 0), sigma)
    den = cv2.GaussianBlur(w, (0, 0), sigma)[..., None]
    return num / np.maximum(den, 1e-4)

def matte(f, with_sky=False):
    """Soft sky alpha. Inside a 7 px band around the edge, each pixel is unmixed between the local
    foreground colour and the local old sky colour, so thin parts (the spire rod, the ball) keep their
    true coverage and no bright fringe of the old sky is left behind."""
    m = hard_matte(f)
    C = f.astype(np.float32)
    k = np.ones((3, 3), np.uint8)
    inner_sky = cv2.erode(m, k, iterations=3).astype(np.float32)
    inner_fg = cv2.erode(1 - m, k, iterations=3).astype(np.float32)
    band = (cv2.dilate(m, k, iterations=3) - cv2.erode(m, k, iterations=3)) > 0
    S = norm_blur(C, inner_sky, 12)          # old sky colour, smooth, extended under the edge
    F = norm_blur(C, inner_fg, 3)            # local foreground colour
    d = S - F
    a = np.sum((C - F) * d, axis=2) / np.maximum(np.sum(d * d, axis=2), 25.0)
    a = np.clip(a, 0, 1)
    alpha = m.astype(np.float32)
    alpha[band] = a[band]
    alpha = cv2.GaussianBlur(alpha, (0, 0), 0.6)
    return (alpha, S) if with_sky else alpha

# --- tracking: similarity transform of each frame relative to frame 0 ---
g0 = cv2.cvtColor(plate[0], cv2.COLOR_BGR2GRAY)
fg0 = (matte(plate[0]) < 0.05).astype(np.uint8)
fg0 = cv2.erode(fg0, np.ones((15, 15), np.uint8))
T = [np.eye(3)]
prev = g0
pts = cv2.goodFeaturesToTrack(prev, 600, 0.01, 12, mask=fg0)
for i in range(1, n):
    gi = cv2.cvtColor(plate[i], cv2.COLOR_BGR2GRAY)
    nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, gi, pts, None, winSize=(31, 31), maxLevel=4)
    good = st.ravel() == 1
    A, inl = cv2.estimateAffinePartial2D(pts[good], nxt[good], method=cv2.RANSAC, ransacReprojThreshold=1.5)
    M = np.vstack([A, [0, 0, 1]])
    T.append(M @ T[-1])
    prev = gi
    pts = nxt[good][inl.ravel() == 1].reshape(-1, 1, 2)
    if len(pts) < 250:  # refresh features on the foreground of this frame
        fg = cv2.erode((matte(plate[i]) < 0.05).astype(np.uint8), np.ones((15, 15), np.uint8))
        pts = cv2.goodFeaturesToTrack(gi, 600, 0.01, 12, mask=fg)
np.save("track.npy", np.array(T))

# --- sky plate: crop the cloud area, scale it up with margin, haze toward the horizon ---
SX, SY, SW, SH = 0, 0, 1340, 760          # cloud area of the sky clip (no trees)
scale = 1.35 * W / SW
haze_y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
haze = 0.12 + np.clip((haze_y - 0.15) / 0.85, 0, 1) ** 1.3 * 0.6
haze_col = np.array([250, 244, 236], np.float32)  # BGR, pale warm haze near the horizon

out = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "25",
                        "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
                        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", "after.mp4"],
                       stdin=subprocess.PIPE)
for i in range(n):
    f = plate[i].astype(np.float32)
    s = sky_still[SY:SY + SH, SX:SX + SW]
    # the sky moves with the camera: centre the scaled plate, then apply this frame's transform
    base = np.array([[scale, 0, (W - SW * scale) / 2 - 0.9 * i], [0, scale, (H - SH * scale) / 2 - 0.12 * H], [0, 0, 1]])
    M = (T[i] @ base)[:2]
    s = cv2.warpAffine(s, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
    s = s * 0.72 + np.array([78, 66, 52], np.float32)   # open up the deep polarised blue toward the plate's soft exposure
    s = s * (1 - haze) + haze_col * haze
    alpha, S_old = matte(plate[i], with_sky=True)
    m = alpha[..., None]
    fg = f * np.array([1.0, 1.0, 1.0], np.float32)          # foreground left untouched
    # difference composite: take out the old sky's share of each pixel and put the new sky's share in
    o = fg - m * S_old * np.array([1.0, 1.0, 1.0], np.float32) + m * s
    # light wrap: a soft 3 px glow of the new sky over the foreground edge
    edge = np.clip(cv2.GaussianBlur(alpha, (0, 0), 2.5) - alpha, 0, 1)[..., None]
    o = o * (1 - 0.25 * edge) + cv2.GaussianBlur(s, (0, 0), 4.0) * 0.25 * edge
    out.stdin.write(np.clip(o, 0, 255).astype(np.uint8).tobytes())
out.stdin.close(); out.wait()
print("after.mp4 written,", n, "frames")
