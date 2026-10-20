# Independent review of ETZ SCARA arm v3 (no-box build)

Scope: v3 deliverable folder plus the CAD sources in the scratchpad `cad/` directory. No existing file was edited. All scripts and outputs of this review live in `/tmp/rv/` (scripts: `c2.py`, `sweep.py`, `scan.py`, `scan2.py`, `extra.py`, `path.py`, `thin.py`, `holes.py`, `clipchk.py`, `brg.py`; raw results in `/tmp/rv/out/`).

Joint range used for the collision work (derived, not stated anywhere in design.json):
- Workspace cells from `reach.py`: elbow-minus solution only is inside the mechanical stops. J1 -0.9..116.3 deg, J2 -150.1..-63.7 deg. The elbow-plus solution needs J1 as low as -119 deg, which is beyond the J1 stop (first contact at about -3 deg), so it is not reachable.
- Measured stops (own scans): J1 low contact about -3 deg, J1 high contact about 121 deg (model post at 118.5 deg). J2 stop post touches link 2 at +140 deg and at about -158 deg (asymmetric).
- Z: hz 5..90 mm (85 mm travel, as in torque.json and all the author's check poses).

## Severity summary

| # | Sev | Finding |
|---|-----|---------|
| 1 | HIGH | Z drive: no shaft coupler anywhere, and the 150 mm Tr8 screw cannot cover the 85 mm stroke (nut leaves the screw above hz = 79.5). |
| 2 | HIGH | J1 motor pulley and GT2-220 belt hit the corner of `z_bottom_mount` for hz < 12.5 mm (every reachable pose at hz = 5). |
| 3 | MED | The "no wall below 0.8 mm" DFM claim is vacuous (the 0.4 mm opening kernel is a single voxel). Real walls of 0.6 and 0.75 mm exist. |
| 4 | MED | Stale text and data about the removed box and old counts: guide PDF (73 screws, 58/6/5/4), `source/fcheck_out.json` (12 E-* entries), 11 ebox coupon files, `anim_data.py` text. |
| 5 | MED | Guide says print 2 cable clips; the model uses 4 (2 on link 1, 2 on link 2). |
| 6 | MED | Hardware not in any BOM: M3 T-nuts for the camera bracket, coupler, mast and boom fasteners, grub screws. |
| 7 | MED | Printed STEP files are multi-body with overlapping solids (138 and 168 bodies in the link channels); union volume is 8-10 % lower than the sum. |
| 8 | LOW | NEMA11 M2.5x5 screws engage only 2.0 mm; 1.3 mm wall at two of the four holes. |
| 9 | LOW | Smaller documentation and model inconsistencies (see list). |

## 1. Stale references to the removed box

Clean (verified):
- `grep -ril "ebox|electronics box|enclosure"` finds nothing in `model_viewer.html`, `bom_fasteners.json`, `verification.json`, `printed/`, `printed_ready/`, `purchased/`, `assembly/*.step` (only the unrelated part `z_carriage_arm:arm_lid`), `test_coupons/catalog.json`, `test_coupons/sheets.json`.
- The PDF text (pdftotext) has no box, ebox or board mention except the line "The electronics box is no longer part of the model: the boards are mounted bare." and the aluminium "lid" of the platform, which is a different object.
- `bom_fasteners.json` = `{ISO7380 M3x8: 24, Ruthex RX M3x5.7: 30, ISO4762 M3x10: 19, ISO7380 M3x6: 14, ISO4032 M3: 13, ISO7380 M2.5x5: 4}`. That is 61 screws, 13 nuts, 30 inserts. It equals `sched.build()` (checked by counting) and equals the `FAST_*` solids in `full_home_with_fasteners.step` (counted by name: same six categories and numbers). No E-* screws.
- `source/reach_seq.json` in the deliverable has 61 entries, no E-*. (The copy in the scratchpad is the old 73-entry one; the deliverable copy is the right one.)

Stale (needs fixing):
- `print_guide_and_changes.pdf`, section 3 table: "Fastener thread check 73 screws" (real: 61) and "Screw reach 58 OK / 6 ball / 5 L-key / 4 blocked" (real: 46 / 6 / 5 / 4 = 61). Both come from the old run with the 12 E-* screws. Source: `mkguide_v3.py` lines for the table.
- `source/fcheck_out.json` (dated 01:52, before the no-box change) has 73 entries including the twelve `E-E1..E4, E-L1..L4, E-S1..S4`. A fresh run of `fcheck.py` (output redirected to `/tmp/rv/out/fcheck_new.json`) gives 61 entries. Ship the new one.
- `test_coupons/ebox_base/` (4 coupons + sheet), `ebox_lid/` (2 + sheet), `ebox_plate/` (2 + sheet): 8 coupon files and 3 sheet files that are not in `catalog.json`, `sheets.json` or the viewer. Delete the three folders.
- Five more coupon files exist on disk but are not in the catalog: `link1_channel__05_d8p1`, `__06_d8p1`, `__11_d8p1`, `__13_d8p1`, `z_carriage_arm__01_d15p2` (catalog has 71 files, disk has 84 non-sheet files, of which 8 are ebox). Either catalog them or delete them.
- `source/anim_data.py`, step 9 text: "...a slack loop for the Z travel leads to the box lid window." Replace with "...leads to the electronics mounting area".
- `source/export_ready.py` line 9 still has `'ebox_plate'` in `ORIENT` (harmless, but dead).
- Cable routes (`assembly4.py`, `k_world`, `cable_Z`) still end at x -64..-94, y -123 (the old box position). They now end in free air. Cosmetic, but a reader of the STEP will see cables going nowhere.
- `purchased/` still contains `board_buck`, `board_esp32`, `board_tb6612`, `board_tmc2209` (four STEP files, unused by the assembly: the model no longer places them). Keep them only if you want reference dimensions for bare mounting; otherwise remove. `parts.py` still defines them in `purchased4()`.

## 2. Consistency of printed, printed_ready, assembly, BOM, purchased

Verified clean:
- 15 printed STEP files and 15 printed_ready STEP files: `verify.check` returns ok = True for all, no messages. Gauss volume equals the model volume to 0.07 % at worst (link1_channel 63.608 vs 63.565 cm3; z_carriage_arm 187.937 vs 187.904).
- printed vs printed_ready: vertex sets are identical after a rigid transform for 14 parts (identity) and for `cam_bracket` (180-degree flip about x, `diag(1,-1,-1)`). So only the cam bracket is flipped, as documented. All printed_ready parts have z min = 0.
- `printed_ready/orientation.json` sizes equal the model bounding boxes. Largest footprint: link1_channel 185.9 x 42.0 (39.5 high), z_carriage_arm 130.5 x 127.7 (60 high). Nothing is near the 220 x 220 mm bed.
- All 22 `purchased/*.step` pass `verify.check` and `topo_check` (0 bad edges, 0 bad references).

Not clean:
- Used but missing from `purchased/`: the three NEMA17 motors (`nema17_40_enc_J1`, `nema17_40_enc_J2`, `nema17_08_enc_Z`). They are in the assembly STEP as vendor bodies (`V:nema17_*`) but there is no motor model file in `purchased/`. The NEMA11 is there.
- Items in the assembly that have no purchased STEP and no BOM line: Z lead-screw coupler (not modelled at all, see finding 1), T-slot nuts for the camera bracket, grub screws of the pulleys.
- `purchased/gt2_belt_*.step` exist and the assembly has `belt_J1/belt_J2` (generated); fine.
- The assembly STEP also contains the four cable bodies (`cable_wrist`, `cable_J1`, `cable_J2`, `cable_Z`) that are not in any list. Documented only in the old step text.

## 3. Printed part checks

- `dfm.json` (matches `source/dfm.json` and the scratchpad copy): `lt_0.8mm` volume = 0.0 and 0 clusters for all 15 parts.
- That result is not meaningful. `dfm.py` builds the opening kernel with `ball(0.4/0.5)`; I ran it: `ball(0.8)` returns a 3x3x3 array with exactly 1 true voxel, so `binary_opening` is the identity and can never report anything. The `lt_1.2mm` kernel (`ball(1.2)`) is a 7-voxel cross, which detects features thinner than about 1.5 mm in axis directions (so the 62 clusters on link1_channel are features below 1.5 mm, not 1.2 mm).
- Independent re-check (`thin.py`): exact Euclidean-distance-transform opening with a true 0.4 mm ball at 0.25 mm voxels, all 15 parts. Real thin features found:
  - `link2_channel` clamp hub: two slabs 0.5-0.6 mm thick (x = -13.4..-12.8, y -5.7..-2.5, z about 2.6..9.4 and 12.6..19.4, link-2 local frame, 10 mm3 each). Cause: `clamp_hub` is called for link 2 with `E = 13.6` and `xc = -9.899`. The head pocket is 6.2 wide, so the outside skin is 13.6 - 9.899 - 3.1 = 0.6 mm (the default `E = -xc + 3.1 + 0.9` would give 0.9 mm; hub_link1 and hub_wrist have 0.9). Verified by point sampling: solid only from x = -13.4 to -12.8 at z = 6.0 and 16.0, y = -4.1. Fix: pass `E = 14.0` (or `E=None`) for link 2, which gives a 1.0 mm skin; the ear then grows 0.4 mm and the clamp-hub corner radius `corner` must be rechecked against the 30 mm link width (14.86 -> about 15.2 for half width 15).
  - `z_carriage_arm` Tr8 nut pocket: two slabs 0.75 and 1.0 mm thick, 6.3 x 6.5 mm, at x = -84.9 (XC), y = +11.2 and -10.9, z about 57 (local). That is a pocket side wall under the TR-1..4 screws (fcheck also reports wall 1.3 mm there). Fix: move the nut pocket side walls out by 0.5 mm or add a 0.8 mm rib.
  - `z_bottom_mount`: two sliver clusters 0.25-0.5 mm x 0.5 mm x 8.25 mm at local (15.6, 0, 4.1) and (0.2, 45.6, 4.1), 1 mm3 each. Near-tangent cut-outs. Cosmetic but the slicer will drop them (gaps in the part).
  - `wrist_bracket`: the 45-degree webs end in knife edges (0.25 mm thick, 1.6-1.9 mm3 each, six places). The slicer will skip them; harmless.
  - `link1_cover_B` corner clusters (3 x 3 x 2.5 mm) are corner-rounding artifacts of the test, not thin walls.
- Bed size: nothing exceeds 220 x 220 (see section 2).
- Support-free claim for the cam bracket flipped: the guide says "1802 > 0" overhang. Re-running `dfm.analyse` on the current flipped part gives 689 mm2 overhang and worst bridge 3.0 mm (no support needed, but not zero). The statement "removes its large overhang completely" is correct for the 17 mm bridge, wrong for the area figure. Fix the table cell to "1802 > 689".

## 4. Collision sweep over the joint range

Method: `interference()` from `checks4.py` logic (res 0.8 mm, overlap above 3 mm3, plus an eroded overlap column), cables excluded, all printed vs printed and printed vs purchased pairs. Poses:
- 41 workspace poses (`reach.cells()` sampled every 3rd cell plus the corner cells, both elbow solutions, hz = 5 or 90).
- 35 box poses (J1 -3, 30, 60, 90, 118.5 x J2 -165, -120, -63, 0, 63, 120, 165, hz alternating 5 and 90).
- 14 extreme-cell poses (cells E0, E8, E5, A0, A8, E2, E7 at hz 5 and 90), 5 parking and stop poses, plus fine J1 and J2 scans around the stops.
In-range poses total about 70 (23 elbow-minus workspace poses, 14 extreme cells, 25 box poses inside the stops, 5 parking and stop poses, plus scans).

Designed contacts ignored (same value in every pose): bearing seats (z_bottom_mount-608 139 mm3, carriage-J1 608 48 mm3, link1-elbow 608 97 mm3), motor pilot into z_top_mount (5.1 mm3), cover-on-channel, clip base on link wall.

In-range collisions found:
1. HIGH: `z_bottom_mount` vs `gt2_20_J1` (16.9 mm3) and `belt_J1` (12.3 mm3). Present in every pose with hz = 5, absent at hz = 90, so it is independent of J1 and J2. Geometry: pulley centre (-46.6, -50.6), tooth radius 9.1, so its edge reaches x = -55.7; the mount corner is at x <= -53.2, y >= -53.8, z 8..16; the pulley spans z 3.5+hz .. 19.5+hz, so contact exists for hz < 12.5. Penetration about 2.5 mm radially. Fix: cut a corner notch in `z_bottom_mount` (remove the area within 11.5 mm of (-46.6, -50.6), for example trim the corner to y >= -45 for x <= -53) or set the Z software minimum to 13 mm. Because the pick height is 5 mm, trimming the mount is the better fix.
2. LOW: `z_carriage_arm` vs `clip_l1_1`, 15-18 mm3 at J1 = -3 (graze on the J1 stop, J1 = -2 is clear). The link-1 channel itself touches the J1 stop post from about -4 deg. Margin from the workspace limit (J1 -0.9) to first contact is only about 2 deg; the other side has about 5 deg (needs 116.3, contact about 121). Belt slack or print tolerance can eat 2 deg. Suggest moving stop A by 2 deg outward or accepting.
3. LOW (parked pose only): at J1 = 90, J2 = +130 (the model's home orientation), hz < 16 mm the electromagnet reaches the `z_bottom_mount` and `frame_plate` (fcheck pose 2 also reports ZB-2 threaded part hitting `em_20x15`). It is outside the pick workspace; just keep the Z axis above 16 mm when the arm is folded.
4. Outside the workspace but inside the mechanical range (documented in the guide, confirmed): wrist bracket, NEMA11, hub and electromagnet hit the mast at J1 = 118.5, J2 = +120 (11,585 mm3 for the motor). J2 > about 155 deg (positive) or < -158 deg (negative): link 2 hits the J2 motor and bridge after the stop post. Stop post engages first: `j2_stop|link2_channel` at +140 deg (97 mm3) and -160 deg; motor contact starts at 160 deg, so the stop protects the motor by 15-20 deg.
5. Elbow-plus poses (J1 -119..-6) collide heavily (carriage arm vs link 1 up to 600 mm3, J1 motor vs link 1 up to 7,000 mm3) but that range is behind the J1 stop, so it is not reachable. Worth stating in the guide that the arm works in one elbow configuration.

No collision was found between any printed part and any purchased part in the 41 workspace poses and the 14 extreme-cell poses other than item 1. The Z top clearance at hz = 90 is 5 mm (carriage top 171, top mount 176).

## 5. Assembly order and screw reach

Steps from `anim_data.py` (regenerated in a copy: 156 items, 52 parts, 104 fasteners, no E-* items). Straight-line insertion paths of every part item checked against all parts installed earlier (`path.py`, 4 mm steps, final-contact overlap subtracted). No mis-order found:
- Passed: frame plate, Z mount, rods, collars, carriage (with LM8UU), Tr8 nut, lead screw, top mount, motor, J1 parts, link 1 channel, both cable clips (before covers), elbow bearings and shaft, cover A, stop plate, bridge, J2 motor, link 2, cover with clips, NEMA11, hub, mast, boom, cam bracket.
- Flagged by the path test but not real: the two 20T pulleys and the 60T J1 pulley (animation direction `[0,0,1]`, but they slide onto the shaft from below, as the shaft points down). The wrist bracket (-z path) touches `z_bottom_mount` at a 60 mm offset and the electromagnet touches the plate at 36-52 mm offset only because the animation pose has the arm folded over the Z column. In reality the arm is raised. These are animation-direction problems only; fix `DIRS` for `gt2_20_J1`, `gt2_20_J2`, `gt2_60_J1` to `[0,0,-1]`.
- Trap check: the belts go on before link 2 (link 2 hub bottom at z 85, belt at 73.5..79.5, elbow shaft top free until step 6): OK. The J2 motor screws (J2-M) come after the belt, so the belt tensioning by sliding is possible, and the bridge posts screws (L1-P) come last from above: OK. Cable clips on link 1 go in before cover A: required, and done. Wrist bracket before link 2 cover: required (its nuts are in the channel tab), done.
- `reach_seq.json` (deliverable, 61 screws): 46 OK, 6 OK-ball (J2-M2..4, W-T1, W-T2, C-2), 5 L-key (J2-M1, CL1-1..4), 4 blocked (CL2-1..4). The 4 blocked screws are the clips on the link-2 cover, and they are driven on the bench (`+S:CL2` and `+clip_l2_*` in step 7), so they are not an assembly problem. The guide's text "4 blocked: cable clips on the link inner walls" is wrong (they are on the cover, and the link-1 clips on the inner walls are L-key, workable). C-2 straight clearance is 5.3 mm: an ordinary hex key will not fit, a ball driver is required.
- Step text errors: step 7 says "bolted from below with two screws"; the schedule has four (W-T1..4).
- `fcheck.py` re-run (61 screws, 6 poses): no errors except ZB-2 (parked pose, item 3 of section 4). Warnings: W-M1..4 engagement 2.0 mm, H1/H2/HW head support 83 %, CL1 head support 65 %. The clip screw holes: axis line is free of any printed solid for all CL1, CL2, W-T and C-1 screws (`clipchk.py`), so the wall and cover clearance holes line up.

## 6. Other first-print and first-assembly risks

1. HIGH, Z drive (verified from `assembly4.py` and the STEP positions):
   - Screw top z = 162.0 and motor shaft bottom z = 162.0 (shaft 162..180, Ø5; screw Ø8). They meet end to end with no coupler. No coupler exists in the model, `purchased/`, `bom_fasteners.json` or any step text.
   - Tr8 nut at hz = 90 spans z 157.5..172.5 (flange 167.5..171), the screw ends at 162. So at hz = 90 only 4.5 mm of the nut boss is on the screw and the flange is off it; the nut is fully on the screw only for hz <= 79.5. With a 25 mm coupler occupying about z 150..175 the nut top must stay below 150, i.e. hz <= 67.5, which is below the parked magnet height HZ = 70 and 22 mm short of the 85 mm stroke assumed by torque.json.
   - Fix options: (a) use a 200 mm Tr8 screw and 220 mm rods and move the top mount up 50 mm (the carriage top is only 5 mm below the top mount at hz = 90, so this has to be done anyway if the stroke is real), or (b) lower the nut mounting 30 mm on the carriage and shorten the stroke to 55 mm, or (c) change the specification to hz 5..65 and reduce the stated travel. Add a 5-to-8 mm coupler (25 mm) to the BOM and model.
2. MED, hardware missing from all lists (sched has them as hosts but they are not counted): 2 M3 T-slot nuts for C-1 and C-2 (`host = tnut`); grub screws for the GT2 pulleys and the two 8 mm shaft collars; mast-to-base-plate fasteners (mast placed at x = -138 on the 8 mm plate, no fastener or hole in `base_plate`); boom-to-mast joint (boom starts at x = -128 against the mast side with no bracket). The top mount is held onto the rods only by friction and gravity.
3. MED, multi-body overlap: link1_channel has 168 bodies, link2_channel 138, z_carriage_arm 18, wrist_bracket 9. They overlap: union volume (voxel) vs sum of body volumes: link2_channel 33.46 vs 36.9 cm3, wrist_bracket 15.4 vs 16.6, z_top_mount 20.5 vs 20.4, z_carriage_arm and link1_channel about 10 % too. A slicer that treats each body as a separate volume (Bambu "parts", Prusa multi-part object) normally unions them, but this is the single most likely cause of a surprise (double-walls, wrong infill zones, a nut trap or insert pocket filled by an overlapping body). The check numbers in the guide use the union, which is right. Recommended: do a one-time 3D test print of a link-2 hub (printed in 20 minutes) and check the pockets, or ask the slicer for "merge/union" and inspect the layer preview at the hubs; if possible fuse bodies in a CAD tool before printing.
4. MED, cable clips: guide says "Print 2". Model has `clip_l1_0, clip_l1_1, clip_l2_0, clip_l2_1` and screws CL1-1..4, CL2-1..4. Print 4.
5. LOW, `W-M1..4` M2.5x5 ISO7380: head 3 mm plate + 2.0 mm engagement in the NEMA11 tapped hole. fcheck warns (engagement 2.0). Wall 1.3 mm around W-M3 and W-M4 in the bracket. Use M2.5x6 if the motor's tap depth is at least 3.5 mm; otherwise leave and use thread-lock. Check the real motor data sheet (this is model-dependent).
6. LOW, elbow bearing 608 sits 1.0 mm lower in the assembly than the floor ledge allows: `l1_plate` has a Ø19.93 hole inside the Ø22.12 boss bore (a 1.1 mm ledge, z 0..2.4), the bearing is placed at z = 1.4 (`assembly4.py`: `Z_L1+hz+1.4`), so it overlaps the ledge by 1.0 mm (65 mm3 in the sweep). In reality the bearing rests at z = 2.4, which shifts both elbow bearings up by 1.0 mm (the second bearing top reaches 19.4 of a 19.5 boss). The printed part is fine; the model offset only matters for shaft length and link-2 hub height (shaft_elbow is 57 mm; allow 1 mm). Fix `assembly4.py`: `1.4 -> 2.4` for the first bearing and `11.4 -> 12.4` for the second, then recheck the shaft protrusion.
7. LOW, DFM table uses union volumes smaller than the STEP volumes (link1_channel 56.46 in dfm vs 63.6 sum of bodies); mass table is correct, volume cell in any report that quotes dfm is not a body sum.
8. LOW, J2 stop asymmetric (+140 / -158 deg): workspace needs -150 deg, margin 8 deg on the working side; if the controller ever allows +J2, the wrist hits the post at +140 first, fine.
9. Coupon claims: the guide says 115 discs and 71 unique; catalog has 115 entries and 71 files, but the folders hold 84 coupon files (see section 1).

## 7. Suggested fixes in priority order

1. Decide the Z drive: add a coupler and a longer screw or reduce the stroke (finding 1). Update `parts.py`, `assembly4.py`, `torque.py`, the guide.
2. Notch the `z_bottom_mount` corner at (-46.6, -50.6), radius 11.5 mm (finding 2), or limit hz >= 13.
3. In `parts4.py` call `clamp_hub` for link 2 with `E = 14.0`; thicken the Tr8 pocket walls; rerun `dfm.py` after replacing `ball(r_vox)` with a proper distance-transform opening (use `scipy.ndimage.distance_transform_edt` as in `thin.py`) at 0.25 mm voxels.
4. Regenerate `fcheck_out.json`, the guide PDF numbers (61 screws, 46/6/5/4), the cam bracket overhang cell, "Print 4" clips, step text ("four screws", no "box lid window"), and delete `test_coupons/ebox_*`, the 5 uncataloged coupons and (optionally) `purchased/board_*.step`.
5. Add the missing hardware to a purchased-parts BOM: coupler, 2 T-nuts, pulley grub screws, mast and boom fasteners; add the three NEMA17 models to `purchased/`.
6. Print a hub test (link-2 hub with the new E) before the big parts, and check the slicer's handling of overlapping bodies.

## 8. What was verified clean

- BOM counts versus schedule versus STEP: identical (61 / 13 / 30).
- All printed and print-ready STEP files load, edges paired, volumes match the model; print-ready is the same geometry as printed with only the cam bracket flipped; no part larger than 186 mm.
- 265 holes of the placed model: every printed screw hole has a counterpart on its mating part within 0.05 mm (carriage and J1 motor, bridge and J2 motor, Z top mount and NEMA17, wrist bracket and NEMA11, link covers and channel posts, wrist bracket tabs and link 2). Only exceptions: the four insert pockets of the link-1 cable clips (clearance holes exist in the wall; axis free) and two cam-bracket holes (mate is the 2020 profile slot, not modelled).
- Rods, LM8UU, bearings and Z mounts: zero overlap beyond the single-face seat contacts.
- No collision of printed vs purchased parts inside the real working range, except finding 2 (hz < 12.5).
- Assembly sequence: no part is installed after something that traps it.

## 9. Resolution status (added after the review)

Fixed in the model and re-checked:
- Finding 1 (Z drive): coupler modelled (5 to 8 mm, 25 mm) and in `hardware_bom.csv`; usable Z range set to 5..65 mm (nut top stays below the coupler), `HZ` home height 65, `torque.py` travel 60 mm. The longer-screw option (200 mm screw, 220 mm rods, taller top mount) was not taken; say if you want the full 85 mm stroke back.
- Finding 2 (J1 pulley vs Z bottom mount): corner notch of radius 10.6 mm around the pulley. Collision check at hz = 5 and 65: clean.
- Finding 3: link 2 hub now `E = 14.0` (1.0 mm skin). The exact thin-wall test (`thin_check.py`, 0.25 mm voxels) shows no link 2 channel feature below 0.8 mm. Nut-pocket windows in the carriage moved out 0.8 mm. Remaining sub-2 mm3 slivers: z_bottom_mount notch tip, carriage hex pockets, wrist web knife edges, link 1 cover corner artefacts.
- Finding 4/5: guide numbers, clip count (4), cam-bracket overhang cell, step texts, `anim_data.py` text, coupons (cleaned, regenerated: 72 unique, none uncatalogued), `fcheck` regenerated (61 screws; poses limited to hz <= 65).
- Finding 6 (hardware): coupler, T-nuts and grub screws added to `hardware_bom.csv`. Mast and boom fixing are still NOT modelled (list only). NEMA17 vendor STEP models added to `purchased/` as `*_vendor_model.step`; `board_tb6612.step` removed.
- Finding 7 (overlapping solids): not changed; guide now recommends a hub test print.
- Finding 8: not changed (M2.5x5 engagement 2.0 mm, thread-lock advised).
- Elbow bearing offset (6.6): assembly model corrected by 1 mm.
- Animation `DIRS` corrected for the three pulleys; animation republished.
Not changed: J1 stop margin of about 2 degrees at the low end (suggest checking on the first print), asymmetric J2 stop, parked-pose ZB-2 warning (keep Z above 16 mm when folded).

## 10. Update: 16 V supply limit (rule)

The maximum nominal supply is 16 V, so the 24 V assumptions in torque.py, the power budget and the magnet choice were replaced. Re-run results (accuracy_calc.py, torque.py at n0 = 600 rpm):
- J1 extended, 90 degrees in 0.5 s: margin 0.94 (was 1.07 at 24 V): the move stalls. 0.6 s rectangular: 1.44; 0.9 s with smoothed ramps: 2.76 (recommended); elbow folded to 90 degrees at 0.5 s: 1.68. At 12 V (sagging pack): 0.81 at 0.5 s.
- Z (17HS08 pancake, lead 2): about 10 to 15 mm/s usable, 60 mm in 4 to 6 s. Tr8x4 or a 40 mm Z motor are the options if faster is needed.
- Magnet: use a 12 V type (24 V type gets about 44 % of its force). PWM from the rail, duty at most 70 %.
- Peak power about 43 W, 2.7 A at 16 V. A charged 4S pack is 16.8 V: check whether the rule counts nominal or charged voltage.

## 11. Update: mechanical upgrades (Z column and J1 bearings)

- Z column extended by 50 mm (`ZEXT` in `parts.py`): 200 mm Tr8 screw, 220 mm rods, top mount, coupler and Z motor raised by 50 mm. Stroke is back to 85 mm (hz 5..90); the nut reaches the coupler only above hz = 117. Z drive remains Tr8x2 (self-locking); at 16 V it moves 10 to 15 mm/s (85 mm in 6 to 9 s). Rod bending with the longer span is about 0.1 mm at mid travel (estimate), not included in the droop figure.
- J1 bearing span widened from 8 to 15 mm: platform bore opened to the underside for the lower 608, an internal 8 mm shelf (bore 20 mm) between the two seats, upper 608 flush with the boss top. FE platform tilt unchanged (0.0033 / 0.0034 rad; the model does not include the shelf, which can only stiffen it).
- Re-checked: fastener check clean (TR screws now have straight access, ZB-2 parked-pose warning only), no new collisions for the carriage, boss, coupler and top mount at hz 5, 70, 90, 100, wall check on the carriage clean, coupons regenerated (72, none mismatched), viewer and animation republished.
- Not re-run: the full sequence-aware screw-reach pass (platform and Z-column change do not touch screw approach paths except TR-1..4, which improved).
