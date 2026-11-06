---
tags: [component]
source: components.csv
updated: 2026-11-06
---
# 4S LiPo battery

4S 2200 mAh 25C+ with XT60, 14.8 V nominal (12.8..16.8). ETZ: drives from batteries on the device, nominal <= 16 V.
~30 min of work per charge. Read on GPIO2 through 100k/15k (x7.67): [[Battery guard]].
Open: reads 11.8 V on the bench - [[Verify ADC readings with a multimeter]]. Drain risk: [[Battery left connected drains through the logic regulator]].
Related: [[Power tree]], [[INA226 (planned)]].
