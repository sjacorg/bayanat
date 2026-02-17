from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta
from typing import Optional

import boto3
from botocore.config import Config as BotoConfig
from flask import (
    Response,
    request,
    current_app,
    send_from_directory,
    abort,
    jsonify,
    render_template,
)
from flask_security import auth_required
from flask_security.decorators import current_user, roles_accepted
from sqlalchemy import func, desc
from werkzeug.utils import safe_join, secure_filename

from enferno.admin.models import Media, Activity, Extraction
from enferno.extensions import db, rds
from enferno.utils.data_helpers import get_file_hash
from enferno.utils.http_response import HTTPResponse
from enferno.utils.logging_utils import get_logger
from enferno.utils.text_utils import normalize_arabic
from enferno.utils.validation_utils import validate_with
from enferno.admin.validation.models import MediaRequestModel
import enferno.utils.typing as t
from . import admin

logger = get_logger()

GRACE_PERIOD = timedelta(hours=2)
S3_URL_EXPIRY = 3600


def _media_url(media_file):
    """Generate a URL for a media file based on storage backend."""
    if not media_file:
        return None
    if current_app.config.get("FILESYSTEM_LOCAL"):
        return safe_join("/admin/api/serve/media", media_file)
    s3 = boto3.client(
        "s3",
        config=BotoConfig(signature_version="s3v4"),
        aws_access_key_id=current_app.config["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=current_app.config["AWS_SECRET_ACCESS_KEY"],
        region_name=current_app.config["AWS_REGION"],
    )
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": current_app.config["S3_BUCKET"], "Key": media_file},
        ExpiresIn=S3_URL_EXPIRY,
    )


# Media dashboard page route
@admin.route("/media/", defaults={"id": None})
@admin.route("/media/<int:id>")
def media_dashboard(id: Optional[t.id]) -> str:
    """Endpoint for media management."""
    return render_template("admin/media-dashboard.html")


@admin.post("/api/media/chunk")
@roles_accepted("Admin", "DA")
def api_medias_chunk() -> Response:
    """
    Endpoint for uploading media files based on file system settings.

    Returns:
        - success/error string based on the operation result.
    """
    file = request.files["file"]

    # to check if file is uploaded from media import tool
    import_upload = "/import/media/" in request.referrer
    # validate file extensions based on user and referrer
    if import_upload:
        # uploads from media import tool
        # must be Admin user
        if current_user.has_role("Admin"):
            allowed_extensions = current_app.config["ETL_VID_EXT"]
            if not Media.validate_file_extension(file.filename, allowed_extensions):
                return HTTPResponse.error("This file type is not allowed", status=415)
        else:
            Activity.create(
                current_user,
                Activity.ACTION_UPLOAD,
                Activity.STATUS_DENIED,
                request.json,
                "media",
                details="Non-admin user attempted to upload media file using import endpoint.",
            )
            return HTTPResponse.forbidden("Unauthorized")
    else:
        # normal uploads by DA or Admin users
        allowed_extensions = current_app.config["MEDIA_ALLOWED_EXTENSIONS"]
        if not Media.validate_file_extension(file.filename, allowed_extensions):
            Activity.create(
                current_user,
                Activity.STATUS_DENIED,
                Activity.ACTION_UPLOAD,
                request.json,
                "media",
                details="User attempted to upload unallowed file type.",
            )
            return HTTPResponse.error("This file type is not allowed", status=415)

    filename = Media.generate_file_name(file.filename)
    filepath = (Media.media_dir / filename).as_posix()

    dz_uuid = request.form.get("dzuuid")

    # Chunked upload
    try:
        current_chunk = int(request.form["dzchunkindex"])
        total_chunks = int(request.form["dztotalchunkcount"])
        total_size = int(request.form["dztotalfilesize"])
    except KeyError as err:
        raise abort(400, body=f"Not all required fields supplied, missing {err}")
    except ValueError:
        raise abort(400, body="Values provided were not in expected format")

    # validate dz_uuid
    if not safe_join(str(Media.media_file), dz_uuid):
        return HTTPResponse.error("Invalid Request", status=425)

    save_dir = Media.media_dir / secure_filename(dz_uuid)

    # validate current chunk
    if not safe_join(str(save_dir), str(current_chunk)) or current_chunk.__class__ != int:
        return HTTPResponse.error("Invalid Request", status=425)

    if not save_dir.exists():
        save_dir.mkdir(exist_ok=True, parents=True)

    # Save the individual chunk
    with open(save_dir / secure_filename(str(current_chunk)), "wb") as f:
        file.save(f)

    # See if we have all the chunks downloaded
    completed = current_chunk == total_chunks - 1

    # Concat all the files into the final file when all are downloaded
    if completed:
        with open(filepath, "wb") as f:
            for file_number in range(total_chunks):
                f.write((save_dir / str(file_number)).read_bytes())

        if os.stat(filepath).st_size != total_size:
            return HTTPResponse.error("Error uploading the file")

        shutil.rmtree(save_dir)
        # get md5 hash
        etag = get_file_hash(filepath)

        # validate etag here // if it exists // reject the upload and send an error code
        if Media.query.filter(Media.etag == etag, Media.deleted.is_not(True)).first():
            return HTTPResponse.error("Error, file already exists", status=409)

        if not current_app.config["FILESYSTEM_LOCAL"] and not import_upload:
            s3 = boto3.resource(
                "s3",
                aws_access_key_id=current_app.config["AWS_ACCESS_KEY_ID"],
                aws_secret_access_key=current_app.config["AWS_SECRET_ACCESS_KEY"],
                region_name=current_app.config["AWS_REGION"],
            )
            s3.Bucket(current_app.config["S3_BUCKET"]).upload_file(filepath, filename)
            # Clean up file if s3 mode is selected
            try:
                os.remove(filepath)
            except Exception as e:
                logger.error(e, exc_info=True)

        response = {"etag": etag, "filename": filename, "original_filename": file.filename}
        Activity.create(
            current_user, Activity.ACTION_UPLOAD, Activity.STATUS_SUCCESS, response, "media"
        )
        return HTTPResponse.success(data=response)

    return HTTPResponse.success(message="Chunk upload successful")


