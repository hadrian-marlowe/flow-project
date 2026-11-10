# Ball with no air

The first simulation: a ball launched with a starting speed and angle, with gravity
only. No air resistance.

## Run it

```
make run
```

(or `make run SIM=ball_no_air`). A window opens and the ball flies at half speed.

## Controls

| Key / control | What it does |
|---|---|
| space | pause or resume (every pause leaves a grey ghost marker with its time) |
| right arrow | step forward by `PAUSE_INTERVAL` seconds |
| "Jump to t" box | type an exact time in seconds, press Enter, and the ball lands there |

With `AUTO_PAUSE = True` the ball also pauses by itself every `PAUSE_INTERVAL` seconds.
Press space to continue to the next one.

## Settings (top of `ball_no_air.py`)

| Setting | Default | Meaning |
|---|---|---|
| `LAUNCH_SPEED` | 20.0 m/s | how fast the ball starts |
| `LAUNCH_ANGLE` | 45.0 ° | angle above the ground |
| `START_HEIGHT` | 0.0 m | starting height |
| `GRAVITY` | 9.8 m/s² | try 1.6 for the Moon |
| `DT` | 0.001 s | size of each physics time slice |
| `FRAME_DT` | 0.02 s | simulated time per animation frame |
| `PLAYBACK_SPEED` | 0.5 | 1.0 is real time |
| `PAUSE_INTERVAL` | 0.5 s | auto-pause spacing and right-arrow step |
| `AUTO_PAUSE` | True | pause by itself every interval |

## Files

- `ball_no_air.py` — the file you run and edit.
- `mockup.html` — the preview of the screen we designed first. Double-click to open.
  (Also online: https://claude.ai/artifact/HwkoejK6XQsR2gvnvN1cbo)
- Physics: `src/flow_project/projectile.py` (look for `# PHYSICS:` lines).
- Drawing: `src/flow_project/animate.py`. Playback rules: `src/flow_project/player.py`.
- Design: `docs/superpowers/specs/2026-11-06-ball-no-air-design.md`
