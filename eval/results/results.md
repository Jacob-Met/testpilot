Backend: scripted

| case | agent status | bug-revealing | solved | tests written | repair rounds | model calls | tokens (est.) | changed-line cov before % | after % |
|---|---|---|---|---|---|---|---|---|---|
| calc_clamp | suspected_code_bug | yes | yes | 4 | 1 | 3 | 1051 | 25.0 | 100.0 |
| durations_parse | suspected_code_bug | yes | yes | 4 | 1 | 3 | 1176 | - | - |
| inventory_cart | failed | yes | no | 4 | 3 | 5 | 2337 | 20.0 | 100.0 |
| stats_median | passed | no | no | 3 | 0 | 2 | 443 | 16.7 | 100.0 |
| textutil_slugify | suspected_code_bug | yes | yes | 4 | 2 | 4 | 1641 | 25.0 | 100.0 |

pass@1 = 0.60 (3/5); bug-revealing = 0.80; tests written = 19; repair rounds = 7; tokens = 6648
