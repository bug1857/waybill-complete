<!-- generated: do not edit; source is the evidence bundle -->
<!-- waybill-evidence-sha256: 3814664c69b955e2282f3953b7061b812d5abf8bc9a95161ed738afd4f3337cc -->
# Waybill evidence report

This report is generated from a schema-validated, content-hashed evidence bundle.

Bundle schema: `1.0.0`  
Bundle SHA-256: `3814664c69b955e2282f3953b7061b812d5abf8bc9a95161ed738afd4f3337cc`

## Solver results

| Input | Problem | Solver | Status | Stop reason | Feasible | Objective | Lower bound | Reference | Wall time (ms) | Record SHA-256 |
|---|---|---|---|---|:---:|---:|---:|---|---:|---|
| data/benchmarks/exact-euclidean-n10-s17.json | TSP | brute_force | PROVEN_OPTIMAL_TSP | optimal | yes | 3232 tsplib_units | 3232 | — | 636.5002080128761 | `58f51f0b848c9e19395a213aa3d442f9b3832ff57e08e55bf70dd500b4b76673` |
| data/benchmarks/exact-euclidean-n10-s17.json | TSP | held_karp | PROVEN_OPTIMAL_TSP | optimal | yes | 3232 tsplib_units | 3232 | — | 4.213874999550171 | `bdd60a210bb528de9a4835a93ea9c8cb44c1c0cc883ab9664ba76ece58f6609a` |
| data/benchmarks/exact-euclidean-n10-s17.json | TSP | branch_and_bound_min_in_out | PROVEN_OPTIMAL_TSP | optimal | yes | 3232 tsplib_units | 3232 | — | 12.212959001772106 | `321659d161d7f3eb2c1fa69abfad5e39ddb59ee486ef1ad397aa7eefecd065bf` |
| data/benchmarks/exact-euclidean-n10-s17.json | TSP | nearest_neighbor | HEURISTIC_FEASIBLE_TSP | completed | yes | 3355 tsplib_units | — | — | 0.07741700392216444 | `3fe583a91252cf463ff2e7a555f1a2a154b7166085d8e42e0843a884f84c4752` |
| data/tsplib/eil51.tsp | TSP | nearest_neighbor | HEURISTIC_FEASIBLE_TSP | completed | yes | 511 tsplib_units | — | 426 tsplib_units (TSPLIB95 published optimum) | 1.2624999944819137 | `5fc5d36137066ef6451c84121bc723baef3b0552af9a7624c009b5e8d42a0216` |
| data/benchmarks/clustered-cvrptw-150-v6-s240519.json | CVRPTW | clarke_wright_savings | HEURISTIC_FEASIBLE_CVRPTW | completed | yes | 142224 metres | — | — | 40.490375002264045 | `4afdaf1603f4c2ca41058818cfa681477d853a21fefb765b2585d4c2c50bbc28` |

## Provenance

