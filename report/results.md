<!-- generated: do not edit; source is the evidence bundle -->
<!-- waybill-evidence-sha256: 217868b99065d76b03be2be001a8fa815ba864e956a975ddd6d39b20ac1c9eb9 -->
# Waybill evidence report

This report is generated from a schema-validated, content-hashed evidence bundle.

Bundle schema: `1.0.0`  
Bundle SHA-256: `217868b99065d76b03be2be001a8fa815ba864e956a975ddd6d39b20ac1c9eb9`

## Solver results

| Input | Problem | Solver | Status | Stop reason | Feasible | Objective | Lower bound | Reference | Wall time (ms) | Record SHA-256 |
|---|---|---|---|---|:---:|---:|---:|---|---:|---|
| data/benchmarks/exact-euclidean-n10-s17.json | TSP | brute_force | PROVEN_OPTIMAL_TSP | optimal | yes | 3232 tsplib_units | 3232 | — | 603.9778750000551 | `60bc0ed0cf3240fc7216946374ad7d6d4981c1c527e3c82631d8a73dc02dc1e5` |
| data/benchmarks/exact-euclidean-n10-s17.json | TSP | held_karp | PROVEN_OPTIMAL_TSP | optimal | yes | 3232 tsplib_units | 3232 | — | 5.391374999931031 | `d0d44282187e9e178908cf10ed12817f32d958022d05ceaa97cb3db07f423058` |
| data/benchmarks/exact-euclidean-n10-s17.json | TSP | branch_and_bound_min_in_out | PROVEN_OPTIMAL_TSP | optimal | yes | 3232 tsplib_units | 3232 | — | 12.72712499996942 | `8b3175c039674dfb2270ff56c0351756f8f2e0c047d689c05a9767898071cd6b` |
| data/benchmarks/exact-euclidean-n10-s17.json | TSP | nearest_neighbor | HEURISTIC_FEASIBLE_TSP | completed | yes | 3355 tsplib_units | — | — | 0.08183299996744609 | `a53196cb4484c5bf145b4b3539c4880014d2a37613bcd9c9c08dfef7192ec8d4` |
| data/tsplib/eil51.tsp | TSP | nearest_neighbor | HEURISTIC_FEASIBLE_TSP | completed | yes | 511 tsplib_units | — | 426 tsplib_units (TSPLIB95 published optimum) | 0.5587919999925361 | `26af3b2504b65f47210755dcd25684d77579675cce845a0f122e6eca6f1dd829` |
| data/benchmarks/clustered-cvrptw-150-v6-s240519.json | CVRPTW | clarke_wright_savings | HEURISTIC_FEASIBLE_CVRPTW | completed | yes | 142224 metres | — | — | 41.457082999954764 | `5283361eeccd2b0dc20df8258042014e06b963431d1ad745579bc78e6ca9755d` |

## Provenance

