# Plotter v2 status (11 Oct 2026, v2.2: every fastener modelled, tolerance coupons)

Egor gave AI-written design rules (parametric, tolerances 0.3-0.5 moving / 0.1-0.15 press / 0.2-0.3 bolts / +0.2 motor holes, walls >= 2.4, fillets on all internal corners, overhang <= 45 deg, bridges <= 10-15 mm, cable-tie features, explain choices, BOM + assembly notes). He asked me to choose all components (except the camera); printer Ender-3 V3 class (220x220, 0.4 nozzle), PETG, no tolerance tests yet, has heat-set inserts, any screws, 2020/MGN12/plywood fine, speed about 100 mm/s, nothing heavier than a checker. He opens models in FreeCAD. He writes in English: answer in English.

## CAD tool
FreeCAD 1.0.2 AppImage from GitHub releases (PyPI is blocked), extracted to /home/claude/tools/freecad. Checks run with its bundled python (./fcpy); coloured export runs the GUI offscreen (QT_QPA_PLATFORM=offscreen freecad export_gui.py, script ends with os._exit(0)). Binary STLs: ./fcpy tools/stl_binary.py. Font for engraved labels: DejaVuSans-Bold.

## Delivered: ETZ_plotter_v2_2.zip (21 MB), ETZ_tolerance_coupons.zip (7.5 MB), parked STEP/FCStd
- Whole device STEP + FCStd, tree adds Fasteners: 454 parts, 554 solids, re-import verified.
- frame/fasteners.py: 133 fasteners (341 solids: screws, nuts, washers, 10 Ruthex inserts, 42 T-nuts). out/fastener_bom.csv.
- assembly.fastener_check / fastener_engagement: no clipping at rest and in 16 poses vs moving parts; engagement OK (insert >= 4, T-nut >= 2.5..3, nuts full, tapped metal within thread depth, blind tips inside target).
- tolerance/: 11 coupons (A vertical bolt holes, B horizontal bolt holes, C inserts 3.8-4.1, D1 bearing/magnet/TO-92, D2 D-bore hubs + post pins, E1 NEMA17, E2 NEMA11, F1 servo window, F2 2020 sleeves + riser tongues, F3 spacer/zip slot/M2 pilot, G panel holes), middle variant = model value; tolerance/README.md maps each to a constant. All pass DFM. About 190 g at full density; print A, C, D1, E1, F1 first.
- New named constants in wrist_module section 1: SPACER_GAP 0.3, SOCKET_GAP 0.2, M2_PILOT 1.8, ZIP_SLOT (3.0, 1.8).

## v2.2 changes found by the fastener check
- Feet: screw-on 20 x 7 in 4 mm pockets under the plywood (3 mm feet could not hold a screw). Beam bolts M5x20 caps in 9.3 x 7.5 counterbores from below.
- Y idler moved to y 12 (nut hit the parked Y block); idler bracket end plate top lowered to z 41.5.
- X idler axle: head between boom and idler, nut outside the slotted plate.
- Corner brackets: side walls, holes 11 mm from the corner (VERIFY). Rails: counterbored M3 holes at 25 mm (VERIFY).
- Wrist carriage ribs 9 -> 7 mm (servo tab nuts). Tray ears moved out; breadboard to y 139. Y chain end screws button heads. Wrist MGN12 block model has its rail channel.

## v2.1 (11 Oct): chains, cables, wiring
- Real 10x15 R18 chains rebuilt per pose (X 280 mm on the boom, moving end on chain_post top z 208; Y 250 mm in y_chain_guide). Y beam on 4 risers (cable tunnel), post 130. X travel PXB 292..435. Cable tubes. wiring.md (2-block E-stop, Pico 2 pin map, harnesses, TMC currents).

## Check results
- No clash at rest, no cable through a part, no collision in 54 poses, all poses inside the polygon, parked inside zones 1+2, lens 29.4 mm above the field at h 5, all printed parts pass DFM.
- Mass 4.0 kg with screws; CoM >= 92 mm inside the feet; tipping needs 31 m/s2 (design 2); worst rail moment 1.65 N m vs 37.5; profile sag <= 0.16 mm.

## Open
- VERIFY with calipers: servo (tab-to-top, case height, spline offset, horn face), magnet thread depth, camera board, chain link pitch and end link, bracket hole position, rail hole pitch/counterbore, NEMA11 thread depth.
- Egor prints the tolerance coupons and reports the fitting variants -> update constants, re-export.
- Camera choice (Egor). CHECK in the full rules: V pin voltage of connectors A and B.
- Not modelled: zip ties, wrist-internal cables (service loop along the top arm).
- Next: firmware/controller plan, reworked project plan.
