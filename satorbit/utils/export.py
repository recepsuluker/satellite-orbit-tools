"""Export utilities — CSV and HTML report generation."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from satorbit.engine.collision_detector import CollisionAnalysis
from satorbit.engine.visibility_calculator import VisibilityResult
from satorbit.logging_config import get_logger

logger = get_logger("utils.export")


def conjunction_events_to_csv(analysis: CollisionAnalysis) -> str:
    """Export conjunction events to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Time (UTC)",
            "Satellite A",
            "NORAD A",
            "Satellite B",
            "NORAD B",
            "Distance (km)",
            "Rel. Velocity (km/s)",
            "Risk Score",
            "Lat A",
            "Lon A",
            "Alt A (km)",
            "Lat B",
            "Lon B",
            "Alt B (km)",
        ]
    )
    for e in analysis.events:
        writer.writerow(
            [
                e.time.strftime("%Y-%m-%d %H:%M:%S"),
                e.satellite_a,
                e.norad_id_a,
                e.satellite_b,
                e.norad_id_b,
                f"{e.distance_km:.4f}",
                f"{e.relative_velocity_km_s:.4f}",
                f"{e.risk_score:.2f}",
                f"{e.pos_a[0]:.4f}",
                f"{e.pos_a[1]:.4f}",
                f"{e.pos_a[2]:.2f}",
                f"{e.pos_b[0]:.4f}",
                f"{e.pos_b[1]:.4f}",
                f"{e.pos_b[2]:.2f}",
            ]
        )
    return output.getvalue()


def passes_to_csv(result: VisibilityResult) -> str:
    """Export pass predictions to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Satellite",
            "NORAD ID",
            "AOS Time",
            "AOS Azimuth",
            "MAX Time",
            "MAX Elevation",
            "MAX Azimuth",
            "LOS Time",
            "LOS Azimuth",
            "Duration (s)",
            "Max Distance (km)",
        ]
    )
    for p in result.passes:
        writer.writerow(
            [
                p.satellite_name,
                p.norad_id,
                p.aos_time.strftime("%Y-%m-%d %H:%M:%S"),
                f"{p.aos_azimuth:.1f}",
                p.max_time.strftime("%Y-%m-%d %H:%M:%S"),
                f"{p.max_elevation:.1f}",
                f"{p.max_azimuth:.1f}",
                p.los_time.strftime("%Y-%m-%d %H:%M:%S"),
                f"{p.los_azimuth:.1f}",
                f"{p.duration_seconds:.0f}",
                f"{p.max_distance_km:.1f}",
            ]
        )
    return output.getvalue()


def generate_html_report(analysis: CollisionAnalysis) -> str:
    """Generate a styled HTML collision analysis report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    rows_html = ""
    for e in analysis.events:
        if e.risk_score >= 70:
            risk_class = "high"
            risk_badge = "HIGH"
        elif e.risk_score >= 30:
            risk_class = "medium"
            risk_badge = "MEDIUM"
        else:
            risk_class = "low"
            risk_badge = "LOW"

        rows_html += f"""
        <tr>
            <td>{e.time.strftime("%Y-%m-%d %H:%M")}</td>
            <td>{e.satellite_a}<br><small>NORAD {e.norad_id_a}</small></td>
            <td>{e.satellite_b}<br><small>NORAD {e.norad_id_b}</small></td>
            <td><strong>{e.distance_km:.3f}</strong> km</td>
            <td>{e.relative_velocity_km_s:.2f} km/s</td>
            <td><span class="badge {risk_class}">{risk_badge} ({e.risk_score})</span></td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Collision Analysis Report — Satellite Orbit Tools</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0a0e1a; color: #e0e0e0; padding: 2rem; }}
  h1 {{ color: #60a5fa; margin-bottom: 0.5rem; }}
  .meta {{ color: #888; margin-bottom: 1.5rem; }}
  .summary {{ display: flex; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; }}
  .card {{ background: #1a1f35; border-radius: 8px; padding: 1rem 1.5rem; min-width: 180px; }}
  .card .label {{ color: #888; font-size: 0.85rem; }}
  .card .value {{ font-size: 1.5rem; font-weight: 700; color: #60a5fa; }}
  .card.danger .value {{ color: #ef4444; }}
  .card.warning .value {{ color: #f59e0b; }}
  table {{ width: 100%; border-collapse: collapse; background: #1a1f35; border-radius: 8px; overflow: hidden; }}
  th {{ background: #252b45; padding: 0.75rem; text-align: left; color: #60a5fa; font-size: 0.85rem; text-transform: uppercase; }}
  td {{ padding: 0.75rem; border-top: 1px solid #252b45; }}
  tr:hover {{ background: #252b45; }}
  .badge {{ padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }}
  .badge.high {{ background: #ef444433; color: #ef4444; }}
  .badge.medium {{ background: #f59e0b33; color: #f59e0b; }}
  .badge.low {{ background: #22c55e33; color: #22c55e; }}
  small {{ color: #666; }}
  footer {{ margin-top: 2rem; color: #555; font-size: 0.85rem; text-align: center; }}
</style>
</head>
<body>
<h1>Collision Analysis Report</h1>
<p class="meta">Generated: {now} | Threshold: {analysis.threshold_km} km | Duration: {analysis.analysis_duration_sec:.2f}s</p>

<div class="summary">
  <div class="card"><div class="label">Pairs Checked</div><div class="value">{analysis.total_pairs_checked:,}</div></div>
  <div class="card"><div class="label">Conjunctions</div><div class="value">{analysis.total_conjunctions}</div></div>
  <div class="card danger"><div class="label">High Risk</div><div class="value">{analysis.high_risk_count}</div></div>
  <div class="card warning"><div class="label">Medium Risk</div><div class="value">{analysis.medium_risk_count}</div></div>
  <div class="card"><div class="label">Low Risk</div><div class="value">{analysis.low_risk_count}</div></div>
</div>

<table>
<thead>
  <tr><th>Time</th><th>Satellite A</th><th>Satellite B</th><th>Distance</th><th>Rel. Velocity</th><th>Risk</th></tr>
</thead>
<tbody>
  {rows_html if rows_html else '<tr><td colspan="6" style="text-align:center;padding:2rem;">No conjunction events detected</td></tr>'}
</tbody>
</table>

<footer>Satellite Orbit Tools v1.0 — Real-time Collision Detection System</footer>
</body>
</html>"""
