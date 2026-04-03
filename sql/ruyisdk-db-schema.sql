CREATE TABLE `telemetry_raw_uploads` (
    `id` BIGINT(20) AUTO_INCREMENT PRIMARY KEY,
    `nonce` UUID NOT NULL COMMENT 'Nonce for server-side event de-duping',
    `raw_events` JSON COMMENT 'The raw JSON payload',
    `created_at` TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
    `is_processed` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Whether this row has been processed',
    UNIQUE KEY `idx_telemetry_raw_uploads_nonce` (`nonce`),
    KEY `idx_telemetry_raw_uploads_ctime_processed` (`created_at`, `is_processed`)
) ENGINE InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `telemetry_ruyi_versions` (
    `id` BIGINT(20) AUTO_INCREMENT PRIMARY KEY,
    `version` VARCHAR(255) NOT NULL COMMENT 'The version of ruyi that generated the data',
    `created_at` TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
    KEY `idx_telemetry_ruyi_versions_ctime_version` (`created_at`, `version`)
) ENGINE InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `telemetry_raw_installation_infos` (
    `id` BIGINT(20) AUTO_INCREMENT PRIMARY KEY,
    `report_uuid` UUID NOT NULL COMMENT 'The UUID of the report',
    `raw` JSON COMMENT 'The raw JSON payload of the installation info',
    `created_at` TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `idx_telemetry_raw_installation_infos_report_uuid` (`report_uuid`),
    KEY `idx_telemetry_raw_installation_infos_ctime` (`created_at`)
) ENGINE InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `telemetry_installation_infos` (
    `id` BIGINT(20) AUTO_INCREMENT PRIMARY KEY,
    `report_uuid` UUID NOT NULL COMMENT 'The UUID of the report',
    `arch` VARCHAR(32) NOT NULL COMMENT 'The architecture of the installation',
    `ci` VARCHAR(128) NOT NULL COMMENT 'Kind of CI environment the installation was working in',
    `libc_name` VARCHAR(32) NOT NULL COMMENT 'The libc of the installation environment',
    `libc_ver` VARCHAR(128) NOT NULL COMMENT 'The libc version of the installation environment',
    `os` VARCHAR(32) NOT NULL COMMENT 'The OS of the installation environment',
    `os_release_id` VARCHAR(128) NOT NULL COMMENT 'The OS release ID',
    `os_release_version_id` VARCHAR(128) NOT NULL COMMENT 'The OS release version ID',
    `shell` VARCHAR(32) NOT NULL COMMENT 'The $SHELL of the working environment',
    `created_at` TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `idx_telemetry_installation_infos_report_uuid` (`report_uuid`),
    KEY `idx_telemetry_installation_infos_ctime` (`created_at`)
) ENGINE InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `telemetry_riscv_machine_infos` (
    `id` BIGINT(20) AUTO_INCREMENT PRIMARY KEY,
    `model_name` VARCHAR(255) NOT NULL COMMENT 'The model name of the RISC-V machine',
    `cpu_count` INT NOT NULL COMMENT 'The number of CPUs in the machine',
    `isa` VARCHAR(1024) NOT NULL COMMENT 'The ISA string of the machine',
    `uarch` VARCHAR(255) NOT NULL COMMENT 'The microarchitecture of the machine from /proc/cpuinfo',
    `uarch_csr` VARCHAR(255) NOT NULL COMMENT 'The uarch CSR values of the machine, "{mvendorid:x}:{marchid:x}:{mimpid:x}" or "unknown"',
    `mmu` VARCHAR(255) NOT NULL COMMENT 'The MMU characteristic of the machine from /proc/cpuinfo, "svXX" or "unknown"',
    `created_at` TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
    KEY `idx_telemetry_riscv_machine_infos_ctime` (`created_at`)
) ENGINE InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `telemetry_aggregated_events` (
    `id` BIGINT(20) AUTO_INCREMENT PRIMARY KEY,
    `time_bucket` VARCHAR(255) NOT NULL,
    `kind` VARCHAR(255) NOT NULL,
    `params_kv_raw` JSON NOT NULL,
    `count` INT NOT NULL,
    `created_at` TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
    CHECK (JSON_VALID(`params_kv_raw`)),
    KEY `idx_telemetry_aggregated_events_ctime_time_bucket_kind` (`created_at`, `time_bucket`, `kind`)
) ENGINE InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `repo_telemetry_raw_uploads` (
    `id` BIGINT(20) AUTO_INCREMENT PRIMARY KEY,
    `nonce` UUID NOT NULL COMMENT 'Nonce for server-side event de-duping',
    `raw_events` JSON COMMENT 'The raw JSON payload',
    `created_at` TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
    `is_processed` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Whether this row has been processed',
    UNIQUE KEY `idx_repo_telemetry_raw_uploads_nonce` (`nonce`),
    KEY `idx_repo_telemetry_raw_uploads_ctime_processed` (`created_at`, `is_processed`)
) ENGINE InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `repo_telemetry_aggregated_events` (
    `id` BIGINT(20) AUTO_INCREMENT PRIMARY KEY,
    `time_bucket` VARCHAR(255) NOT NULL,
    `kind` VARCHAR(255) NOT NULL,
    `pkg_name` VARCHAR(255) NOT NULL,
    `pkg_version` VARCHAR(255) NOT NULL,
    `host` VARCHAR(255) NOT NULL,
    `count` INT NOT NULL,
    `created_at` TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
    KEY `idx_repo_telemetry_aggregated_events_ctime_time_bucket_kind` (`created_at`, `time_bucket`, `kind`),
    KEY `idx_repo_telemetry_aggregated_events_pkg_name` (`pkg_name`)
) ENGINE InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `package_publish_audit_log` (
    `id` BIGINT(20) AUTO_INCREMENT PRIMARY KEY,
    `user` VARCHAR(255) NOT NULL COMMENT 'Username of the publisher',
    `action` VARCHAR(64) NOT NULL COMMENT 'Action type: upload, reject, commit',
    `package_info` JSON NOT NULL COMMENT 'Package metadata: category, name, version',
    `distfile_name` VARCHAR(1024) NOT NULL COMMENT 'Name of the distfile',
    `status` VARCHAR(32) NOT NULL COMMENT 'Outcome: success, failure',
    `details` JSON NOT NULL COMMENT 'Additional details: errors, checksums, etc.',
    `created_at` TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
    CHECK (JSON_VALID(`package_info`)),
    CHECK (JSON_VALID(`details`)),
    KEY `idx_package_publish_audit_log_user_ctime` (`user`, `created_at`),
    KEY `idx_package_publish_audit_log_ctime` (`created_at`)
) ENGINE InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `download_stats_daily_pypi` (
    `id` BIGINT(20) AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(255) NOT NULL COMMENT 'The name of the PyPI package',
    `version` VARCHAR(255) NOT NULL COMMENT 'The version of the PyPI package',
    `date` TIMESTAMP NOT NULL COMMENT 'The date of the download stats',
    `count` INT NOT NULL DEFAULT 0 COMMENT 'The number of downloads on that date',
    `created_at` TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `idx_download_stats_daily_pypi_name_version_date` (`name`, `version`, `date`)
) ENGINE InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
