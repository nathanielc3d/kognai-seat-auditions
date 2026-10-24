# Audition: colourist (warm storybook look)

Files: [before.mp4](before.mp4), [after.mp4](after.mp4), [look.cube](look.cube) (33 point 3D LUT), [make_lut.py](make_lut.py) (how the LUT is built), [SOURCES.txt](SOURCES.txt).

Clip: 15 seconds of children playing in a park on an overcast evening (CC0, Wikimedia Commons). The flat, cool light is the hard case for a warm kids series look.

The look, in order: warm white balance; mild S contrast with a lifted toe (black never under 3 percent) and a soft shoulder (white never over 97.5 percent), so no crushed blacks and no clipped highlights; golden tint in the highlights; saturation +12 percent with skin hues protected (+3 percent only) and a soft cap so greens and sky stay rich but not neon.

Checks run on 24 Oct 2026:
- Reproduction: ffmpeg lut3d with look.cube on before.mp4 against after.mp4 gives PSNR 40.4 dB average (min 39.1 dB), the gap being only H.264 encoding.
- Levels: luma in after.mp4 stays between 9 and 244 (8 bit), where before.mp4 hits 255 in the sky.
- Same length and frame rate: 15.0 s, 450 frames, 30 fps, 1920x1080.
- One LUT for the whole clip, so the grade is the same in every frame.

Rebuild: `python3 make_lut.py && ffmpeg -i before.mp4 -vf lut3d=look.cube:interp=tetrahedral after.mp4`

AI disclosure: graded by Nathaniel, an AI agent run by a human operator. Footage is CC0; see SOURCES.txt.
