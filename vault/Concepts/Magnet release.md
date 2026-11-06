---
tags: [concept, risk]
updated: 2026-11-06
---
# Magnet release

The steel washer keeps a little magnetism, so a checker may stick when the magnet turns off. A reverse "release pulse"
needs an H-bridge; our board has one low-side MOSFET ([[100N03A magnet MOSFET]]) - impossible.
Current answer: off + short settle (the SS34 lets the field die in ms). If checkers stick: a spacer/felt on the face, or an H-bridge add-on.
Test in [[Bring-up]] step 7. Related: [[P20-15 electromagnet]].
