---
tags: [lesson]
updated: 2026-11-06
---
# Do not react to your own abort messages

**What happened:** run.py's abort cleared the queue, the firmware answered `q stopped`, and run.py treated that as a new fault.

**Rule:** Guard abort handling with an in-abort flag; separate "events I caused" from "events that happened to me".

Related: [[Run program]], [[Move queue]]
