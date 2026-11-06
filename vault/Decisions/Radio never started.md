---
tags: [decision, rule]
updated: 2026-11-06
---
# Radio never started

ETZ rule: Wi-Fi and Bluetooth off on every controller and the laptop. The [[ESP32-S3 DevKitC-1]] has a radio, so the
firmware never calls the Wi-Fi/BLE init. Be ready to show the judges the code.
Bonus: ADC2 pins (GPIO13/14) are usable because Wi-Fi never runs ([[Measure everything]]).
Idea: print "radio never started" at boot as proof (`docs/ideas.md` #40). Related: [[Competition Rules]].
