# PlacementIQ — Evals Report

**Overall:** 🟢 **PASS**  
**Ran at:** 2026-05-20T10:51:45+00:00

| Suite | Status | Key metrics |
|---|---|---|
| score_calibration | 🟢 pass | accuracy 1.00 (≥ 0.9), sensitivity Δ 1.35 (≥ 1.0) |
| gap_relevance | 🟢 pass | full-match 5/5, #1 correct 5/5 |
| early_warning | 🟢 pass | recall 1.00, false positives 0 (≤ 1) |

## score_calibration — 🟢 pass

| Metric | Value |
|---|---|
| directional_accuracy | 1 |
| correct | 10 |
| total | 10 |
| min_accuracy | 0.9 |
| sensitivity_delta | 1.35 |
| sensitivity_min_delta | 1 |

<details><summary>All cases</summary>

| Case | Result | Expected | Actual | Note |
|---|---|---|---|---|
| CAL_001 | ✅ pass | `placed` | `{"overall": 87.2, "bucket": "placed"}` | Strong BFSI candidate, top-quartile scores |
| CAL_002 | ✅ pass | `placed` | `{"overall": 84.4, "bucket": "placed"}` | Strong Analytics candidate |
| CAL_003 | ✅ pass | `placed` | `{"overall": 81.0, "bucket": "placed"}` | Solid Digital Marketing candidate |
| CAL_004 | ✅ pass | `placed` | `{"overall": 76.4, "bucket": "placed"}` | BFSI candidate just above the placed threshold |
| CAL_005 | ✅ pass | `not_placed` | `{"overall": 35.8, "bucket": "not_placed"}` | Clearly weak BFSI candidate |
| CAL_006 | ✅ pass | `not_placed` | `{"overall": 41.6, "bucket": "not_placed"}` | Weak Analytics candidate, mildly declining |
| CAL_007 | ✅ pass | `not_placed` | `{"overall": 43.2, "bucket": "not_placed"}` | Disengaged Digital Marketing candidate |
| CAL_008 | ✅ pass | `not_placed` | `{"overall": 45.6, "bucket": "not_placed"}` | BFSI candidate just under the not-placed threshold |
| CAL_009 | ✅ pass | `borderline` | `{"overall": 67.8, "bucket": "borderline"}` | Sensitivity pair — baseline (BFSI, mid-band) |
| CAL_010 | ✅ pass | `borderline` | `{"overall": 69.15, "bucket": "borderline"}` | Sensitivity pair — perturbed (+15 to every cycle of financial_math) |
| sensitivity[CAL_009→CAL_010] | ✅ pass | `{"min_overall_delta": 1.0, "perturbation": "Adds 15 to each of the 3 cycles of financial_math (BFSI Q). Q has 2 sub-skills and 0.30 weight \u2192 expected overall delta \u2248 1.35."}` | `{"overall_delta": 1.35}` | Adds 15 to each of the 3 cycles of financial_math (BFSI Q). Q has 2 sub-skills and 0.30 weight → expected overall delta ≈ 1.35. |

</details>

## gap_relevance — 🟢 pass

| Metric | Value |
|---|---|
| profiles_full_match | 5 |
| profiles_first_correct | 5 |
| profiles_total | 5 |
| full_match_required | 4 |
| first_correct_required | 5 |

<details><summary>All cases</summary>

| Case | Result | Expected | Actual | Note |
|---|---|---|---|---|
| GAP_001 | ✅ pass | `["financial_math", "quant_aptitude", "banking_fundamentals"]` | `["financial_math", "quant_aptitude", "banking_fundamentals"]` | BFSI student — Q dimension underwater, modest D gap. financial_math beats quant_aptitude by larger raw gap. |
| GAP_002 | ✅ pass | `["data_interpretation", "sql_basics", "stats_fundamentals"]` | `["data_interpretation", "sql_basics", "stats_fundamentals"]` | Analytics student — clearly weak in Q's data_interpretation; sql_basics and stats_fundamentals tie on priority but sql_basics wins the alphabetical tiebreak. |
| GAP_003 | ✅ pass | `["copywriting", "seo_fundamentals", "social_media_strategy"]` | `["copywriting", "seo_fundamentals", "social_media_strategy"]` | Digital Marketing — copywriting (E) leads despite 0.30 weight because the raw gap is large; D gaps follow. |
| GAP_004 | ✅ pass | `["business_communication", "presentation", "accounting_basics"]` | `["business_communication", "presentation", "accounting_basics"]` | BFSI student — E-dimension weak (business_communication and presentation tied on priority; alphabetical tiebreak picks business_communication first). |
| GAP_005 | ✅ pass | `["excel_modelling", "stats_fundamentals", "sql_basics"]` | `["excel_modelling", "stats_fundamentals", "sql_basics"]` | Analytics student — all gaps live in D dimension; excel_modelling has the biggest raw gap. |

</details>

## early_warning — 🟢 pass

| Metric | Value |
|---|---|
| recall | 1 |
| true_positives | 4 |
| false_negatives | 0 |
| false_positives | 0 |
| false_positive_rate | 0 |
| min_recall | 1 |
| max_false_positives | 1 |

<details><summary>All cases</summary>

| Case | Result | Expected | Actual | Note |
|---|---|---|---|---|
| WARN_001 | ✅ pass | `{"at_risk": true}` | `{"at_risk": true, "readiness": 46.6, "trajectory_slope": -3.5, "days_to_placement": 120, "risk_level": "medium"}` | BFSI student, all subskills declining — should be flagged. |
| WARN_002 | ✅ pass | `{"at_risk": true}` | `{"at_risk": true, "readiness": 52.2, "trajectory_slope": -3.5, "days_to_placement": 100, "risk_level": "medium"}` | Analytics student trending down — slope clearly negative, readiness just under 55. |
| WARN_003 | ✅ pass | `{"at_risk": true}` | `{"at_risk": true, "readiness": 46.0, "trajectory_slope": 0.0, "days_to_placement": 130, "risk_level": "medium"}` | Digital Marketing student stuck — flat low scores, low attendance, low engagement. |
| WARN_004 | ✅ pass | `{"at_risk": true}` | `{"at_risk": true, "readiness": 52.8, "trajectory_slope": -2.5, "days_to_placement": 60, "risk_level": "medium"}` | Days-to-placement at the 60-day boundary — should still flag. |
| WARN_005 | ✅ pass | `{"at_risk": false}` | `{"at_risk": false, "readiness": 49.6, "trajectory_slope": 7.5, "days_to_placement": 120, "risk_level": "medium"}` | Low absolute readiness BUT clearly improving — positive slope should save the student from being flagged. |
| WARN_006 | ✅ pass | `{"at_risk": false}` | `{"at_risk": false, "readiness": 67.4, "trajectory_slope": 1.5, "days_to_placement": 100, "risk_level": "low"}` | Borderline-but-above-threshold student. Readiness above 55, no flag. |
| WARN_007 | ✅ pass | `{"at_risk": false}` | `{"at_risk": false, "readiness": 83.8, "trajectory_slope": 2.5, "days_to_placement": 100, "risk_level": "low"}` | Strong student well clear of the threshold. |
| WARN_008 | ✅ pass | `{"at_risk": false}` | `{"at_risk": false, "readiness": 42.6, "trajectory_slope": -2.5, "days_to_placement": 30, "risk_level": "high"}` | Weak student but days_to_placement < 60 — intervention window has closed; should NOT flag (architecture §4.2 floor). |

</details>

