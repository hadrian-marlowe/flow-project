# Ball with no air

A ball thrown with gravity only, no air resistance. Two paths, A (blue) and B
(orange), fly at the same time so you can compare them.

## Run it

```
make run
```

## The window

| Area | What it does |
|---|---|
| Equation banner (top) | `r(t)` with the selected path's numbers in it. Click a number to jump to its box. The A / B buttons pick which path it shows. |
| Plot | Balls, dotted trails, velocity arrows, numbers next to each ball, and a black × where the equation says the ball should be. |
| Time slider | Drag to any moment. Doesn't leave markers. |
| Play / Pause | Starts and pauses. Says **Launch** when you've typed new numbers; press it to use them. |
| Step › | Jumps to the next multiple of the "pause every" time. |
| pause every __ s | Tick it to make the flight stop by itself at that spacing. Off by default. |
| jump to t + Go | Lands on an exact time. |
| Clear markers | Removes the grey ghost circles. |
| speed | 0.25×, 0.5× or real time. |
| Launch boxes (right) | x₀, y₀, v₀, θ, vₓ, v_y for each path. v₀/θ and vₓ/v_y are the same arrow two ways: change one pair and the other updates. Press Enter to confirm a box. |
| show path B | Turn the second path off. |
| World & view | Gravity box and Earth / Moon / Mars / Jupiter buttons; x and y axis min / max; Auto-fit; show/hide arrows, numbers and the equation ×. |
| Readout | Both balls' x, y, vx, vy, speed, range, max height, flight time, and `sim−eq`, the gap between the simulation and the equation. |

Keys: **space** = Play / Pause, **right arrow** = Step. Keys are ignored while you're typing in a box.

Every pause (space, Step, jump, or auto-pause) leaves a grey ghost circle with its time.

## Starting values

The settings at the top of `ball_no_air.py` are only what the boxes show when
the window opens. You can change everything on screen.

## Where the physics is

- `src/flow_project/projectile.py`: the time-slice loop (`step` and `simulate`), lines marked `# PHYSICS:`.
- `src/flow_project/launch.py`: splitting v₀ and θ into vₓ and v_y and back, lines marked `# PHYSICS:`.

The rest is playback (`player.py`), drawing (`animate.py`) and the window (`launch_window.py`).

Design: `docs/superpowers/specs/2026-11-16-two-path-launch-window-design.md`

Earlier drafts of this simulation are in `simulations/prototypes/`.
