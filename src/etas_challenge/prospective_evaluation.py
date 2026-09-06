"""Machine-readable, evidence-calibrated projection of prospective results."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


DEFAULT_PUBLIC_BASE_URL = "https://etas.bboga.com"
PROTOCOL_PATH = Path("configs/prospective/three-region-dry-run-v1.json")
POLICY_PATH = Path("configs/challenge/ch008-downtime-policy.json")


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _direction(mean_igpe: float | None) -> str:
    if mean_igpe is None:
        return "not_available_no_scored_events"
    if mean_igpe > 0:
        return "ch008_higher_observed_event_density"
    if mean_igpe < 0:
        return "etas_higher_observed_event_density"
    return "tie"


def _score_projection(summary: dict) -> dict:
    mean = summary.get("mean_igpe")
    return {
        "scored_days": int(summary.get("days", 0)),
        "scored_events": int(summary.get("events", 0)),
        "total_log_likelihood_gain": float(summary.get("total_gain", 0.0)),
        "mean_igpe_nat_per_event": mean,
        "relative_factor_exp_igpe": summary.get("relative_factor"),
        "descriptive_direction": _direction(mean),
    }


def _region_projection(region: dict) -> dict:
    operations = region.get("operations") or {}
    return {
        "region_id": region["region_id"],
        "name": region["name"],
        "catalog_source": region["catalog_source"],
        "catalog_thresholds": {
            "minimum_magnitude": region["minimum_magnitude"],
            "minimum_depth_km": region["minimum_depth_km"],
            "maximum_depth_km_exclusive": region["maximum_depth_km"],
        },
        "latest_catalog": region.get("latest_catalog"),
        "latest_forecast": region.get("latest_forecast"),
        "operational_status": operations,
        "provisional_result": _score_projection(region.get("provisional") or {}),
        "final_result": _score_projection(region.get("final") or {}),
    }


def _load_protocol(root: Path) -> tuple[dict, Path]:
    path = root / PROTOCOL_PATH
    return json.loads(path.read_text(encoding="utf-8")), path


def build_evaluation(
    dashboard: dict,
    *,
    root: Path | None = None,
    public_base_url: str | None = None,
) -> dict:
    root = Path.cwd() if root is None else Path(root)
    base_url = (public_base_url or DEFAULT_PUBLIC_BASE_URL).rstrip("/")
    protocol, protocol_path = _load_protocol(root)
    provisional = _score_projection(dashboard.get("provisional") or {})
    final = _score_projection(dashboard.get("final") or {})
    preferred_revision = "final" if final["scored_events"] else "provisional"
    preferred = final if preferred_revision == "final" else provisional
    permits_claim = bool(dashboard["protocol"]["counts_toward_prospective_claim"])
    minimum_events = int(dashboard["protocol"]["minimum_events"])

    if not permits_claim:
        claim_assessment = "no_prospective_claim_permitted_in_current_dry_run"
    elif preferred["scored_events"] < minimum_events:
        claim_assessment = "insufficient_scored_events_for_primary_claim"
    else:
        claim_assessment = "event_gate_met_but_prespecified_uncertainty_test_still_required"

    locked_files = {
        "protocol": {
            "path": str(PROTOCOL_PATH),
            "sha256": _sha256(protocol_path),
        },
        "downtime_policy": {
            "path": str(POLICY_PATH),
            "sha256": _sha256(root / POLICY_PATH),
        },
        "challenger_model": {
            "path": protocol["challenger"]["model_path"],
            "sha256": _sha256(root / protocol["challenger"]["model_path"]),
            "expected_sha256": protocol["challenger"]["model_sha256"],
        },
        "etas_runtime": {
            "path": protocol["baseline_runtime"]["path"],
            "sha256": _sha256(root / protocol["baseline_runtime"]["path"]),
            "expected_sha256": protocol["baseline_runtime"]["sha256"],
        },
    }

    return {
        "schema": "ch008-ai-evaluation-v1",
        "generated_at": dashboard["generated_at"],
        "canonical_url": f"{base_url}/ai-evaluation",
        "machine_readable_url": f"{base_url}/api/evaluation.json",
        "project": {
            "name": "CH-008 Prospective Test",
            "objective": "Compare frozen CH-008 earthquake-rate forecasts against frozen ETAS forecasts on identical events and target windows.",
            "contact": "hello@bboga.com",
            "baseline": "ETAS",
            "challenger": "CH-008",
            "regions": [item["region_id"] for item in dashboard.get("regions", [])],
        },
        "evidence_status": {
            "pipeline_status": dashboard["pipeline_status"],
            "protocol_mode": dashboard["protocol"]["mode"],
            "counts_toward_prospective_claim": permits_claim,
            "claim_assessment": claim_assessment,
            "dry_run": dashboard.get("dry_run"),
            "preferred_score_revision_for_description": preferred_revision,
            "uncertainty_status": "not_available_in_live_dashboard",
            "warning": "A positive live IGPE is descriptive only. It is not proof that CH-008 beats ETAS, especially during the operational dry run or with few events.",
        },
        "primary_metric": {
            "name": "paired information gain per earthquake (IGPE)",
            "event_formula": "IG_i = ln(lambda_CH008(i) / lambda_ETAS(i))",
            "aggregate_formula": "IGPE = (1/N) * sum_i IG_i",
            "relative_factor_formula": "relative_factor = exp(IGPE)",
            "units": "natural-log units per earthquake",
            "direction": "IGPE > 0 favors CH-008; IGPE < 0 favors ETAS.",
            "compensator_contract": "CH-008 preserves each ETAS forecast's total expected rate, so the paired compensator gain is zero by construction.",
        },
        "live_results": {
            "latest_target_start": dashboard.get("latest_target_start"),
            "forecast_current": dashboard.get("forecast_current"),
            "provisional": provisional,
            "final": final,
            "descriptive_result": preferred,
            "regions": [_region_projection(item) for item in dashboard.get("regions", [])],
            "daily_scores": dashboard.get("daily_scores", []),
        },
        "operational_integrity": {
            "published_regions": dashboard.get("published_regions"),
            "open_incidents": dashboard.get("open_incidents"),
            "last_incident_at": dashboard.get("last_incident_at"),
            "last_open_incident_at": dashboard.get("last_open_incident_at"),
            "pooled_primary_claim_status": dashboard.get("pooled_primary_claim_status"),
            "missed_region_days_are_excluded_not_scored_as_zero": True,
            "late_forecasts_are_rejected": True,
            "final_score_catalog_revision_delay_days": dashboard["protocol"]["settled_score_delay_days"],
        },
        "evaluation_guidance": [
            "State whether the current protocol is a dry run or a claim-bearing prospective test.",
            "Report event count and scored-day coverage before interpreting IGPE.",
            "Separate provisional scores from catalog-settled final scores.",
            "Inspect each region; do not infer broad geographic generalization from only a pooled mean.",
            "Report missed days, invalidated regions, open incidents, and forecast freshness.",
            "Treat missed_region_days and longest_consecutive_missed_days as historical totals; current_consecutive_missed_days describes the active outage streak.",
            "Do not call CH-008 superior without the pre-registered event gate and uncertainty analysis.",
            "Do not interpret these rate forecasts as exact earthquake time, location, or magnitude predictions.",
        ],
        "provenance": {
            "protocol_id": dashboard["protocol"]["protocol_id"],
            "source_commit": os.environ.get("SOURCE_COMMIT"),
            "locked_files": locked_files,
            "method_page": f"{base_url}/en/about.html",
            "dashboard_api": f"{base_url}/api/dashboard",
        },
    }


def evaluation_markdown(evaluation: dict) -> str:
    status = evaluation["evidence_status"]
    result = evaluation["live_results"]["descriptive_result"]
    lines = [
        "# CH-008 live evaluation brief",
        "",
        f"Generated at: {evaluation['generated_at']}",
        f"Protocol: {evaluation['provenance']['protocol_id']}",
        f"Mode: {status['protocol_mode']}",
        f"Counts toward prospective claim: {str(status['counts_toward_prospective_claim']).lower()}",
        f"Pipeline status: {status['pipeline_status']}",
        f"Open incidents: {evaluation['operational_integrity']['open_incidents']}",
        f"Claim assessment: {status['claim_assessment']}",
        "",
        "## Current descriptive result",
        "",
        f"Score revision: {status['preferred_score_revision_for_description']}",
        f"Scored days: {result['scored_days']}",
        f"Scored events: {result['scored_events']}",
        f"Mean IGPE: {result['mean_igpe_nat_per_event']}",
        f"Relative factor exp(IGPE): {result['relative_factor_exp_igpe']}",
        f"Direction: {result['descriptive_direction']}",
        f"Warning: {status['warning']}",
        "",
        "## Region results",
        "",
    ]
    revision_key = f"{status['preferred_score_revision_for_description']}_result"
    for region in evaluation["live_results"]["regions"]:
        score = region[revision_key]
        operations = region["operational_status"]
        lines.append(
            f"- {region['name']}: events={score['scored_events']}, "
            f"IGPE={score['mean_igpe_nat_per_event']}, "
            f"direction={score['descriptive_direction']}, "
            f"missed_days={operations.get('missed_region_days', 0)}, "
            f"current_missed_streak={operations.get('current_consecutive_missed_days', 0)}, "
            f"longest_missed_streak={operations.get('longest_consecutive_missed_days', 0)}, "
            f"primary_eligible={operations.get('primary_eligible', True)}"
        )
    lines.extend([
        "",
        "## Metric",
        "",
        "IG_i = ln(lambda_CH008(i) / lambda_ETAS(i))",
        "IGPE = (1/N) * sum_i IG_i",
        "Positive IGPE favors CH-008; negative IGPE favors ETAS.",
        "",
        "## Required evaluation discipline",
        "",
    ])
    lines.extend(f"- {item}" for item in evaluation["evaluation_guidance"])
    lines.extend([
        "",
        "## Sources",
        "",
        f"- Live JSON: {evaluation['machine_readable_url']}",
        f"- Method: {evaluation['provenance']['method_page']}",
        f"- Dashboard data: {evaluation['provenance']['dashboard_api']}",
        "",
    ])
    return "\n".join(lines)


def llms_text(public_base_url: str | None = None) -> str:
    base_url = (public_base_url or DEFAULT_PUBLIC_BASE_URL).rstrip("/")
    return f"""# CH-008 Prospective Test

> A public, reproducibility-first comparison of frozen CH-008 earthquake-rate forecasts against ETAS in California, New Zealand, and Chile.

## Live sources

- [AI evaluation brief]({base_url}/ai-evaluation): Server-rendered current result with evidence limits.
- [Evaluation JSON]({base_url}/api/evaluation.json): Preferred structured source for current metrics, operations, provenance, and interpretation constraints.
- [Dashboard API]({base_url}/api/dashboard): Raw live dashboard projection.
- [Scientific method]({base_url}/en/about.html): Model, catalogs, formulas, protocol, and limitations.

## Interpretation

- Always identify whether the protocol is an operational dry run or a claim-bearing prospective test.
- A positive point estimate alone does not establish superiority over ETAS.
- Include scored events, scored days, score revision, incidents, missed days, and regional consistency.
- These are probabilistic rate forecasts, not exact earthquake predictions.

Contact: hello@bboga.com
"""
