"""Read-only PostgreSQL projection for the prospective dashboard."""

from __future__ import annotations

from datetime import datetime, timezone
import math


def _iso(value):
    return None if value is None else value.isoformat()


def _score_summary(rows: list[dict], revision: str) -> dict:
    selected = [row for row in rows if row["revision"] == revision]
    events = sum(row["event_count"] for row in selected)
    total = sum(row["total_gain"] for row in selected)
    mean = None if not events else total / events
    return {
        "days": len({row["target_date"] for row in selected}),
        "events": events,
        "total_gain": total,
        "mean_igpe": mean,
        "relative_factor": None if mean is None else math.exp(mean),
    }


def _dry_run_progress(rows: list[dict], region_ids: list[str], planned_days: int) -> dict:
    expected = set(region_ids)

    def complete_days(revision: str) -> int:
        coverage = {}
        for row in rows:
            if row["revision"] == revision:
                coverage.setdefault(row["target_date"], set()).add(row["region_id"])
        return sum(regions >= expected for regions in coverage.values()) if expected else 0

    provisional_days = complete_days("provisional")
    final_days = complete_days("final")
    if final_days >= planned_days:
        phase = "complete"
    elif provisional_days >= planned_days:
        phase = "settling"
    elif provisional_days:
        phase = "running"
    else:
        phase = "awaiting_scores"
    return {
        "phase": phase,
        "planned_days": planned_days,
        "provisional_days": min(provisional_days, planned_days),
        "final_days": min(final_days, planned_days),
    }


