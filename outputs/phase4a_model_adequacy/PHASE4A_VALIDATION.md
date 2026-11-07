# Phase 4A validation

Read-only historical seed checks, circuit checks and development gates are recorded below. No final test data enter these gates.

```json
{
  "seed_audit": {
    "unique_stage_seeds": 190,
    "historical_explicit_seed_values_checked": 265,
    "collisions": [],
    "note": "Scans explicit JSON seed fields and expands Phase 3A/3B derivations; not a proof against unrecorded historical seeds."
  },
  "ideal": {
    "detectors": 40,
    "observables": 1,
    "diagnostic_shots": 256,
    "all_zero": true
  },
  "model_metadata": {
    "(0.001, 0.001)": {
      "circuit_sha256": "2676fe2e7c0f8083aacf333605079b1623787579c1840ceffda66b0f88ba7cae",
      "dem_sha256": "295c85a6da705b4b66bf5f9f660deb93780e21b18b3ec07b61609cdef450d305",
      "fault_locations": {
        "DEPOLARIZE1": 40,
        "DEPOLARIZE2": 120,
        "X_ERROR": 49
      },
      "edges": 142,
      "python_wrapper_bytes_not_total": 48,
      "weights_vs_fixed": {
        "common_edges": 142,
        "different_weights": 142,
        "max_absolute_change": 1.1004173235027945,
        "same_edge_keys": true
      }
    },
    "(0.001, 0.003)": {
      "circuit_sha256": "44acb0e7d3bf3f0cba8c1c1b55b564053508c854dd39672545711566c97e0014",
      "dem_sha256": "4de86215b01722e954a61d95a87219efed361a2472b8672f76457f626f54fb18",
      "fault_locations": {
        "DEPOLARIZE1": 40,
        "DEPOLARIZE2": 120,
        "X_ERROR": 49
      },
      "edges": 142,
      "python_wrapper_bytes_not_total": 48,
      "weights_vs_fixed": {
        "common_edges": 142,
        "different_weights": 142,
        "max_absolute_change": 1.0996806652956748,
        "same_edge_keys": true
      }
    },
    "(0.001, 0.006)": {
      "circuit_sha256": "f4590fe9765fb78499d08ab2a00309362a9d5496c4a45ff3154c4204f7341c45",
      "dem_sha256": "5a34f52876e25ae58a4f21b0bc990a489a79ef542a5908564267cfbb0214e6ed",
      "fault_locations": {
        "DEPOLARIZE1": 40,
        "DEPOLARIZE2": 120,
        "X_ERROR": 49
      },
      "edges": 142,
      "python_wrapper_bytes_not_total": 48,
      "weights_vs_fixed": {
        "common_edges": 142,
        "different_weights": 142,
        "max_absolute_change": 1.0996806652956748,
        "same_edge_keys": true
      }
    },
    "(0.003, 0.001)": {
      "circuit_sha256": "2f88f6af72a8e37bac7b25dbe384c472c97b0ad9e86bcebcafd4a014931ff917",
      "dem_sha256": "6ddf761aec31951ef810afd6503aabb01c706e79a9a226a76d239513db078f4f",
      "fault_locations": {
        "DEPOLARIZE1": 40,
        "DEPOLARIZE2": 120,
        "X_ERROR": 49
      },
      "edges": 142,
      "python_wrapper_bytes_not_total": 48,
      "weights_vs_fixed": {
        "common_edges": 142,
        "different_weights": 47,
        "max_absolute_change": 0.7486543399769223,
        "same_edge_keys": true
      }
    },
    "(0.003, 0.003)": {
      "circuit_sha256": "994c32305d7ec2746f7f3cd9caab0502f40bf4dadb4018b60d0d30cd5fdff1b3",
      "dem_sha256": "e3f4ce019079efcc961615d58c7754147e6061438ab5a37b8faa69d694ec27c5",
      "fault_locations": {
        "DEPOLARIZE1": 40,
        "DEPOLARIZE2": 120,
        "X_ERROR": 49
      },
      "edges": 142,
      "python_wrapper_bytes_not_total": 48,
      "weights_vs_fixed": {
        "common_edges": 142,
        "different_weights": 0,
        "max_absolute_change": 0.0,
        "same_edge_keys": true
      }
    },
    "(0.003, 0.006)": {
      "circuit_sha256": "c259c0d610e40d4b68d8a4b5e829728ecaaf86a66c4196e9d4dc19625ec08370",
      "dem_sha256": "91551979f7bff3838c76e4d63f754aa05571654b23129aeccaae615d27fb88df",
      "fault_locations": {
        "DEPOLARIZE1": 40,
        "DEPOLARIZE2": 120,
        "X_ERROR": 49
      },
      "edges": 142,
      "python_wrapper_bytes_not_total": 48,
      "weights_vs_fixed": {
        "common_edges": 142,
        "different_weights": 47,
        "max_absolute_change": 0.5847092650340686,
        "same_edge_keys": true
      }
    },
    "(0.006, 0.001)": {
      "circuit_sha256": "ef451e2bfd9bbb6b6a5ee6e0767aa000b8df1b90de2d822031d22cf417cc56ac",
      "dem_sha256": "062a629d756aabae255545739243deafbf7b72d0ba87fedf9ca3e8f31b1769df",
      "fault_locations": {
        "DEPOLARIZE1": 40,
        "DEPOLARIZE2": 120,
        "X_ERROR": 49
      },
      "edges": 142,
      "python_wrapper_bytes_not_total": 48,
      "weights_vs_fixed": {
        "common_edges": 142,
        "different_weights": 142,
        "max_absolute_change": 0.6947529645613777,
        "same_edge_keys": true
      }
    },
    "(0.006, 0.003)": {
      "circuit_sha256": "2b234bc71b4d4f639287379509d0934bb3f8878927c72f293f130678317c583d",
      "dem_sha256": "32a7cddc73826b59305b8e2bd617e21daaf024d3b08648909c1294a211d67943",
      "fault_locations": {
        "DEPOLARIZE1": 40,
        "DEPOLARIZE2": 120,
        "X_ERROR": 49
      },
      "edges": 142,
      "python_wrapper_bytes_not_total": 48,
      "weights_vs_fixed": {
        "common_edges": 142,
        "different_weights": 142,
        "max_absolute_change": 0.6947529645613777,
        "same_edge_keys": true
      }
    },
    "(0.006, 0.006)": {
      "circuit_sha256": "b2aaf73845b95b4fb331d8f1bbbe213a89174938e3cef0fb581369c3afb4be60",
      "dem_sha256": "0b5fc609e7340f1f337c0fdfe475f06819ccf5cc4c063549651b287aaf3144f3",
      "fault_locations": {
        "DEPOLARIZE1": 40,
        "DEPOLARIZE2": 120,
        "X_ERROR": 49
      },
      "edges": 142,
      "python_wrapper_bytes_not_total": 48,
      "weights_vs_fixed": {
        "common_edges": 142,
        "different_weights": 142,
        "max_absolute_change": 0.6958575839838321,
        "same_edge_keys": true
      }
    }
  },
  "preflight_passed": true,
  "exact_calibration_recoveries": {
    "data_heavy": 20,
    "nominal": 20,
    "measurement_heavy": 20
  },
  "development_gates": {
    "calibration": true,
    "disagreement": true,
    "validation_direction": true
  }
}
```
