import json
import tempfile
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from ..components.auth import DIUser, User
from ..components.package_publisher import (
    PublishError,
    check_collision,
    check_manifest_exists,
    generate_manifest_toml,
    move_to_committed,
    store_distfile,
    sync_to_mirror,
    update_packages_index,
    validate_metadata,
    verify_distfile_integrity,
    write_audit_log,
)
from ..config.env import DIEnvConfig
from ..db.conn import DIMainDB
from ..schema.packages import PackagePublishMetadata

router = APIRouter(prefix="/packages")


@router.post("/upload-v1", status_code=201)
async def package_upload_v1(
    distfile: Annotated[UploadFile, File()],
    metadata_json: Annotated[str, Form(alias="metadata")],
    main_db: DIMainDB,
    cfg: DIEnvConfig,
    user: DIUser,
) -> dict:
    """Upload a distfile with package metadata for publishing.

    Requires admin or dev authentication. The distfile is verified for
    integrity (size + checksums), then synced to the mirror and a PR is
    opened to packages-index.
    """

    if not cfg.publish.staging_dir:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Package publishing is not configured",
        )

    # Parse metadata
    try:
        meta_dict = json.loads(metadata_json)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metadata JSON: {e}",
        )

    try:
        meta = PackagePublishMetadata.model_validate(meta_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metadata: {e}",
        )

    package_info = {
        "category": meta.category,
        "name": meta.name,
        "version": meta.version,
    }

    # Write uploaded file to a temp path for integrity verification
    with tempfile.NamedTemporaryFile(delete=False, suffix="-upload") as tmp:
        tmp_path = tmp.name
        while chunk := await distfile.read(65536):
            tmp.write(chunk)

    try:
        # Validate metadata structure
        try:
            validate_metadata(meta)
        except PublishError as e:
            async with main_db.connect() as conn:
                await write_audit_log(
                    conn,
                    user=user.username,
                    action="reject",
                    package_info=package_info,
                    distfile_name="(unknown)",
                    status="failure",
                    details={"error": e.detail},
                )
                await conn.commit()
            raise HTTPException(status_code=e.status_code, detail=e.detail)

        # We handle the first distfile from the upload (the one that was actually sent)
        if len(meta.distfiles) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Currently exactly one distfile per upload is supported",
            )

        df = meta.distfiles[0]

        # Verify integrity
        try:
            verify_distfile_integrity(
                tmp_path,
                expected_size=df.size,
                expected_sha256=df.checksums.sha256,
                expected_sha512=df.checksums.sha512,
            )
        except PublishError as e:
            async with main_db.connect() as conn:
                await write_audit_log(
                    conn,
                    user=user.username,
                    action="reject",
                    package_info=package_info,
                    distfile_name=df.name,
                    status="failure",
                    details={"error": e.detail, "checksums": df.checksums.model_dump()},
                )
                await conn.commit()
            raise HTTPException(status_code=e.status_code, detail=e.detail)

        # Check for collision
        try:
            check_collision(
                cfg.publish.staging_dir,
                cfg.publish.committed_dir,
                df.name,
                df.size,
            )
        except PublishError as e:
            async with main_db.connect() as conn:
                await write_audit_log(
                    conn,
                    user=user.username,
                    action="reject",
                    package_info=package_info,
                    distfile_name=df.name,
                    status="failure",
                    details={"error": e.detail},
                )
                await conn.commit()
            raise HTTPException(status_code=e.status_code, detail=e.detail)

        # Check manifest doesn't already exist in index
        if cfg.publish.packages_index_dir:
            try:
                check_manifest_exists(
                    cfg.publish.packages_index_dir,
                    meta.category,
                    meta.name,
                    meta.version,
                )
            except PublishError as e:
                async with main_db.connect() as conn:
                    await write_audit_log(
                        conn,
                        user=user.username,
                        action="reject",
                        package_info=package_info,
                        distfile_name=df.name,
                        status="failure",
                        details={"error": e.detail},
                    )
                    await conn.commit()
                raise HTTPException(status_code=e.status_code, detail=e.detail)

        # Store distfile to staging
        staged_path = await store_distfile(
            tmp_path, cfg.publish.staging_dir, df.name
        )

        # Sync to mirror
        pr_url = None
        mirror_error = None
        try:
            await sync_to_mirror(
                cfg.publish.staging_dir,
                cfg.publish.mirror_rsync_url,
                cfg.publish.mirror_rsync_pass or None,
            )
        except PublishError as e:
            mirror_error = e.detail
            # Don't raise — we still want to record the upload attempt
            # and the distfile is in staging for retry

        # Move to committed (if mirror sync succeeded)
        if mirror_error is None:
            await move_to_committed(
                cfg.publish.staging_dir, cfg.publish.committed_dir, df.name
            )

        # Update packages-index (PR)
        index_error = None
        if cfg.publish.packages_index_dir and cfg.publish.github_token_for_pr and mirror_error is None:
            try:
                manifest_toml = generate_manifest_toml(meta)
                pr_url = await update_packages_index(
                    cfg.publish.packages_index_dir,
                    meta.category,
                    meta.name,
                    meta.version,
                    manifest_toml,
                    cfg.publish.github_token_for_pr,
                    user.username,
                )
            except PublishError as e:
                index_error = e.detail

        # Audit log
        details = {
            "checksums": df.checksums.model_dump(),
            "size": df.size,
        }
        if pr_url:
            details["pr_url"] = pr_url
        if mirror_error:
            details["mirror_error"] = mirror_error
        if index_error:
            details["index_error"] = index_error

        overall_status = "success" if not mirror_error and not index_error else "partial"

        async with main_db.connect() as conn:
            await write_audit_log(
                conn,
                user=user.username,
                action="upload",
                package_info=package_info,
                distfile_name=df.name,
                status=overall_status,
                details=details,
            )
            await conn.commit()

        if mirror_error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Mirror sync failed: {mirror_error}",
            )
        if index_error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Index update failed: {index_error}",
            )

        response: dict = {
            "status": "ok",
            "distfile": df.name,
            "package": f"{meta.category}/{meta.name}-{meta.version}",
        }
        if pr_url:
            response["pr_url"] = pr_url

        return response

    finally:
        # Clean up temp file
        import os

        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
