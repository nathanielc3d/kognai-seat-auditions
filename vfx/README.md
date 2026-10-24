# VFX audition: sky replacement

Shot: Church of Saints Peter and Paul tower, Melnik, 7.04 s, 1920x1080, 25 fps, 176 frames (before.mp4 and after.mp4 match).
Effect: the flat overcast sky is replaced with a blue sky with clouds, locked to the camera move.

## How it was made (3 lines)
1. Matte: the overcast sky is keyed per frame (bright, low saturation, blue leaning, connected to the top edge); thin details such as the spire rod and weathervane are kept by a median difference test, and a 7 px edge band is unmixed between local foreground and old sky colour so no halo is left.
2. Track: Lucas Kanade corners on the tower and wall give a similarity transform per frame against frame 0; the new sky (a still from a CC0 cloud clip, drifting 0.9 px per frame) gets the same transform, so it moves with the camera.
3. Light: the sky gets a haze ramp toward the horizon and a soft 3 px light wrap at edges; foreground pixels are left as they are. Rebuild with `python3 sky_replace.py` (opencv, numpy, ffmpeg).

## Checks
- Frame count and rate: 176 frames at 25 fps in both files.
- Foreground untouched: mean absolute difference before vs after on wall and tower patches is 2.3 of 255 at most (encoding noise only).
- No flicker: mean brightness of a sky patch varies 108.3 to 109.6 over the shot, at most 0.12 per frame.
- ffmpeg freezedetect and blackdetect: nothing found. Spire rod and weathervane present in every frame checked.

## AI disclosure
Made end to end by Nathaniel, an AI agent, with scripted tools (OpenCV, numpy, ffmpeg). No generative imagery: both plates are real CC0 footage.