| Record | Timestamp (UTC) | Git revision | Dirty | Python | Platform | Input SHA-256 | Matrix SHA-256 | Matrix unit | Seed | Budget | Solver configuration | Metrics |
|---|---|---|:---:|---|---|---|---|---|---:|---|---|---|
| `58f51f0b848c9e19395a213aa3d442f9b3832ff57e08e55bf70dd500b4b76673` | 2026-10-13T06:43:43.455417Z | `56b6b2445df91451a3be0f028ff42465065e1aed` | no | 3.14.5 | macOS-27.0.1-arm64-arm-64bit-Mach-O | `3cb0defa277d4dc0f8c54e1247fccafd45d50a6597418f0cc1b502bf05acde95` | `d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826` | tsplib_units | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance_config":{"family":"random_euclidean_tsp","name":"exact-euclidean-n10-s17","nodes":10,"seed":17,"span":1000},"solver":"brute_force"} | {"bound_time_ms":0.0,"nodes_created":181440,"nodes_explored":181440,"nodes_pruned":0,"peak_frontier":0,"report_distance_matrix_hash":"d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826","report_solver_config_hash":"edb0cffc120a09bc"} |
| `bdd60a210bb528de9a4835a93ea9c8cb44c1c0cc883ab9664ba76ece58f6609a` | 2026-10-13T06:43:43.511265Z | `56b6b2445df91451a3be0f028ff42465065e1aed` | no | 3.14.5 | macOS-27.0.1-arm64-arm-64bit-Mach-O | `3cb0defa277d4dc0f8c54e1247fccafd45d50a6597418f0cc1b502bf05acde95` | `d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826` | tsplib_units | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance_config":{"family":"random_euclidean_tsp","name":"exact-euclidean-n10-s17","nodes":10,"seed":17,"span":1000},"solver":"held_karp"} | {"bound_time_ms":0.0,"nodes_created":2304,"nodes_explored":2304,"nodes_pruned":0,"peak_frontier":0,"report_distance_matrix_hash":"d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826","report_extra":{"greedy_customer_bytes_estimate":"96","max_customers":"18","node_budget_counter":"dp_states_materialized","projected_states":"2304","state_bytes_estimate":"320","states_materialized":"2304"},"report_solver_config_hash":"edb0cffc120a09bc"} |
| `321659d161d7f3eb2c1fa69abfad5e39ddb59ee486ef1ad397aa7eefecd065bf` | 2026-10-13T06:43:43.557376Z | `56b6b2445df91451a3be0f028ff42465065e1aed` | no | 3.14.5 | macOS-27.0.1-arm64-arm-64bit-Mach-O | `3cb0defa277d4dc0f8c54e1247fccafd45d50a6597418f0cc1b502bf05acde95` | `d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826` | tsplib_units | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance_config":{"family":"random_euclidean_tsp","name":"exact-euclidean-n10-s17","nodes":10,"seed":17,"span":1000},"solver":"branch_and_bound_min_in_out"} | {"bound_time_ms":11.041412013582885,"nodes_created":458,"nodes_explored":77,"nodes_pruned":380,"peak_frontier":65,"report_distance_matrix_hash":"d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826","report_extra":{"bound":"min_in_out","incumbent_seed":"nearest_neighbor","node_budget_counter":"nodes_explored","search_strategy":"best_first","state_bytes_estimate":"672"},"report_solver_config_hash":"edb0cffc120a09bc"} |
| `3fe583a91252cf463ff2e7a555f1a2a154b7166085d8e42e0843a884f84c4752` | 2026-10-13T06:43:43.598500Z | `56b6b2445df91451a3be0f028ff42465065e1aed` | no | 3.14.5 | macOS-27.0.1-arm64-arm-64bit-Mach-O | `3cb0defa277d4dc0f8c54e1247fccafd45d50a6597418f0cc1b502bf05acde95` | `d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826` | tsplib_units | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance_config":{"family":"random_euclidean_tsp","name":"exact-euclidean-n10-s17","nodes":10,"seed":17,"span":1000},"solver":"nearest_neighbor"} | {"bound_time_ms":0.0,"nodes_created":9,"nodes_explored":9,"nodes_pruned":0,"peak_frontier":0,"report_distance_matrix_hash":"d2d4e93e97d8c048c54f7b9ca96a2b3d266805186c3ee05956bdd96f9093f826","report_extra":{"construction_complete":"true","tie_break":"node_index"},"report_solver_config_hash":"edb0cffc120a09bc"} |
| `5fc5d36137066ef6451c84121bc723baef3b0552af9a7624c009b5e8d42a0216` | 2026-10-13T06:43:43.627992Z | `56b6b2445df91451a3be0f028ff42465065e1aed` | no | 3.14.5 | macOS-27.0.1-arm64-arm-64bit-Mach-O | `66c05ad077ffd64d5778e358bbd16be049f8c8ae880cbd24f034487331d1ccce` | `fc44db3d68b784409c051776f121425b5a337251c2fda66a3ebc17cb18c6ed85` | tsplib_units | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance":"eil51","reference":"TSPLIB95 published optimum"} | {"bound_time_ms":0.0,"nodes_created":50,"nodes_explored":50,"nodes_pruned":0,"peak_frontier":0,"report_distance_matrix_hash":"fc44db3d68b784409c051776f121425b5a337251c2fda66a3ebc17cb18c6ed85","report_extra":{"construction_complete":"true","tie_break":"node_index"},"report_solver_config_hash":"edb0cffc120a09bc"} |
| `4afdaf1603f4c2ca41058818cfa681477d853a21fefb765b2585d4c2c50bbc28` | 2026-10-13T06:43:43.707382Z | `56b6b2445df91451a3be0f028ff42465065e1aed` | no | 3.14.5 | macOS-27.0.1-arm64-arm-64bit-Mach-O | `45f8cc35a2ab2a780aa78bb0d38cd4e574baa5f5556dc11b7135652e24ac944e` | `608925deea2c204b4affa1de8b963a33632bd466781bc898c43e5b3e676f707a` | metres | — | {"max_memory_mb":null,"max_nodes":null,"wall_time_ms":null} | {"instance_config":{"customers":150,"family":"clustered_cvrptw_150","name":"clustered-cvrptw-c150-v6-s240519","note":"Synthetic reproducible integration fixture; not live-road or live-traffic data.","seed":240519,"vehicles":6}} | {"bound_time_ms":0.0,"nodes_created":22350,"nodes_explored":21940,"nodes_pruned":0,"peak_frontier":0,"report_distance_matrix_hash":"608925deea2c204b4affa1de8b963a33632bd466781bc898c43e5b3e676f707a","report_extra":{"construction":"directed_parallel_clarke_wright","construction_complete":"true","final_routes":"6","initial_routes":"150","instance_infeasibility_proven":"false","merges_accepted":"144","pairs_evaluated":"21940","positive_merges":"144","savings_pairs":"22350"},"report_solver_config_hash":"edb0cffc120a09bc"} |

## Bundle metadata

```json
{
  "purpose": "release evidence and static demo",
  "scope": "exact validation, heuristic reference, and CVRPTW feasibility"
}
```

_Generated from the bundle identified above; manual edits are not evidence._
