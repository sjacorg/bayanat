from pathlib import Path

import os
from typing import Optional

import shortuuid
from flask import jsonify, request, Response, Blueprint, current_app, json
from flask.templating import render_template
from flask_security.decorators import auth_required, current_user, roles_accepted, roles_required
from sqlalchemy.orm.attributes import flag_modified
from unidecode import unidecode
from werkzeug.utils import safe_join

from enferno.admin.constants import Constants
from enferno.admin.models import Media
from enferno.data_import.models import DataImport, Mapping
from enferno.data_import.utils.sheet_import import SheetImport
from enferno.tasks import process_row, process_files
from enferno.utils.data_helpers import get_file_hash
from enferno.utils.http_response import HTTPResponse
from enferno.utils.logging_utils import get_logger
import enferno.utils.typing as t

imports = Blueprint(
    "imports",
    __name__,
    static_folder="../static",
    template_folder="../data_import/templates",
    cli_group=None,
    url_prefix="/import",
)

PER_PAGE = 50

logger = get_logger()


@imports.before_request
@auth_required("session")
def data_import_before_request() -> Optional[Response]:
    """Function to check if user is authenticated before accessing the data import routes."""
    # only admins allowed to interact with these routes
    if not (current_user.has_role("Admin")):
        return HTTPResponse.FORBIDDEN


@imports.route("/log/")
@imports.get("/log/<int:id>")
def data_import_dashboard(id: Optional[t.id] = None) -> str:
    """
    Endpoint to render the log dashboard.

    Args:
        - id: id of the log.

    Returns:
        - html page of the log dashboard.
    """
    return render_template("import-log.html")


@imports.get("/api/imports/<int:id>")
def api_import_get(id: t.id) -> Response:
    """
    Endpoint to get a single log item.

    Args:
        - id: id of the log.

    Returns:
        - log in json format / success or error.
    """
    data_import = DataImport.query.get(id)

    if data_import is None:
        return HTTPResponse.NOT_FOUND
    else:
        return json.dumps(data_import.to_dict()), 200


@imports.post("/api/imports/")
def api_imports() -> Response:
    """
    API endpoint to feed log request items in JSON format with paging.

    Returns:
        - successful json feed or error.
    """
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)
    q = request.json.get("q", None)

    if q and (batch_id := q.get("batch_id")):
        result = (
            DataImport.query.filter(DataImport.batch_id == batch_id)
            .order_by(-DataImport.id)
            .paginate(page=page, per_page=per_page, count=True)
        )
    else:
        result = DataImport.query.order_by(-DataImport.id).paginate(
            page=page, per_page=per_page, count=True
        )

    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": PER_PAGE,
        "total": result.total,
    }

    return Response(json.dumps(response), content_type="application/json")


# Data Import Backend API
@imports.route("/media/")
@roles_required("Admin")
def media_import() -> Response:
    """
    Endpoint to render the etl backend.

    Returns:
        - html page of the etl backend.
    """
    if not current_app.config["ETL_TOOL"]:
        return HTTPResponse.NOT_FOUND
    return render_template("media-import.html")


@imports.post("/media/path/")
@roles_required("Admin")
def path_process() -> Response:
    """API endpoint to process a path for media import."""
    # Check if path import is enabled and allowed path is set
    if (
        not current_app.config.get("ETL_PATH_IMPORT")
        or current_app.config.get("ETL_ALLOWED_PATH") is None
    ):
        return HTTPResponse.FORBIDDEN

    allowed_path = Path(current_app.config.get("ETL_ALLOWED_PATH"))

    if not allowed_path.is_dir():
        return "Allowed import path is not configured correctly", 417

    sub_path = request.json.get("path")
    if sub_path == "":
        import_path = allowed_path
    else:
        safe_path = safe_join(allowed_path, sub_path)
        if safe_path:
            import_path = Path(safe_path)
        else:
            return HTTPResponse.FORBIDDEN

    if not import_path.is_dir():
        return "Invalid path specified", 417

    recursive = request.json.get("recursive", False)
    if recursive:
        items = import_path.rglob("*")
    else:
        items = import_path.glob("*")

    # return relative path
    files = [str(file.relative_to(allowed_path)) for file in items if file.is_file()]

    output = [{"filename": os.path.basename(file), "path": file} for file in files]

    return json.dumps(output), 200


