import asyncio
import hashlib
import logging
import os
import pathlib
import shutil
from typing import Any

import anyio
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncConnection

from ..db.schema import package_publish_audit_log
from ..schema.packages import PackagePublishMetadata

logger = logging.getLogger(__name__)


class PublishError(Exception):
    """Raised when a publish operation fails validation or processing."""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def validate_metadata(meta: PackagePublishMetadata) -> None:
    """Validate package metadata before accepting an upload."""

    if not meta.category:
        raise PublishError("category is required")
    if not meta.name:
        raise PublishError("name is required")
    if not meta.version:
        raise PublishError("version is required")
    if not meta.distfiles:
        raise PublishError("at least one distfile is required")
    if not meta.binary and not meta.blob:
        raise PublishError("at least one of binary or blob is required")
    if not meta.metadata.desc:
        raise PublishError("metadata.desc is required")
    if not meta.metadata.vendor.name:
        raise PublishError("metadata.vendor.name is required")


def verify_distfile_integrity(
    file_path: str,
    expected_size: int,
    expected_sha256: str,
    expected_sha512: str,
) -> None:
    """Verify a distfile's size and checksums."""

    try:
        actual_size = os.path.getsize(file_path)
    except FileNotFoundError:
        raise PublishError(f"distfile not found: {file_path}", 500)

    if actual_size != expected_size:
        raise PublishError(
            f"size mismatch: expected {expected_size}, got {actual_size}"
        )

    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()

    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
            sha512.update(chunk)

    actual_sha256 = sha256.hexdigest()
    actual_sha512 = sha512.hexdigest()

    if actual_sha256 != expected_sha256:
        raise PublishError(
            f"sha256 mismatch: expected {expected_sha256}, got {actual_sha256}"
        )
    if actual_sha512 != expected_sha512:
        raise PublishError(
            f"sha512 mismatch: expected {expected_sha512}, got {actual_sha512}"
        )


def check_collision(
    staging_dir: str,
    committed_dir: str,
    distfile_name: str,
    expected_size: int,
) -> None:
    """Check if a distfile with the same name already exists with different content."""

    for check_dir in [staging_dir, committed_dir]:
        existing = os.path.join(check_dir, distfile_name)
        if os.path.exists(existing):
            existing_size = os.path.getsize(existing)
            if existing_size != expected_size:
                raise PublishError(
                    f"distfile '{distfile_name}' already exists with different size "
                    f"(existing: {existing_size}, new: {expected_size})",
                    409,
                )
            # Same name, same size — likely the same file, allow it (idempotent upload)


def check_manifest_exists(
    packages_index_dir: str,
    category: str,
    name: str,
    version: str,
) -> None:
    """Check if a manifest with the same category/name/version already exists."""

    manifest_path = os.path.join(
        packages_index_dir, "packages", category, name, f"{version}.toml"
    )
    if os.path.exists(manifest_path):
        raise PublishError(
            f"manifest already exists: {category}/{name}/{version}.toml",
            409,
        )


def generate_manifest_toml(meta: PackagePublishMetadata) -> str:
    """Generate a canonical TOML manifest from upload metadata."""

    lines: list[str] = []
    lines.append('format = "v1"')
    lines.append("")
    lines.append("[metadata]")
    lines.append(f'desc = "{_escape_toml_string(meta.metadata.desc)}"')
    vendor_name = _escape_toml_string(meta.metadata.vendor.name)
    if meta.metadata.vendor.eula:
        eula = _escape_toml_string(meta.metadata.vendor.eula)
        lines.append(f'vendor = {{ name = "{vendor_name}", eula = "{eula}" }}')
    else:
        lines.append(f'vendor = {{ name = "{vendor_name}", eula = "" }}')

    for df in meta.distfiles:
        lines.append("")
        lines.append("[[distfiles]]")
        lines.append(f'name = "{_escape_toml_string(df.name)}"')
        lines.append(f"size = {df.size}")
        lines.append("")
        lines.append("[distfiles.checksums]")
        lines.append(f'sha256 = "{df.checksums.sha256}"')
        lines.append(f'sha512 = "{df.checksums.sha512}"')
        if df.strip_components != 1:
            lines.append(f"strip_components = {df.strip_components}")

    for bh in meta.binary:
        lines.append("")
        lines.append("[[binary]]")
        lines.append(f'host = "{_escape_toml_string(bh.host)}"')
        distfiles_list = ", ".join(
            f'"{_escape_toml_string(d)}"' for d in bh.distfiles
        )
        lines.append(f"distfiles = [{distfiles_list}]")

    for bh in meta.blob:
        lines.append("")
        lines.append("[[blob]]")
        lines.append(f'host = "{_escape_toml_string(bh.host)}"')
        distfiles_list = ", ".join(
            f'"{_escape_toml_string(d)}"' for d in bh.distfiles
        )
        lines.append(f"distfiles = [{distfiles_list}]")

    lines.append("")
    return "\n".join(lines)


