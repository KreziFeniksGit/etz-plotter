# Plotter project handoff (as of 2026-10-10, model v1 done)

## State
Egor approved the plotter example on 10 Oct. Model v1 is built: parametric Python model (src/model.py), checks, exports, viewer artifact "ETZ Plotter Model" (https://claude.ai/artifact/QJ7oXMWeb1v1TFoiJrMLWY). Files were sent as plotter_model_v1.zip (STEP assembly, 18 printed STL/STEP, plywood DXF, BOM, analysis). Source scripts are in that zip, not in this project; ask Egor to re-upload the zip if a new session must change the model. No CAD kernel could be installed (package sites blocked), so geometry is my own faceted prism kernel (geo.py).

## Design v1 (polygon coordinates, mm; X along 600, Y along 500)
- Base: 12 mm birch plywood X 90..340, Y 10..470, R10 corners, 4 rubber feet at (100|330, 22|458). No ballast (tipping margin 5.2 without it).
- Y: 2020 beam X 195..215 Y 10..410, MGN12 400 rail on top, MGN12H block. NEMA17 at Y 443 behind a printed mount, belt in a vertical plane X 183..189, idler at Y 22, microswitch home at the idler end. Carriage Y range 40..376.
- Post 2020 140 mm (Z 58..198) in a printed socket on the Y carriage; boom 2020 270 mm (X 209..479, Z 152..172) joined by 2 corner brackets (top and bottom).
- X: MGN12 250 rail under the boom (X 229..479), block centred on PXB; NEMA17 behind the post (centre X 165, Z 162), belt in a vertical plane beside the boom; idler bracket at the boom end. PXB range 256..440.
- Wrist module: printed wrist carriage (plate + vertical base plate with servo window), MG996R servo, arms 80 mm (pivots Z 117 / 77), 684ZZ bearings, end plate + shelf (notched for the lower arm), NEMA11, D-bore hub, electromagnet 20x15, camera 32x32 board, hall home. Magnet axis at PXB+105, PYC+21. Face height 5..40.
- Rule items modelled: latching E-stop, start button, green and red LEDs, connectors A 3 pin, B 3 pin, C 4 pin on the control panel side, 400-point breadboard next to them, 4S 2200 pack on a printed tray, electronics board (envelope) on standoffs.

## Checks (v1)
59/59 positions reachable; 0 collisions in 98 poses incl. screw heads; parked footprint inside zones 1+2; tipping 5.2 (field side); rail moment margin 135x (X) and 21x (Y); 116 fasteners checked; 18 printed designs, 19 pieces, about 220 g, all fit 220x220.

## Open items
- Controller choice (ESP32 with radio off vs RP2040/STM32): not answered yet; board is an envelope.
- Battery wording: summary says nominal at most 16 V, so 4S (14.8 V nominal) is assumed OK; confirm against the full text.
- Egor lists components he owns on Monday; budget about 300 EUR. BOM may change.
- Not modelled: wiring, X cable chain, microswitch screw holes, belt tooth combs, tolerance coupons.
- Old 14-week plan PDF and the git repo still describe the SCARA arm.
