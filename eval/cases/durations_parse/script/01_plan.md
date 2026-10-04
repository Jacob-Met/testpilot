Plan for durations.parse_duration:
1. Compact "1h30m" -> 5400.
2. Spaced "1h 30m 5s" -> 5405.
3. Unknown unit raises ValueError.
4. Trailing number raises ValueError.
