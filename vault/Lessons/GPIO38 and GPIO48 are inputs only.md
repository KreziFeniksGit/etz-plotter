---
tags: [lesson]
updated: 2026-11-06
---
# GPIO38 and GPIO48 are inputs only

**What happened:** One of them drives the DevKitC's RGB LED (48 on v1.0, 38 on v1.1). We use them for home switches.

**Rule:** Never configure them as outputs; keep them inputs with pull-up.

Related: [[Pin map]], [[ESP32-S3 DevKitC-1]], [[Omron D2F home switches]]
