---
tags: [hub, meta]
updated: 2026-11-06
---
# How to use this vault

Open the `vault/` folder as a vault in Obsidian. Graph colours: hubs, decisions, components, concepts, lessons, theory.

**Note types** (tag in the frontmatter):
- `hub` - a map of a topic, mostly links
- `decision` - a choice, who made it, when, why, what it cost
- `component` - a bought part: what it is for, the numbers that matter, links
- `concept` - how something in our system works
- `lesson` - a mistake or surprise, and the rule it gave us
- `theory` - a topic for the theory round

**Rules for Claude** (also in [[Agent Protocol]]):
- Before work in an area, open its hub and the linked lessons.
- When something surprising happens or Egor corrects something, add a `lesson` note and link it from [[Lessons Index]] and the hub.
- When a decision changes, update its note (keep the history line), do not make a new one.
- Exact numbers live in repo files (`source:` in the frontmatter); do not copy tables here, link them.
- Every new note links to at least two others: no orphans.