@imports.post("/media/process")
@roles_required("Admin")
def etl_process() -> Response:
    """
    process a single file.

    Returns:
        - response contains the processing result
    """

    files = request.json.pop("files")
    meta = request.json
    batch_id = shortuuid.uuid()[:9]

    process_files.delay(files=files, meta=meta, user_id=current_user.id, batch_id=batch_id)

    return batch_id, 200


# CSV Tool
@imports.route("/sheets/")
@roles_required("Admin")
def csv_dashboard() -> Response:
    """
    Endpoint to render the csv backend.

    Returns:
        - html page of the csv backend.
    """
    if not current_app.config.get("SHEET_IMPORT"):
        return HTTPResponse.NOT_FOUND
    return render_template("sheets-import.html")


@imports.post("/api/csv/upload")
@roles_required("Admin")
def api_local_csv_upload() -> Response:
    """API endpoint to upload a file for csv import."""
    import_dir = Path(current_app.config.get("IMPORT_DIR"))
    # file pond sends multiple requests for multiple files (handle each request as a separate file )
    try:
        f = request.files.get("file")
        # validate immediately
        allowed_extensions = current_app.config["SHEETS_ALLOWED_EXTENSIONS"]
        if not Media.validate_file_extension(f.filename, allowed_extensions):
            return "This file type is not allowed", 415
        # final file
        decoded = unidecode(f.filename)
        filename = Media.generate_file_name(decoded)
        filepath = (import_dir / filename).as_posix()
        f.save(filepath)

        # get md5 hash
        etag = get_file_hash(filepath)

        response = {"etag": etag, "filename": filename, "original_filename": f.filename}
        return Response(json.dumps(response), content_type="application/json"), 200
    except Exception as e:
        logger.error(e, exc_info=True)
        return f"Request Failed", 417


@imports.delete("/api/csv/upload/")
@roles_required("Admin")
def api_local_csv_delete() -> str:
    """
    API endpoint for removing files

    Returns:
        - success if file is removed / keeping uploaded sheets for now, used as a handler for http calls from filepond for now.
    """
    return ""


@imports.post("/api/csv/analyze")
@roles_required("Admin")
def api_csv_analyze() -> Response:
    """API endpoint to analyze a csv file."""
    # locate file
    filename = request.json.get("file").get("filename")
    import_dir = Path(current_app.config.get("IMPORT_DIR"))

    filepath = (import_dir / filename).as_posix()
    result = SheetImport.parse_csv(filepath)

    if result:
        return json.dumps(result)
    else:
        return "Problem parsing sheet file", 417


# Excel sheet selector
@imports.post("/api/xls/sheets")
@roles_required("Admin")
def api_xls_sheet() -> Response:
    """API endpoint to get sheets from an excel file."""
    filename = request.json.get("file").get("filename")
    import_dir = Path(current_app.config.get("IMPORT_DIR"))

    filepath = (import_dir / filename).as_posix()
    sheets = SheetImport.get_sheets(filepath)

    return json.dumps(sheets)


@imports.post("/api/xls/analyze")
@roles_required("Admin")
def api_xls_analyze() -> Response:
    """API endpoint to analyze an excel file."""
    # locate file
    filename = request.json.get("file").get("filename")
    import_dir = Path(current_app.config.get("IMPORT_DIR"))

    filepath = (import_dir / filename).as_posix()
    sheet = request.json.get("sheet")

    result = SheetImport.parse_excel(filepath, sheet)

    if result:
        return Response(json.dumps(result, sort_keys=False), content_type="application/json"), 200
    else:
        return "Problem parsing sheet file", 417