def _escape_toml_string(s: str) -> str:
    """Escape a string for TOML double-quoted string."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


async def store_distfile(
    src_path: str,
    staging_dir: str,
    distfile_name: str,
) -> str:
    """Move an uploaded file to the staging directory. Returns the staged path."""

    pathlib.Path(staging_dir).mkdir(parents=True, exist_ok=True)
    dest = os.path.join(staging_dir, distfile_name)
    shutil.move(src_path, dest)
    return dest


async def sync_to_mirror(
    staging_dir: str,
    rsync_url: str,
    rsync_pass: str | None,
) -> None:
    """Rsync the staging directory to the mirror."""

    env = os.environ.copy()
    if rsync_pass:
        env["RSYNC_PASSWORD"] = rsync_pass

    # rsync individual files from staging to remote dist/ dir
    # -av: archive + verbose
    # --no-relative: don't recreate directory structure
    remote_spec = rsync_url.rstrip("/") + "/"
    local_spec = staging_dir + "/"

    process = await asyncio.create_subprocess_exec(
        "rsync",
        "-av",
        "--no-relative",
        local_spec,
        remote_spec,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise PublishError(
            f"mirror sync failed (rsync exit code {process.returncode}): "
            f"{stderr.decode('utf-8', 'replace')}",
            502,
        )


async def move_to_committed(
    staging_dir: str,
    committed_dir: str,
    distfile_name: str,
) -> None:
    """Move a distfile from staging to committed after successful mirror sync."""

    pathlib.Path(committed_dir).mkdir(parents=True, exist_ok=True)
    src = os.path.join(staging_dir, distfile_name)
    dest = os.path.join(committed_dir, distfile_name)
    shutil.move(src, dest)


async def update_packages_index(
    packages_index_dir: str,
    category: str,
    name: str,
    version: str,
    manifest_toml: str,
    github_token: str,
    user: str,
) -> str:
    """Write manifest to packages-index, commit, and open a PR.

    Returns the PR URL.
    """

    pkg_dir = os.path.join(packages_index_dir, "packages", category, name)
    pathlib.Path(pkg_dir).mkdir(parents=True, exist_ok=True)

    manifest_path = os.path.join(pkg_dir, f"{version}.toml")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_toml)

    branch_name = f"publish/{category}/{name}/{version}"

    # git operations
    async def _git(*args: str) -> None:
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=packages_index_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise PublishError(
                f"git {args[0]} failed: {stderr.decode('utf-8', 'replace')}",
                502,
            )

    await _git("checkout", "main")
    await _git("pull", "--ff-only")
    await _git("checkout", "-b", branch_name)

    manifest_rel = os.path.relpath(manifest_path, packages_index_dir)
    await _git("add", manifest_rel)

    commit_msg = (
        f"feat(packages): add {category}/{name} {version}\n\n"
        f"Automated publish by {user}"
    )
    await _git("commit", "-s", "-m", commit_msg)

    # push using token auth
    push_url = (
        f"https://x-access-token:{github_token}@github.com/"
        f"ruyisdk/packages-index.git"
    )
    await _git("push", push_url, f"HEAD:{branch_name}")

    # open PR via gh CLI
    proc = await asyncio.create_subprocess_exec(
        "gh",
        "pr",
        "create",
        "--repo",
        "ruyisdk/packages-index",
        "--base",
        "main",
        "--head",
        branch_name,
        "--title",
        f"feat(packages): add {category}/{name} {version}",
        "--body",
        f"Automated package publish by `{user}`.\n\n"
        f"**Category**: {category}\n"
        f"**Name**: {name}\n"
        f"**Version**: {version}",
        env={**os.environ, "GITHUB_TOKEN": github_token},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise PublishError(
            f"gh pr create failed: {stderr.decode('utf-8', 'replace')}",
            502,
        )

    pr_url = stdout.decode("utf-8").strip()

    # clean up: switch back to main and delete local branch
    await _git("checkout", "main")
    await _git("branch", "-D", branch_name)

    return pr_url


async def write_audit_log(
    conn: AsyncConnection,
    user: str,
    action: str,
    package_info: dict[str, Any],
    distfile_name: str,
    status: str,
    details: dict[str, Any],
) -> None:
    """Write an entry to the package publish audit log."""

    await conn.execute(
        insert(package_publish_audit_log).values(
            user=user,
            action=action,
            package_info=package_info,
            distfile_name=distfile_name,
            status=status,
            details=details,
        )
    )
