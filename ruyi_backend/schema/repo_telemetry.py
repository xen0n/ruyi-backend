from pydantic import BaseModel, PositiveInt

from .client_telemetry import AggregatedTelemetryEvent


class RepoUploadPayload(BaseModel):
    """Upload payload for repo-scoped telemetry data.

    Simpler than the PM upload payload: no installation info or report UUID
    needed, since repo telemetry is about package install/uninstall events
    rather than client environment details.
    """

    fmt: PositiveInt
    nonce: str
    ruyi_version: str
    events: list[AggregatedTelemetryEvent] = []
