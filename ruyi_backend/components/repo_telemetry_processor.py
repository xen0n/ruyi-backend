from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncConnection

from ..db.schema import (
    ModelRepoTelemetryAggregatedEvent,
    repo_telemetry_aggregated_events,
)
from ..schema.repo_telemetry import RepoUploadPayload


def _extract_param(params: list[tuple[str, str]], key: str) -> str:
    """Extract a parameter value from the aggregated event params list."""
    for k, v in params:
        if k == key:
            return v
    return ""


async def process_repo_telemetry_data(
    conn: AsyncConnection,
    raw_events: list[RepoUploadPayload],
) -> None:
    """
    Processes raw repo telemetry events, extracts package install/uninstall
    data, and stores aggregated results in the database.
    """

    # Aggregate by (time_bucket, kind, pkg_name, pkg_version, host)
    # key -> total count
    agg: dict[tuple[str, str, str, str, str], int] = {}

    for upload in raw_events:
        for ev in upload.events:
            pkg_name = _extract_param(ev.params, "pkg_name")
            pkg_version = _extract_param(ev.params, "pkg_version")
            host = _extract_param(ev.params, "host")

            agg_key = (ev.time_bucket, ev.kind, pkg_name, pkg_version, host)
            agg[agg_key] = agg.get(agg_key, 0) + ev.count

    if not agg:
        return

    # Batch insert aggregated results
    rows: list[ModelRepoTelemetryAggregatedEvent] = [
        {
            "time_bucket": key[0],
            "kind": key[1],
            "pkg_name": key[2],
            "pkg_version": key[3],
            "host": key[4],
            "count": count,
        }
        for key, count in sorted(agg.items())
    ]

    await conn.execute(
        insert(repo_telemetry_aggregated_events).values(rows)
    )
