# Prototypes

Rough drafts kept as a record of how each simulation got to its final form.
Each one is frozen: it has its own copy of any code it needs, so later changes
to the shared engine in `src/flow_project/` can't break it. Prototypes are not
covered by `make test`.

Run one with `make run SIM=prototypes/<name>`.

| Draft | Date | What it was | Why it was replaced |
|---|---|---|---|
| `mockups/mockup_v1.html` | 2026-11-06 | Web sketch of the first screen: one ball, numbers next to it, pause / step / jump-to-time. Double-click to open in a browser. | It was only a sketch to agree on the screen before writing Python. |
| `ball_no_air_v1/` | 2026-11-10 | First Python window. One path, settings edited at the top of the file, auto-pause on, jump-to-time box. Physics by time slices. | Couldn't change the numbers on screen, and it always paused. Too hard to experiment with. |
| `mockups/mockup_v2.html` | 2026-11-16 | Web sketch of the redesigned window: clickable equation, two paths, side panel, axis boxes. | Sketch only; became the final Python window. |

The final versions live in `simulations/final/`.
