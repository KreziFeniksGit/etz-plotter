---
tags: [lesson]
updated: 2026-11-06
---
# Non-ASCII paths break external tools

**What happened:** gmsh failed because the repo path contained "Рабочий стол".

**Rule:** Tools run in an ASCII temp folder (`fea.py` does this); keep project paths ASCII when possible.

Related: [[FEA]], [[CAD Pipeline]]
