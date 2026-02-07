from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta

import boto3
from botocore.config import Config as BotoConfig
from flask import Response, request, current_app, send_from_directory, abort
from flask_security.decorators import current_user, roles_accepted
from werkzeug.utils import safe_join, secure_filename

from enferno.admin.models import Media, Activity
from enferno.utils.data_helpers import get_file_hash
from enferno.utils.http_response import HTTPResponse
from enferno.utils.logging_utils import get_logger
from enferno.utils.validation_utils import validate_with
from enferno.admin.validation.models import MediaRequestModel
import enferno.utils.typing as t
from . import admin

logger = get_logger()

GRACE_PERIOD = timedelta(hours=2)
S3_URL_EXPIRY = 3600


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
