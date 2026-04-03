from fastapi import APIRouter
from sqlalchemy import text

from ..db.conn import DIMainDB
from ..schema.repo_telemetry import RepoUploadPayload

router = APIRouter(prefix="/telemetry")


@router.post("/repo/upload-v1", status_code=204)
async def telemetry_repo_upload_v1(
    payload: RepoUploadPayload, main_db: DIMainDB
) -> None:
    if payload.fmt != 1:
        raise ValueError("Invalid telemetry format version")

    async with main_db.connect() as conn:
        # Record the raw aggregated events into repo_telemetry_raw_uploads
        # De-duping is achieved by using INSERT IGNORE INTO and the unique
        # constraint on the nonce column
        await conn.execute(
            text(
                "INSERT IGNORE INTO `repo_telemetry_raw_uploads` (`nonce`, `raw_events`) VALUES (:nonce, :raw_events)"
            ),
            {
                "nonce": payload.nonce,
                "raw_events": payload.model_dump_json(),
            },
        )

        await conn.commit()

    return None