def build_dashboard(connection, protocol_id: str, now=None) -> dict:
    generated_at = now or datetime.now(timezone.utc)
    protocol_row = connection.execute(
        """
        SELECT status, config, planned_days, minimum_events
        FROM prospective.protocols WHERE protocol_id = %s
        """,
        (protocol_id,),
    ).fetchone()
    if protocol_row is None:
        raise ValueError("prospective dashboard protocol is missing")
    config = protocol_row[1]
    region_rows = connection.execute(
        """
        SELECT region_id, name, catalog_source, minimum_magnitude,
               minimum_depth_km, maximum_depth_km
        FROM prospective.regions
        WHERE protocol_id = %s
        ORDER BY region_id
        """,
        (protocol_id,),
    ).fetchall()
    run_rows = connection.execute(
        """
        SELECT DISTINCT ON (region_id)
               region_id, run_id, issue_time, target_start, target_end,
               status, finished_at, state_id,
               (SELECT count(*) FROM prospective.forecast_artifacts a
                WHERE a.run_id = r.run_id)
        FROM prospective.forecast_runs r
        WHERE protocol_id = %s
        ORDER BY region_id, target_start DESC
        """,
        (protocol_id,),
    ).fetchall()
    latest_runs = {
        row[0]: {
            "run_id": row[1],
            "issue_time": _iso(row[2]),
            "target_start": _iso(row[3]),
            "target_end": _iso(row[4]),
            "status": row[5],
            "finished_at": _iso(row[6]),
            "state_id": row[7],
            "artifacts": int(row[8]),
        }
        for row in run_rows
    }
    catalog_rows = connection.execute(
        """
        SELECT DISTINCT ON (region_id)
               region_id, source_cutoff_at, event_count, content_sha256
        FROM prospective.catalog_snapshots
        WHERE region_id = ANY(%s) AND collection_kind = 'rolling'
        ORDER BY region_id, source_cutoff_at DESC, captured_at DESC
        """,
        ([row[0] for row in region_rows],),
    ).fetchall()
    latest_catalogs = {
        row[0]: {
            "cutoff": _iso(row[1]),
            "window_events": int(row[2]),
            "sha256": row[3],
        }
        for row in catalog_rows
    }
    score_rows = connection.execute(
        """
        SELECT region_id, target_date, score_revision, event_count,
               total_log_likelihood_gain, mean_igpe, computed_at
        FROM prospective.daily_scores
        WHERE protocol_id = %s
        ORDER BY target_date, region_id, score_revision
        """,
        (protocol_id,),
    ).fetchall()
    scores = [
        {
            "region_id": row[0],
            "target_date": row[1].isoformat(),
            "revision": row[2],
            "event_count": int(row[3]),
            "total_gain": float(row[4]),
            "mean_igpe": None if row[5] is None else float(row[5]),
            "computed_at": _iso(row[6]),
        }
        for row in score_rows
    ]
    incident_row = connection.execute(
        """
        SELECT count(*), max(occurred_at)
        FROM prospective.incidents
        WHERE protocol_id = %s AND resolved_at IS NULL
          AND severity IN ('warning', 'critical')
        """,
        (protocol_id,),
    ).fetchone()
    operational_rows = connection.execute(
        """
        SELECT region_id, primary_eligible, missed_region_days,
               consecutive_missed_days, invalidated_at, invalidation_reason
        FROM prospective.region_operational_status
        WHERE protocol_id = %s
        """,
        (protocol_id,),
    ).fetchall()
    operational = {
        row[0]: {
            "primary_eligible": bool(row[1]),
            "missed_region_days": int(row[2]),
            "consecutive_missed_days": int(row[3]),
            "invalidated_at": _iso(row[4]),
            "invalidation_reason": row[5],
        }
        for row in operational_rows
    }
    regions = []
    for row in region_rows:
        region_id = row[0]
        region_scores = [score for score in scores if score["region_id"] == region_id]
        regions.append({
            "region_id": region_id,
            "name": row[1],
            "catalog_source": row[2],
            "minimum_magnitude": float(row[3]),
            "minimum_depth_km": None if row[4] is None else float(row[4]),
            "maximum_depth_km": None if row[5] is None else float(row[5]),
            "latest_forecast": latest_runs.get(region_id),
            "latest_catalog": latest_catalogs.get(region_id),
            "provisional": _score_summary(region_scores, "provisional"),
            "final": _score_summary(region_scores, "final"),
            "operations": operational.get(region_id, {
                "primary_eligible": True,
                "missed_region_days": 0,
                "consecutive_missed_days": 0,
                "invalidated_at": None,
                "invalidation_reason": None,
            }),
        })
    latest_targets = {
        item["latest_forecast"]["target_start"]
        for item in regions
        if item["latest_forecast"] is not None
    }
    published_regions = sum(
        item["latest_forecast"] is not None
        and item["latest_forecast"]["status"] == "published"
        and item["latest_forecast"]["artifacts"] == 6
        for item in regions
    )
    open_incidents = int(incident_row[0])
    pooled_primary_eligible = all(
        item["operations"]["primary_eligible"] for item in regions
    )
    pipeline_status = (
        "ok"
        if published_regions == len(regions)
        and len(latest_targets) == 1
        and open_incidents == 0
        and pooled_primary_eligible
        else "attention"
    )
    planned_days = int(protocol_row[2])
    return {
        "schema_version": 2,
        "generated_at": generated_at.isoformat(),
        "pipeline_status": pipeline_status,
        "protocol": {
            "protocol_id": protocol_id,
            "database_status": protocol_row[0],
            "mode": config["mode"],
            "counts_toward_prospective_claim": config["counts_toward_prospective_claim"],
            "planned_days": planned_days,
            "minimum_events": int(protocol_row[3]),
            "settled_score_delay_days": config["catalog_revision_contract"]["settled_score_delay_days"],
        },
        "latest_target_start": next(iter(latest_targets)) if len(latest_targets) == 1 else None,
        "published_regions": published_regions,
        "open_incidents": open_incidents,
        "last_incident_at": _iso(incident_row[1]),
        "pooled_primary_claim_status": (
            "eligible" if pooled_primary_eligible else "inconclusive"
        ),
        "dry_run": _dry_run_progress(
            scores, [row[0] for row in region_rows], planned_days
        ),
        "provisional": _score_summary(scores, "provisional"),
        "final": _score_summary(scores, "final"),
        "regions": regions,
        "daily_scores": scores,
    }


def read_dashboard(database_url: str, protocol_id: str) -> dict:
    import psycopg

    with psycopg.connect(database_url, connect_timeout=5) as connection:
        return build_dashboard(connection, protocol_id)