# Saved Searches
@imports.route("/api/mappings/")
def api_mappings() -> Response:
    """
    Endpoint to get sheet mappings.

    Returns:
        - successful json feed of mappings or error.
    """
    mappings = Mapping.query.all()
    return json.dumps([map.to_dict() for map in mappings]), 200


@imports.post("/api/mapping/")
@roles_accepted("Admin")
def api_mapping_create() -> Response:
    """
    API Endpoint save a mapping object.

    Returns:
        - success if save is successful, error otherwise.
    """
    d = request.json.get("data", None)

    name = request.json.get("name", None)
    if d and name:
        map = Mapping()
        map.name = name
        map.data = d
        map.user_id = current_user.id
        # Important : flag json field to enable correct update
        flag_modified(map, "data")

        if map.save():
            return {"message": f"Mapping #{map.id} created successfully", "id": map.id}, 200
        else:
            return "Error creating Mapping", 417
    else:
        return "Update request missing parameters data", 417


@imports.put("/api/mapping/<int:id>")
@roles_accepted("Admin")
def api_mapping_update(id: t.id) -> Response:
    """
    API Endpoint update a mapping object.

    Args:
        - id: id of the mapping object to update.

    Returns:
        - success if save is successful, error otherwise.
    """
    map = Mapping.query.get(id)
    if map:
        data = request.json.get("data")
        m = data.get("map", None)
        name = request.json.get("name", None)
        if m and name:
            map.name = name
            map.data = data
            map.user_id = current_user.id
            if map.save():
                return {"message": f"Mapping #{map.id} updated successfully", "id": map.id}, 200
            else:
                return "Error updating Mapping", 417
        else:
            return "Update request missing parameters data", 417

    else:
        return HTTPResponse.NOT_FOUND


@imports.post("/api/process-sheet")
@roles_accepted("Admin")
def api_process_sheet() -> Response:
    """
    API Endpoint invoke sheet import into target model via a CSV mapping.

    Returns:
        - success if save is successful, error otherwise.
    """
    files = request.json.get("files")
    import_dir = Path(current_app.config.get("IMPORT_DIR"))
    map = request.json.get("map")
    vmap = request.json.get("vmap")
    sheet = request.json.get("sheet")
    lang = request.json.get("lang", "en")
    actor_config = request.json.get("actorConfig")
    roles = request.json.get("roles")

    batch_id = shortuuid.uuid()[:9]

    for filename in files:
        filepath = safe_join(import_dir, filename)
        etag = get_file_hash(filepath)

        df = SheetImport.sheet_to_df(filepath, sheet)
        for row_id, row in df.iterrows():
            data_import = DataImport(
                user_id=current_user.id,
                table="actor",
                file=filename,
                file_hash=etag,
                batch_id=batch_id,
                data=row.to_json(orient="index"),
                log="",
            )

            data_import.file_format = "xls" if sheet else "csv"

            string = f"Added row {row_id} from file {filename}"
            if sheet:
                string += f" sheet {sheet}"
            string += f" to import queue."
            data_import.add_to_log(string)

            process_row.delay(
                filepath,
                sheet,
                row_id,
                data_import.id,
                map,
                batch_id,
                vmap,
                actor_config,
                lang,
                roles,
            )

    return batch_id, 200


@imports.get("/api/whisper/models/")
@roles_required("Admin")
def api_whisper_models() -> Response:
    """Returns the list of whisper models."""
    return jsonify({"models": Constants.WHISPER_MODEL_OPTS})


@imports.get("/api/whisper/languages/")
@roles_required("Admin")
def api_whisper_languages() -> Response:
    """Returns the list of whisper languages."""
    from whisper.tokenizer import TO_LANGUAGE_CODE

    return jsonify({"languages": TO_LANGUAGE_CODE})
