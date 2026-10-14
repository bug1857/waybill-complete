<!-- generated: do not edit; source is the evidence bundle -->
<!-- waybill-evidence-sha256: 972d469a4915594961651916189e5b5c0b839086722f84b4e41c2c3634affb04 -->
# Waybill evidence report

This report is generated from a schema-validated, content-hashed evidence bundle.

Bundle schema: `1.0.0`  
Bundle SHA-256: `972d469a4915594961651916189e5b5c0b839086722f84b4e41c2c3634affb04`

## Solver results

| Input | Problem | Solver | Status | Stop reason | Feasible | Objective | Lower bound | Reference | Wall time (ms) | Record SHA-256 |
|---|---|---|---|---|:---:|---:|---:|---|---:|---|
| data/benchmarks/exact-euclidean-n10-s17.json | TSP | brute_force | PROVEN_OPTIMAL_TSP | optimal | yes | 3232 tsplib_units | 3232 | — | 473.84512500138953 | `0d852cde688df9bb1484dc8426f77378b1c48c5ba18dc9974c8c033c0464cf3c` |
| data/benchmarks/exact-euclidean-n10-s17.json | TSP | held_karp | PROVEN_OPTIMAL_TSP | optimal | yes | 3232 tsplib_units | 3232 | — | 3.922875002899673 | `ae2dee0f05117e327a510fb34d895abccbac2ebea37999ca7433e6270ca3f810` |
| data/benchmarks/exact-euclidean-n10-s17.json | TSP | branch_and_bound_min_in_out | PROVEN_OPTIMAL_TSP | optimal | yes | 3232 tsplib_units | 3232 | — | 10.179124998103362 | `fd198c1d1cf72f564beef56f994f674896816b058d5b36fc9fe615bf0c35560d` |
| data/benchmarks/exact-euclidean-n10-s17.json | TSP | nearest_neighbor | HEURISTIC_FEASIBLE_TSP | completed | yes | 3355 tsplib_units | — | — | 0.06637500337092206 | `2249439c42876eed29c6a0947fa6252af2db388d00fcc8999115221f9874e80d` |
| data/tsplib/eil51.tsp | TSP | nearest_neighbor | HEURISTIC_FEASIBLE_TSP | completed | yes | 511 tsplib_units | — | 426 tsplib_units (TSPLIB95 published optimum) | 0.44337500003166497 | `388ad8fd9596552c60b300f93d714cfb25d5877a43ae3f0a7e679f9634b4519e` |
| data/benchmarks/clustered-cvrptw-150-v6-s240519.json | CVRPTW | clarke_wright_savings | HEURISTIC_FEASIBLE_CVRPTW | completed | yes | 142224 metres | — | — | 30.770792000112124 | `9efb4fa5666af35cadfa57c4569b397c0bfc55d370739aa1736cf533d06c9052` |

## Provenance

