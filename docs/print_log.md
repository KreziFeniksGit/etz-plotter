# Print log

What Egor has printed, from `out/printed/`. Claude updates this when Egor reports a print, and marks a part
**REPRINT** when its geometry changes after it was printed (see `.claude/rules/cad.md`).

Status: `printed` / `REPRINT` (model changed since) / `-` (not printed yet).
"Model" = the model version whose geometry was printed.

| Step | Part (`out/printed/*.step`) | Qty | Status | Model | Reported | Note |
|---|---|---|---|---|---|---|
| 1 | `foot_x4` | 4 | printed | v2.15+ | 24 Nov | all 4 |
| 1 | `y_beam_riser_x4` | 4 | printed | v2.15+ | 24 Nov | |
| 1 | `y_motor_mount` | 1 | printed | v2.15+ | 24 Nov | |
| 1 | `y_idler_bracket` | 1 | printed | v2.15+ | 24 Nov | |
| 1 | `y_idler_slider` | 1 | printed | v2.15+ | 24 Nov | |
| 1 | `y_carriage` | 1 | printed | v2.15+ | 24 Nov | |
| 1 | `y_belt_clamp` | 1 | printed | v2.15+ | 24 Nov | |
| 1 | `y_belt_spacer` | 1 | printed | v2.15+ | 24 Nov | |
| 2 | `post_cap` | 1 | - | | | |
| 2 | `x_motor_mount` | 1 | - | | | |
| 2 | `x_idler_bracket` | 1 | - | | | changed in v2.17 |
| 2 | `x_idler_slider` | 1 | - | | | |
| 2 | `wrist_wrist_carriage` | 1 | - | | | |
| 2 | `wrist_x_belt_riser` | 1 | - | | | changed in v2.17; also the belt grip test |
| 2 | `wrist_x_belt_clamp` | 1 | - | | | changed in v2.17; also the belt grip test |
| 3 | `wrist_chain_post` | 1 | - | | | wait: coupons D1, F1, E2 + calipers first |
| 3 | `wrist_arm_top` | 1 | - | | | wait (as above) |
| 3 | `wrist_arm_bottom` | 1 | - | | | wait (as above) |
| 3 | `wrist_end_plate` | 1 | - | | | wait (as above) |
| 3 | `wrist_shelf` | 1 | - | | | wait (as above) |
| 3 | `wrist_wrist_hub` | 1 | - | | | wait (as above) |
| 5 | `y_chain_guide` | 1 | - | | | |

Test stands (not plotter parts):

| Stand | Part | Qty | Status | Reported | Note |
|---|---|---|---|---|---|
| camera | `camera_stand/out/camera_stand_{base,post,slider}.step` | 3 | printed | 19 Nov | stand built |
| wrist | `wrist_stand/out/wrist_stand_base.step` | 1 | - | | 24 Nov model |
| wrist | `wrist_stand/out/wrist_stand_post.step` | 1 | - | | |
| wrist | `wrist_stand/out/wrist_stand_head.step` | 1 | - | | 3 Ruthex inserts |

Step 1: all printed (24 Nov). Waiting for the MGN12 rails (400 + 250, MGN12H blocks) to assemble the Y axis.

"v2.15+": these parts have the same geometry from v2.15 (23 Oct) to v2.17. A print made before 23 Oct may be
the older shape (feet, beam bolts); tell Claude if so.