@admin.post("/api/media/upload/")
@roles_accepted("Admin", "DA")
def api_medias_upload() -> Response:
    """
    Endpoint to upload screenshots based on file system settings.

    Returns:
        - success/error string based on the operation result.
    """
    file = request.files.get("file")
    if not file:
        return HTTPResponse.error("Invalid request params", status=400)

    # normal uploads by DA or Admin users
    allowed_extensions = current_app.config["MEDIA_ALLOWED_EXTENSIONS"]
    if not Media.validate_file_extension(file.filename, allowed_extensions):
        Activity.create(
            current_user,
            Activity.STATUS_DENIED,
            Activity.ACTION_UPLOAD,
            request.json,
            "media",
            details="User attempted to upload unallowed file type.",
        )
        return HTTPResponse.error("This file type is not allowed", status=415)

    if current_app.config["FILESYSTEM_LOCAL"]:
        file = request.files.get("file")
        # final file
        filename = Media.generate_file_name(file.filename)
        filepath = (Media.media_dir / filename).as_posix()

        with open(filepath, "wb") as f:
            file.save(f)
        # get md5 hash
        etag = get_file_hash(filepath)
        # check if file already exists
        if Media.query.filter(Media.etag == etag, Media.deleted is not True).first():
            return HTTPResponse.error("Error: File already exists", status=409)

        response = {"etag": etag, "filename": filename}

        return HTTPResponse.success(data=response)
    else:
        s3 = boto3.resource(
            "s3",
            aws_access_key_id=current_app.config["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=current_app.config["AWS_SECRET_ACCESS_KEY"],
        )

        # final file
        filename = Media.generate_file_name(file.filename)
        # filepath = (Media.media_dir/filename).as_posix()

        response = s3.Bucket(current_app.config["S3_BUCKET"]).put_object(Key=filename, Body=file)

        etag = response.get()["ETag"].replace('"', "")

        # check if file already exists
        if Media.query.filter(Media.etag == etag, Media.deleted is not True).first():
            return HTTPResponse.error("Error: File already exists", status=409)

        return HTTPResponse.success(data={"filename": filename, "etag": etag})


# return signed url from s3 valid for some time
@admin.route("/api/media/<filename>")
def serve_media(
    filename: str,
) -> Response:
    """
    Endpoint to generate file urls to be served (based on file system type.)

    Args:
        - filename: name of the file.

    Returns:
        - temporarily accessible url of the file.
    """

    if current_app.config["FILESYSTEM_LOCAL"]:
        file_path = safe_join("/admin/api/serve/media", filename)
        if file_path:
            return HTTPResponse.success(data={"url": file_path})
        else:
            return HTTPResponse.error("Invalid Request", status=425)
    else:
        # validate access control
        media = Media.query.filter(Media.media_file == filename).first()

        s3_config = BotoConfig(signature_version="s3v4")

        s3 = boto3.client(
            "s3",
            config=s3_config,
            aws_access_key_id=current_app.config["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=current_app.config["AWS_SECRET_ACCESS_KEY"],
            region_name=current_app.config["AWS_REGION"],
        )

        # allow generation of s3 urls for a short period while the media is not created
        if media is None:
            # this means the file is not in the database
            # we allow serving it briefly while the user is still creating the media
            try:
                # Get the last modified time of the file
                resp = s3.head_object(Bucket=current_app.config["S3_BUCKET"], Key=filename)
                last_modified = resp["LastModified"]

                # Check if file is uploaded within the grace period
                if datetime.utcnow() - last_modified.replace(tzinfo=None) <= GRACE_PERIOD:
                    params = {"Bucket": current_app.config["S3_BUCKET"], "Key": filename}
                    url = s3.generate_presigned_url("get_object", Params=params, ExpiresIn=36000)
                    return HTTPResponse.success(data={"url": url})
                else:
                    Activity.create(
                        current_user,
                        Activity.ACTION_VIEW,
                        Activity.STATUS_DENIED,
                        {"file": filename},
                        "media",
                        details="Unauthorized attempt to access restricted media file.",
                    )
                    return HTTPResponse.forbidden("Restricted Access")
            except s3.exceptions.NoSuchKey:
                return HTTPResponse.not_found("File not found")
            except Exception:
                return HTTPResponse.error("Internal Server Error", status=500)
        else:
            # media exists in the database, check access control restrictions
            if not current_user.can_access(media):
                Activity.create(
                    current_user,
                    Activity.ACTION_VIEW,
                    Activity.STATUS_DENIED,
                    request.json,
                    "media",
                    details="Unauthorized attempt to access restricted media file.",
                )
                return HTTPResponse.forbidden("Restricted Access")

            params = {"Bucket": current_app.config["S3_BUCKET"], "Key": filename}
            if filename.lower().endswith("pdf"):
                params["ResponseContentType"] = "application/pdf"
            return HTTPResponse.success(
                data={
                    "url": s3.generate_presigned_url(
                        "get_object", Params=params, ExpiresIn=S3_URL_EXPIRY
                    )
                },
            )


@admin.route("/api/serve/media/<filename>")
def api_local_serve_media(
    filename: str,
) -> Response:
    """
    serves file from local file system.

    Args:
        - filename: name of the file.

    Returns:
        - file to be served.
    """

    media = Media.query.filter(Media.media_file == filename).first()

    if media and not current_user.can_access(media):
        Activity.create(
            current_user,
            Activity.ACTION_VIEW,
            Activity.STATUS_DENIED,
            request.json,
            "media",
            details="Unauthorized attempt to access restricted media file.",
        )
        return HTTPResponse.forbidden("Restricted Access")
    else:
        if media:
            Activity.create(
                current_user,
                Activity.ACTION_VIEW,
                Activity.STATUS_SUCCESS,
                media.to_mini() if media else {"file": filename},
                "media",
            )
        return send_from_directory("media", filename)


@admin.post("/api/inline/upload")
@roles_accepted("Admin", "DA")
def api_inline_medias_upload() -> Response:
    """
    Endpoint to upload inline media files.

    Returns:
        - success/error string based on the operation result.
    """
    try:
        f = request.files.get("file")

        # final file
        filename = Media.generate_file_name(f.filename)
        filepath = (Media.inline_dir / filename).as_posix()
        f.save(filepath)
        response = {"location": filename}

        return HTTPResponse.success(data=response)
    except Exception as e:
        logger.error(e, exc_info=True)
        return HTTPResponse.error("Request Failed", status=500)


@admin.route("/api/serve/inline/<filename>")
def api_local_serve_inline_media(filename: str) -> Response:
    """
    serves inline media files - only for authenticated users.

    Args:
        - filename: name of the file.

    Returns:
        - file to be served.
    """
    return send_from_directory("media/inline", filename)


# Medias routes


@admin.get("/api/media/<int:id>")
@auth_required("session")
def api_media_get(id: int):
    """Get a single media item by ID with extraction and bulletin info."""
    media = Media.query.get(id)
    if media is None:
        return HTTPResponse.not_found("Media not found")

    if not current_user.can_access(media):
        return HTTPResponse.forbidden("Restricted Access")

    item = media.to_dict()
    item["extraction"] = media.extraction.to_dict() if media.extraction else None
    item["ocr_status"] = media.extraction.status if media.extraction else "pending"
    if media.bulletin:
        item["bulletin"] = {"id": media.bulletin.id, "title": media.bulletin.title}
    else:
        item["bulletin"] = None
    media_url = _media_url(media.media_file)
    item["media_url"] = media_url
    item["thumbnail_url"] = media_url
    item["url"] = media_url

    return jsonify(item)


@admin.put("/api/media/<int:id>")
@roles_accepted("Admin", "DA")
@validate_with(MediaRequestModel)
def api_media_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update a media item.

    Args:
        - id: id of the media
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    media = Media.query.get(id)
    if media is None:
        return HTTPResponse.not_found("Media not found")

    if not current_user.can_access(media):
        Activity.create(
            current_user,
            Activity.ACTION_VIEW,
            Activity.STATUS_DENIED,
            validated_data,
            "media",
            details="Unauthorized attempt to update restricted media.",
        )
        return HTTPResponse.forbidden("Restricted Access")

    media = media.from_json(validated_data["item"])
    if media.save():
        Activity.create(
            current_user,
            Activity.ACTION_VIEW,
            Activity.STATUS_SUCCESS,
            validated_data,
            "media",
        )
        return HTTPResponse.success(message=f"Media {id} updated")
    else:
        return HTTPResponse.error("Error updating Media", status=500)


# OCR Extraction endpoints
@admin.get("/api/media/dashboard")
@auth_required("session")
@roles_accepted("Admin", "DA")
def api_media_dashboard():
    """
    Media dashboard with OCR status.
    Query params:
      - page, per_page: pagination
      - ocr_status: pending|processed|failed|cant_read
      - q: search in extracted text
      - bulletin_id: filter by bulletin
      - date_from, date_to: filter by extraction created_at
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    ocr_status = request.args.get("ocr_status")
    search = request.args.get("q")
    bulletin_id = request.args.get("bulletin_id", type=int)
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    query = Media.query.outerjoin(Extraction)

    # Filter by bulletin
    if bulletin_id:
        query = query.filter(Media.bulletin_id == bulletin_id)

    # Filter by OCR status
    if ocr_status == "pending":
        query = query.filter(Extraction.id.is_(None))
    elif ocr_status:
        query = query.filter(Extraction.status == ocr_status)

    # Text search in normalized extraction text
    if search:
        search = normalize_arabic(search)
        query = query.filter(Extraction.search_text.ilike(f"%{search}%"))

    # Date range filter on extraction created_at
    if date_from:
        query = query.filter(Extraction.created_at >= date_from)
    if date_to:
        query = query.filter(Extraction.created_at <= date_to)

    query = query.order_by(desc(Media.id))
    paginated = query.paginate(page=page, per_page=per_page, count=True)

    items = []
    for media in paginated.items:
        item = media.to_dict()
        item["extraction"] = media.extraction.to_dict() if media.extraction else None
        item["ocr_status"] = media.extraction.status if media.extraction else "pending"
        # Add bulletin info for FE
        if media.bulletin:
            item["bulletin"] = {"id": media.bulletin.id, "title": media.bulletin.title}
        else:
            item["bulletin"] = None
        # Add media URLs for thumbnails (FE expects thumbnail_url and url)
        media_url = _media_url(media.media_file)
        item["media_url"] = media_url
        item["thumbnail_url"] = media_url
        item["url"] = media_url
        items.append(item)

    return jsonify(
        {
            "items": items,
            "page": page,
            "perPage": per_page,
            "total": paginated.total,
            "hasMore": paginated.has_next,
        }
    )


@admin.get("/api/ocr/stats")
@auth_required("session")
@roles_accepted("Admin", "DA")
def api_ocr_stats():
    """OCR processing statistics for dashboard header."""
    # Only count media with OCR-eligible file extensions
    ocr_ext = current_app.config.get("OCR_EXT", [])
    ext_filters = [Media.media_file.ilike(f"%.{ext}") for ext in ocr_ext]
    total_media = (
        db.session.query(func.count(Media.id)).filter(db.or_(*ext_filters)).scalar() or 0
        if ext_filters
        else 0
    )

    # Count by extraction status
    status_counts = (
        db.session.query(Extraction.status, func.count(Extraction.id))
        .group_by(Extraction.status)
        .all()
    )
    status_map = {row[0]: row[1] for row in status_counts}

    total_extracted = sum(status_map.values())
    pending = total_media - total_extracted

    return jsonify(
        {
            "total": total_media,
            "pending": pending,
            "processed": status_map.get("processed", 0),
            "cant_read": status_map.get("cant_read", 0),
            "failed": status_map.get("failed", 0),
        }
    )


@admin.get("/api/extraction/<int:extraction_id>")
def api_extraction_get(extraction_id: int):
    """Return full extraction data including text."""
    extraction = Extraction.query.get(extraction_id)
    if not extraction:
        return HTTPResponse.not_found()
    return HTTPResponse.success(data=extraction.to_dict())


@admin.put("/api/extraction/<int:extraction_id>")
@auth_required("session")
@roles_accepted("Admin", "DA")
def api_extraction_update(extraction_id: int):
    """
    Update extraction record (transcribe or mark unreadable).
    Body:
      - action: transcribe|cant_read
      - text: (required for transcribe) corrected text
    """
    extraction = Extraction.query.get(extraction_id)
    if not extraction:
        return HTTPResponse.not_found("Extraction not found")

    data = request.json or {}
    action = data.get("action")

    if action == "transcribe":
        text = data.get("text")
        if not text:
            return HTTPResponse.error("Text required for transcription")
        # Record edit history
        history = list(extraction.history or [])
        history.append(
            {
                "user_id": current_user.id,
                "old_text": extraction.text or "",
                "new_text": text,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        extraction.history = history
        extraction.text = text
        extraction.word_count = len(text.split())
        extraction.status = "processed"
        extraction.manual = True
        extraction.reviewed_by = current_user.id
        extraction.reviewed_at = datetime.utcnow()

    elif action == "cant_read":
        extraction.status = "cant_read"
        extraction.reviewed_by = current_user.id
        extraction.reviewed_at = datetime.utcnow()

    else:
        return HTTPResponse.error("Invalid action. Use: transcribe, cant_read")

    db.session.commit()

    detail_map = {
        "transcribe": "Manual transcription",
        "cant_read": "Marked unreadable",
    }
    Activity.create(
        current_user,
        Activity.ACTION_REVIEW,
        Activity.STATUS_SUCCESS,
        extraction.to_mini(),
        "extraction",
        details=detail_map.get(action),
    )

    return jsonify(extraction.to_dict())


@admin.put("/api/media/<int:id>/orientation")
@auth_required("session")
@roles_accepted("Admin", "DA")
def api_media_orientation(id: int):
    """Set media orientation independently of OCR."""
    media = Media.query.get(id)
    if not media:
        return HTTPResponse.not_found("Media not found")

    if not current_user.can_access(media):
        return HTTPResponse.forbidden("Restricted Access")

    data = request.json or {}
    orientation = data.get("orientation")
    if orientation not in (0, 90, 180, 270):
        return HTTPResponse.error("Invalid orientation. Use: 0, 90, 180, 270")

    media.orientation = orientation
    db.session.commit()

    Activity.create(
        current_user,
        Activity.ACTION_UPDATE,
        Activity.STATUS_SUCCESS,
        media.to_mini(),
        "media",
        details=f"Orientation set to {orientation}",
    )

    return HTTPResponse.success(data={"orientation": orientation})


@admin.post("/api/extraction/<int:extraction_id>/translate")
@auth_required("session")
@roles_accepted("Admin")
def api_extraction_translate(extraction_id: int):
    """Translate extraction text on demand."""
    from enferno.utils.translate_utils import translate_text

    extraction = Extraction.query.get(extraction_id)
    if not extraction:
        return HTTPResponse.not_found("Extraction not found")

    source_text = extraction.text or extraction.original_text
    if not source_text:
        return HTTPResponse.error("No text to translate")

    data = request.json or {}
    target = data.get("target_language", "fr")

    try:
        result = translate_text(
            source_text,
            target_language=target,
            source_language=extraction.language,
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Translation failed for extraction {extraction_id}: {e}")
        return HTTPResponse.error("Translation failed", status=500)


@admin.post("/api/ocr/process/<int:media_id>")
@auth_required("session")
@roles_accepted("Admin")
def api_ocr_process(media_id: int):
    """Run OCR on a single media item (sync)."""
    from enferno.tasks.extraction import process_media_extraction_task

    media = db.session.get(Media, media_id)
    if not media:
        return HTTPResponse.not_found("Media not found")
    if not current_user.can_access(media):
        return HTTPResponse.forbidden("Restricted Access")

    result = process_media_extraction_task(media_id)

    Activity.create(
        current_user,
        Activity.ACTION_CREATE,
        Activity.STATUS_SUCCESS,
        media.to_mini(),
        "extraction",
        details=f"OCR processed (status: {result.get('status', 'unknown')})",
    )

    return jsonify(result)


@admin.post("/api/ocr/bulk")
@auth_required("session")
@roles_accepted("Admin")
def api_ocr_bulk():
    """
    Bulk OCR processing via Celery (async).

    Body:
      - media_ids: list of media IDs to process
      - bulletin_id: process all pending media for a bulletin
      - all: process all pending media
      - limit: max items (default 1000, cap 10000)
    """
    from sqlalchemy import or_, select

    from enferno.tasks import bulk_ocr_process

    data = request.json or {}
    media_ids = data.get("media_ids", [])
    bulletin_id = data.get("bulletin_id")
    process_all = data.get("all", False)
    limit = min(data.get("limit", 1000), 10000)

    # Only queue files with OCR-supported extensions
    ocr_ext = current_app.config.get("OCR_EXT", [])
    ext_filters = [Media.media_file.ilike(f"%.{ext}") for ext in ocr_ext] if ocr_ext else []

    # Build media ID list
    if process_all and not media_ids:
        stmt = select(Media.id).outerjoin(Extraction).where(Extraction.id.is_(None))
        if ext_filters:
            stmt = stmt.where(or_(*ext_filters))
        stmt = stmt.limit(limit)
        media_ids = list(db.session.scalars(stmt))
    elif bulletin_id and not media_ids:
        stmt = (
            select(Media.id)
            .outerjoin(Extraction)
            .where(Media.bulletin_id == bulletin_id)
            .where(Extraction.id.is_(None))
        )
        if ext_filters:
            stmt = stmt.where(or_(*ext_filters))
        stmt = stmt.limit(limit)
        media_ids = list(db.session.scalars(stmt))

    if not media_ids:
        return HTTPResponse.error("No media to process")

    # Track processing items in Redis (auto-expires in 2 hours)
    redis_key = f"ocr_processing:{current_user.id}"
    rds.sadd(redis_key, *media_ids)
    rds.expire(redis_key, 7200)

    task = bulk_ocr_process.delay(media_ids, current_user.id)
    return jsonify(
        {
            "task_id": task.id,
            "queued": len(media_ids),
            "message": f"Queued {len(media_ids)} items. You'll be notified when complete.",
        }
    )


@admin.get("/api/ocr/processing")
@auth_required("session")
@roles_accepted("Admin")
def api_ocr_processing():
    """Get list of media IDs currently being processed by bulk OCR."""
    redis_key = f"ocr_processing:{current_user.id}"
    ids = rds.smembers(redis_key)
    return jsonify([int(id) for id in ids] if ids else [])