| Record | Timestamp (UTC) | Git revision | Dirty | Python | Platform | Input SHA-256 | Matrix SHA-256 | Matrix unit | Seed | Budget | Solver configuration | Metrics |
|---|---|---|:---:|---|---|---|---|---|---:|---|---|---|
| `0d852cde688df9bb1484dc8426f77378b1c48c5ba18dc9974c8c033c0464cf3c` | 2026-10-14T08:09:48.026950Z | `976760703f6b299c3d4bbd3d43dd5c25b73256b8` | no | 3.14.5 | macOS-27.0.1-arm64-arm-64bit-Mach-O | `3cb0defa277d4dc0f8c54e1247fccafd45d50a6597418f0cc1b502bf05acde95` | `d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826` | tsplib_units | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance_config":{"family":"random_euclidean_tsp","name":"exact-euclidean-n10-s17","nodes":10,"seed":17,"span":1000},"solver":"brute_force"} | {"bound_time_ms":0.0,"nodes_created":181440,"nodes_explored":181440,"nodes_pruned":0,"peak_frontier":0,"report_distance_matrix_hash":"d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826","report_solver_config_hash":"edb0cffc120a09bc"} |
| `ae2dee0f05117e327a510fb34d895abccbac2ebea37999ca7433e6270ca3f810` | 2026-10-14T08:09:48.075381Z | `976760703f6b299c3d4bbd3d43dd5c25b73256b8` | no | 3.14.5 | macOS-27.0.1-arm64-arm-64bit-Mach-O | `3cb0defa277d4dc0f8c54e1247fccafd45d50a6597418f0cc1b502bf05acde95` | `d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826` | tsplib_units | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance_config":{"family":"random_euclidean_tsp","name":"exact-euclidean-n10-s17","nodes":10,"seed":17,"span":1000},"solver":"held_karp"} | {"bound_time_ms":0.0,"nodes_created":2304,"nodes_explored":2304,"nodes_pruned":0,"peak_frontier":0,"report_distance_matrix_hash":"d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826","report_extra":{"greedy_customer_bytes_estimate":"96","max_customers":"18","node_budget_counter":"dp_states_materialized","projected_states":"2304","state_bytes_estimate":"320","states_materialized":"2304"},"report_solver_config_hash":"edb0cffc120a09bc"} |
| `fd198c1d1cf72f564beef56f994f674896816b058d5b36fc9fe615bf0c35560d` | 2026-10-14T08:09:48.101459Z | `976760703f6b299c3d4bbd3d43dd5c25b73256b8` | no | 3.14.5 | macOS-27.0.1-arm64-arm-64bit-Mach-O | `3cb0defa277d4dc0f8c54e1247fccafd45d50a6597418f0cc1b502bf05acde95` | `d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826` | tsplib_units | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance_config":{"family":"random_euclidean_tsp","name":"exact-euclidean-n10-s17","nodes":10,"seed":17,"span":1000},"solver":"branch_and_bound_min_in_out"} | {"bound_time_ms":9.50761898275232,"nodes_created":458,"nodes_explored":77,"nodes_pruned":380,"peak_frontier":65,"report_distance_matrix_hash":"d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826","report_extra":{"bound":"min_in_out","incumbent_seed":"nearest_neighbor","node_budget_counter":"nodes_explored","search_strategy":"best_first","state_bytes_estimate":"672"},"report_solver_config_hash":"edb0cffc120a09bc"} |
| `2249439c42876eed29c6a0947fa6252af2db388d00fcc8999115221f9874e80d` | 2026-10-14T08:09:48.117071Z | `976760703f6b299c3d4bbd3d43dd5c25b73256b8` | no | 3.14.5 | macOS-27.0.1-arm64-arm-64bit-Mach-O | `3cb0defa277d4dc0f8c54e1247fccafd45d50a6597418f0cc1b502bf05acde95` | `d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826` | tsplib_units | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance_config":{"family":"random_euclidean_tsp","name":"exact-euclidean-n10-s17","nodes":10,"seed":17,"span":1000},"solver":"nearest_neighbor"} | {"bound_time_ms":0.0,"nodes_created":9,"nodes_explored":9,"nodes_pruned":0,"peak_frontier":0,"report_distance_matrix_hash":"d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826","report_extra":{"construction_complete":"true","tie_break":"node_index"},"report_solver_config_hash":"edb0cffc120a09bc"} |
| `388ad8fd9596552c60b300f93d714cfb25d5877a43ae3f0a7e679f9634b4519e` | 2026-10-14T08:09:48.133310Z | `976760703f6b299c3d4bbd3d43dd5c25b73256b8` | no | 3.14.5 | macOS-27.0.1-arm64-arm-64bit-Mach-O | `66c05ad077ffd64d5778e358bbd16be049f8c8ae880cbd24f034487331d1ccce` | `fc44db3d68b784409c051776f121425b5a337251c2fda66a3ebc17cb18c6ed85` | tsplib_units | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance":"eil51","reference":"TSPLIB95 published optimum"} | {"bound_time_ms":0.0,"nodes_created":50,"nodes_explored":50,"nodes_pruned":0,"peak_frontier":0,"report_distance_matrix_hash":"fc44db3d68b784409c051776f121425b5a337251c2fda66a3ebc17cb18c6ed85","report_extra":{"construction_complete":"true","tie_break":"node_index"},"report_solver_config_hash":"edb0cffc120a09bc"} |
| `9efb4fa5666af35cadfa57c4569b397c0bfc55d370739aa1736cf533d06c9052` | 2026-10-14T08:09:48.186413Z | `976760703f6b299c3d4bbd3d43dd5c25b73256b8` | no | 3.14.5 | macOS-27.0.1-arm64-arm-64bit-Mach-O | `45f8cc35a2ab2a780aa78bb0d38cd4e574baa5f5556dc11b7135652e24ac944e` | `608925deea2c204b4affa1de8b963a33632bd466781bc898c43e5b3e676f707a` | metres | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance_config":{"customers":150,"family":"clustered_cvrptw_150","name":"clustered-cvrptw-c150-v6-s240519","note":"Synthetic reproducible integration fixture; not live-road or live-traffic data.","seed":240519,"vehicles":6}} | {"bound_time_ms":0.0,"nodes_created":22350,"nodes_explored":21940,"nodes_pruned":0,"peak_frontier":0,"report_distance_matrix_hash":"608925deea2c204b4affa1de8b963a33632bd466781bc898c43e5b3e676f707a","report_extra":{"construction":"directed_parallel_clarke_wright","construction_complete":"true","final_routes":"6","initial_routes":"150","instance_infeasibility_proven":"false","merges_accepted":"144","pairs_evaluated":"21940","positive_merges":"144","savings_pairs":"22350"},"report_solver_config_hash":"edb0cffc120a09bc"} |

## Bundle metadata

```json
{
  "purpose": "release evidence and static demo",
  "scope": "exact validation, heuristic reference, and CVRPTW feasibility"
}
```

_Generated from the bundle identified above; manual edits are not evidence._
