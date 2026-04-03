import datetime
from typing import NotRequired, Sequence, TypedDict
import uuid

from sqlalchemy import (
    Table,
    Column,
    MetaData,
    BIGINT,
    BOOLEAN,
    TIMESTAMP,
    VARCHAR,
    JSON,
    UUID,
    INT,
    CheckConstraint,
)
from sqlalchemy.sql import func

from ..schema.client_telemetry import AggregatedTelemetryEvent, NodeInfo

metadata = MetaData()


class ModelTelemetryRawUpload(TypedDict):
    id: NotRequired[int]
    nonce: uuid.UUID
    raw_events: Sequence[AggregatedTelemetryEvent]
    created_at: NotRequired[datetime.datetime]
    is_processed: bool


telemetry_raw_uploads = Table(
    "telemetry_raw_uploads",
    metadata,
    Column("id", BIGINT(), primary_key=True, autoincrement=True),
    Column("nonce", UUID(), nullable=False),
    Column("raw_events", JSON()),
    Column(
        "created_at", TIMESTAMP(timezone=False), server_default=func.current_timestamp()
    ),
    Column("is_processed", BOOLEAN(), nullable=False, default=False),
)


class ModelTelemetryRuyiVersion(TypedDict):
    id: NotRequired[int]
    version: str
    created_at: NotRequired[datetime.datetime]


telemetry_ruyi_versions = Table(
    "telemetry_ruyi_versions",
    metadata,
    Column("id", BIGINT(), primary_key=True, autoincrement=True),
    Column("version", VARCHAR(255), nullable=False),
    Column(
        "created_at", TIMESTAMP(timezone=False), server_default=func.current_timestamp()
    ),
)


class ModelTelemetryRawInstallationInfo(TypedDict):
    id: NotRequired[int]
    report_uuid: uuid.UUID
    raw: NodeInfo
    created_at: NotRequired[datetime.datetime]


telemetry_raw_installation_infos = Table(
    "telemetry_raw_installation_infos",
    metadata,
    Column("id", BIGINT(), primary_key=True, autoincrement=True),
    Column("report_uuid", UUID(), nullable=False),
    Column("raw", JSON()),
    Column(
        "created_at", TIMESTAMP(timezone=False), server_default=func.current_timestamp()
    ),
)


class ModelTelemetryInstallationInfo(TypedDict):
    id: NotRequired[int]
    report_uuid: uuid.UUID
    arch: str
    ci: str
    libc_name: str
    libc_ver: str
    os: str
    os_release_id: str
    os_release_version_id: str
    shell: str
    created_at: NotRequired[datetime.datetime]


telemetry_installation_infos = Table(
    "telemetry_installation_infos",
    metadata,
    Column("id", BIGINT(), primary_key=True, autoincrement=True),
    Column("report_uuid", UUID(), nullable=False),
    Column("arch", VARCHAR(32), nullable=False),
    Column("ci", VARCHAR(128), nullable=False),
    Column("libc_name", VARCHAR(32), nullable=False),
    Column("libc_ver", VARCHAR(128), nullable=False),
    Column("os", VARCHAR(32), nullable=False),
    Column("os_release_id", VARCHAR(128), nullable=False),
    Column("os_release_version_id", VARCHAR(128), nullable=False),
    Column("shell", VARCHAR(32), nullable=False),
    Column(
        "created_at", TIMESTAMP(timezone=False), server_default=func.current_timestamp()
    ),
)


class ModelTelemetryRISCVMachineInfo(TypedDict):
    id: NotRequired[int]
    model_name: str
    cpu_count: int
    isa: str
    uarch: str
    uarch_csr: str
    mmu: str
    created_at: NotRequired[datetime.datetime]


telemetry_riscv_machine_infos = Table(
    "telemetry_riscv_machine_infos",
    metadata,
    Column("id", BIGINT(), primary_key=True, autoincrement=True),
    Column("model_name", VARCHAR(255), nullable=False),
    Column("cpu_count", INT(), nullable=False),
    Column("isa", VARCHAR(1024), nullable=False),
    Column("uarch", VARCHAR(255), nullable=False),
    Column("uarch_csr", VARCHAR(255), nullable=False),
    Column("mmu", VARCHAR(255), nullable=False),
    Column(
        "created_at", TIMESTAMP(timezone=False), server_default=func.current_timestamp()
    ),
)


class ModelTelemetryAggregatedEvent(TypedDict):
    id: NotRequired[int]
    time_bucket: str
    kind: str
    params_kv_raw: Sequence[list[str] | tuple[str, str]]
    count: int
    created_at: NotRequired[datetime.datetime]


telemetry_aggregated_events = Table(
    "telemetry_aggregated_events",
    metadata,
    Column("id", BIGINT(), primary_key=True, autoincrement=True),
    Column("time_bucket", VARCHAR(255), nullable=False),
    Column("kind", VARCHAR(255), nullable=False),
    Column("params_kv_raw", JSON(), nullable=False),
    Column("count", INT(), nullable=False),
    Column(
        "created_at", TIMESTAMP(timezone=False), server_default=func.current_timestamp()
    ),
    CheckConstraint("JSON_VALID(`params_kv_raw`)"),
)


class ModelRepoTelemetryRawUpload(TypedDict):
    id: NotRequired[int]
    nonce: uuid.UUID
    raw_events: Sequence[AggregatedTelemetryEvent]
    created_at: NotRequired[datetime.datetime]
    is_processed: bool


repo_telemetry_raw_uploads = Table(
    "repo_telemetry_raw_uploads",
    metadata,
    Column("id", BIGINT(), primary_key=True, autoincrement=True),
    Column("nonce", UUID(), nullable=False),
    Column("raw_events", JSON()),
    Column(
        "created_at", TIMESTAMP(timezone=False), server_default=func.current_timestamp()
    ),
    Column("is_processed", BOOLEAN(), nullable=False, default=False),
)


class ModelRepoTelemetryAggregatedEvent(TypedDict):
    id: NotRequired[int]
    time_bucket: str
    kind: str
    pkg_name: str
    pkg_version: str
    host: str
    count: int
    created_at: NotRequired[datetime.datetime]


repo_telemetry_aggregated_events = Table(
    "repo_telemetry_aggregated_events",
    metadata,
    Column("id", BIGINT(), primary_key=True, autoincrement=True),
    Column("time_bucket", VARCHAR(255), nullable=False),
    Column("kind", VARCHAR(255), nullable=False),
    Column("pkg_name", VARCHAR(255), nullable=False),
    Column("pkg_version", VARCHAR(255), nullable=False),
    Column("host", VARCHAR(255), nullable=False),
    Column("count", INT(), nullable=False),
    Column(
        "created_at", TIMESTAMP(timezone=False), server_default=func.current_timestamp()
    ),
)


class ModelDownloadStatsDailyPyPI(TypedDict):
    id: NotRequired[int]
    name: str
    version: str
    date: datetime.datetime
    count: int
    created_at: NotRequired[datetime.datetime]


download_stats_daily_pypi = Table(
    "download_stats_daily_pypi",
    metadata,
    Column("id", BIGINT(), primary_key=True, autoincrement=True),
    Column("name", VARCHAR(255), nullable=False),
    Column("version", VARCHAR(255), nullable=False),
    Column("date", TIMESTAMP(timezone=False), nullable=False),
    Column("count", INT(), nullable=False, default=0),
    Column(
        "created_at", TIMESTAMP(timezone=False), server_default=func.current_timestamp()
    ),
)