| Record | Timestamp (UTC) | Git revision | Dirty | Python | Platform | Input SHA-256 | Matrix SHA-256 | Matrix unit | Seed | Budget | Solver configuration | Metrics |
|---|---|---|:---:|---|---|---|---|---|---:|---|---|---|
| `60bc0ed0cf3240fc7216946374ad7d6d4981c1c527e3c82631d8a73dc02dc1e5` | 2026-10-01T05:33:26.719970Z | `a3676cf99d833f9a5166aa44020ee4870db17c64` | yes | 3.13.5 | macOS-27.0-arm64-arm-64bit-Mach-O | `3cb0defa277d4dc0f8c54e1247fccafd45d50a6597418f0cc1b502bf05acde95` | `d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826` | tsplib_units | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance_config":{"family":"random_euclidean_tsp","name":"exact-euclidean-n10-s17","nodes":10,"seed":17,"span":1000},"solver":"brute_force"} | {"bound_time_ms":0.0,"nodes_created":181440,"nodes_explored":181440,"nodes_pruned":0,"peak_frontier":0,"report_distance_matrix_hash":"d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826","report_solver_config_hash":"edb0cffc120a09bc"} |
| `d0d44282187e9e178908cf10ed12817f32d958022d05ceaa97cb3db07f423058` | 2026-10-01T05:33:26.754221Z | `a3676cf99d833f9a5166aa44020ee4870db17c64` | yes | 3.13.5 | macOS-27.0-arm64-arm-64bit-Mach-O | `3cb0defa277d4dc0f8c54e1247fccafd45d50a6597418f0cc1b502bf05acde95` | `d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826` | tsplib_units | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance_config":{"family":"random_euclidean_tsp","name":"exact-euclidean-n10-s17","nodes":10,"seed":17,"span":1000},"solver":"held_karp"} | {"bound_time_ms":0.0,"nodes_created":2304,"nodes_explored":2304,"nodes_pruned":0,"peak_frontier":0,"report_distance_matrix_hash":"d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826","report_extra":{"greedy_customer_bytes_estimate":"96","max_customers":"18","node_budget_counter":"dp_states_materialized","projected_states":"2304","state_bytes_estimate":"320","states_materialized":"2304"},"report_solver_config_hash":"edb0cffc120a09bc"} |
| `8b3175c039674dfb2270ff56c0351756f8f2e0c047d689c05a9767898071cd6b` | 2026-10-01T05:33:26.783207Z | `a3676cf99d833f9a5166aa44020ee4870db17c64` | yes | 3.13.5 | macOS-27.0-arm64-arm-64bit-Mach-O | `3cb0defa277d4dc0f8c54e1247fccafd45d50a6597418f0cc1b502bf05acde95` | `d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826` | tsplib_units | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance_config":{"family":"random_euclidean_tsp","name":"exact-euclidean-n10-s17","nodes":10,"seed":17,"span":1000},"solver":"branch_and_bound_min_in_out"} | {"bound_time_ms":11.950455998885445,"nodes_created":458,"nodes_explored":77,"nodes_pruned":380,"peak_frontier":65,"report_distance_matrix_hash":"d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826","report_extra":{"bound":"min_in_out","incumbent_seed":"nearest_neighbor","node_budget_counter":"nodes_explored","search_strategy":"best_first","state_bytes_estimate":"672"},"report_solver_config_hash":"edb0cffc120a09bc"} |
| `a53196cb4484c5bf145b4b3539c4880014d2a37613bcd9c9c08dfef7192ec8d4` | 2026-10-01T05:33:26.799401Z | `a3676cf99d833f9a5166aa44020ee4870db17c64` | yes | 3.13.5 | macOS-27.0-arm64-arm-64bit-Mach-O | `3cb0defa277d4dc0f8c54e1247fccafd45d50a6597418f0cc1b502bf05acde95` | `d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826` | tsplib_units | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance_config":{"family":"random_euclidean_tsp","name":"exact-euclidean-n10-s17","nodes":10,"seed":17,"span":1000},"solver":"nearest_neighbor"} | {"bound_time_ms":0.0,"nodes_created":9,"nodes_explored":9,"nodes_pruned":0,"peak_frontier":0,"report_distance_matrix_hash":"d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826","report_extra":{"construction_complete":"true","tie_break":"node_index"},"report_solver_config_hash":"edb0cffc120a09bc"} |
| `26af3b2504b65f47210755dcd25684d77579675cce845a0f122e6eca6f1dd829` | 2026-10-01T05:33:26.816529Z | `a3676cf99d833f9a5166aa44020ee4870db17c64` | yes | 3.13.5 | macOS-27.0-arm64-arm-64bit-Mach-O | `66c05ad077ffd64d5778e358bbd16be049f8c8ae880cbd24f034487331d1ccce` | `fc44db3d68b784409c051776f121425b5a337251c2fda66a3ebc17cb18c6ed85` | tsplib_units | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance":"eil51","reference":"TSPLIB95 published optimum"} | {"bound_time_ms":0.0,"nodes_created":50,"nodes_explored":50,"nodes_pruned":0,"peak_frontier":0,"report_distance_matrix_hash":"fc44db3d68b784409c051776f121425b5a337251c2fda66a3ebc17cb18c6ed85","report_extra":{"construction_complete":"true","tie_break":"node_index"},"report_solver_config_hash":"edb0cffc120a09bc"} |
| `5283361eeccd2b0dc20df8258042014e06b963431d1ad745579bc78e6ca9755d` | 2026-10-01T05:33:26.876231Z | `a3676cf99d833f9a5166aa44020ee4870db17c64` | yes | 3.13.5 | macOS-27.0-arm64-arm-64bit-Mach-O | `45f8cc35a2ab2a780aa78bb0d38cd4e574baa5f5556dc11b7135652e24ac944e` | `608925deea2c204b4affa1de8b963a33632bd466781bc898c43e5b3e676f707a` | metres | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance_config":{"customers":150,"family":"clustered_cvrptw_150","name":"clustered-cvrptw-c150-v6-s240519","note":"Synthetic reproducible integration fixture; not live-road or live-traffic data.","seed":240519,"vehicles":6}} | {"bound_time_ms":0.0,"nodes_created":22350,"nodes_explored":21940,"nodes_pruned":0,"peak_frontier":0,"report_distance_matrix_hash":"608925deea2c204b4affa1de8b963a33632bd466781bc898c43e5b3e676f707a","report_extra":{"construction":"directed_parallel_clarke_wright","construction_complete":"true","final_routes":"6","initial_routes":"150","instance_infeasibility_proven":"false","merges_accepted":"144","pairs_evaluated":"21940","positive_merges":"144","savings_pairs":"22350"},"report_solver_config_hash":"edb0cffc120a09bc"} |

## Bundle metadata

```json
{
  "purpose": "release evidence and static demo",
  "scope": "exact validation, heuristic reference, and CVRPTW feasibility"
}
```

_Generated from the bundle identified above; manual edits are not evidence._
