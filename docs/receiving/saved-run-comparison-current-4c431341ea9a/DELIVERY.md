# Portable comparison handoff

Open the existing Drive packet, extract it, and open `comparison.html`:

[TestPilot Saved-Run Comparison](https://drive.google.com/file/d/1I0irYiTNtK8mbJYoyzL35x0KWiFXOLTn/view?usp=drivesdk)

The current [HAMON tooling atlas](https://app.notion.com/p/3f4aedcdf4a5812abb24e3faabd70a8e?pvs=204)
contains the usable artifact, immutable source, and bounded receiving result.
The shared-delivery owner published both in the established destinations and
read them back. Source integration remains on the separate
`integration/4c431341-saved-run-comparison` branch.

## Exact delivery identity

| Item | Identity |
|---|---|
| Drive file | `1I0irYiTNtK8mbJYoyzL35x0KWiFXOLTn` |
| Existing Drive parent | Estate run artifacts, `1for5kGniDXsNyYNLNC9wNXclUy7iTIcK` |
| Packet filename | `TestPilot-Saved-Run-Comparison-f074598a.zip` |
| Packet size / members | 38,520 bytes / 25 members |
| Packet SHA-256 | `7e1790350109c2336076bdb72d968f295cfc394edb45431e550a09774c5c7c78` |
| Comparison SHA-256 | `f074598a711791c2665ea890044ff4db036354c9c0c508cfc3dc10caef32ce9a` |
| Independent browser receipt SHA-256 | `5beb03c09d93de3557e4b9c3df3a20cdd941b336cc8985869bb169d3217594da` |
| Published implementation | `cd15c2db2e4cd6ff07f40f85103c30137f32ba5c` |
| Tested/published source tree | `80101f399499f8572e8b258d5bffd7932bd7bc09` |

The peer receiver downloaded the newly written Drive object and verified its
complete ZIP bytes, CRCs, and members. The source worker separately checked the
local delivered ZIP against the recorded size, member count, CRCs, and hash.
The packet contains the exact comparison, both original native reports, controlled
source projects and scripted inputs, the native CLI receipt, the independent
browser receipt, source pins, and short opening instructions.

Both synthetic reports passed their selected tests. The example demonstrates
how absent changed-line denominators remain unavailable while a measured zero
remains numeric. It does not demonstrate a quality or performance improvement.
