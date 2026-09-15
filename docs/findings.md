# Scenario findings

All bundled runs use 60 ticks and seed 42. They are simulation outcomes, not claims
about a physical farm.

| Scenario | Final health | Yield | Water | Fertilizer | Fuel | Tasks | Messages |
|---|---:|---:|---:|---:|---:|---:|---:|
| Normal | 93.10 | 672.59 | 522 | 24 | 34.50 | 39 | 2,163 |
| Drought | 92.42 | 671.61 | 648 | 24 | 41.99 | 46 | 2,222 |
| Pest | 91.62 | 653.15 | 522 | 36 | 35.12 | 40 | 2,167 |
| Equipment failure | 93.10 | 672.59 | 522 | 24 | 36.83 | 39 | 2,141 |
| Mixed | 92.89 | 661.25 | 630 | 36 | 43.92 | 46 | 2,175 |

The drought scenario consumes almost the full water budget and produces more irrigation
contracts. The pest scenario redirects fertilizer/logistics capacity and has the lowest
yield. During the equipment-failure scenario one irrigation unit goes offline, but the
second unit maintains the same completed-task count and crop health at a modest fuel
penalty. That is evidence of redundancy in this simulated configuration.

Every completed Contract Net negotiation takes one scheduler cycle. The raw JSON files
preserve zone histories, events, bids, awards and more than two thousand peer messages
per scenario for audit and further analysis.
