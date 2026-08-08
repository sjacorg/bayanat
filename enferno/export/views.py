from pathlib import Path
from typing import Optional

from flask import request, Response, Blueprint, send_from_directory
from flask.templating import render_template
from flask_security.decorators import auth_required, current_user, roles_required
from enferno.extensions import db
from enferno.admin.constants import Constants
from enferno.admin.models import Activity, Actor
from enferno.admin.models.Notification import Notification
from enferno.export.models import Export, ExportTemplate
from enferno.tasks import generate_export
from enferno.utils.http_response import HTTPResponse
from enferno.utils.logging_utils import get_logger
import enferno.utils.typing as t

export = Blueprint(
    "export",
    __name__,
    static_folder="../static",
    template_folder="../export/templates",
    cli_group=None,
    url_prefix="/export",
)

PER_PAGE = 30

logger = get_logger()


@export.before_request
@auth_required("session")
def export_before_request() -> Optional[Response]:
    """Check user's permissions."""
    # check user's permissions
    if not (current_user.has_role("Admin") or current_user.can_export):
        return HTTPResponse.forbidden("Forbidden")


@export.route("/dashboard/")
@export.get("/dashboard/<int:id>")
def exports_dashboard(id: Optional[t.id] = None) -> str:
    """
    Endpoint to render the exports dashboard.

    Args:
        - id: Optional export id.

    Returns:
        - The html page of the exports dashboard.
    """
    return render_template("export-dashboard.html")


@export.post("/api/bulletin/export")
def export_bulletins() -> Response:
    """
    just creates an export request.

    Returns:
        - success code / failure if something goes wrong.
    """
    # create an export request
    export_request = Export()
    export_request.from_json("bulletin", request.json)
    if export_request.save():
        # Record activity
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            export_request.to_mini(),
            Export.__table__.name,
        )
        # Notify admins
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.NEW_EXPORT,
            "New Export Request",
            f"Export (bulletin) request {export_request.id} has been created by {current_user.username} successfully.",
        )

        return HTTPResponse.created(
            message=f"Export request created successfully, id:  {export_request.id} ",
            data={"item": export_request.to_dict()},
        )
    return HTTPResponse.error("Error creating export request", status=417)


@export.post("/api/actor/export")
def export_actors() -> Response:
    """
    just creates an export request.

    Returns:
        - success code / failure if something goes wrong.
    """
    # create an export request
    export_request = Export()
    export_request.from_json("actor", request.json)
    if export_request.save():
        # Record activity
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            export_request.to_mini(),
            Export.__table__.name,
        )
        # Notify admins
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.NEW_EXPORT,
            "New Export Request",
            f"Export (actor) request {export_request.id} has been created by {current_user.username} successfully.",
        )

        return HTTPResponse.created(
            message=f"Export request created successfully, id:  {export_request.id} ",
            data={"item": export_request.to_dict()},
        )
    return HTTPResponse.error("Error creating export request", status=417)


@export.post("/api/incident/export")
def export_incidents() -> Response:
    """
    just creates an export request.

    Returns:
        - success code / failure if something goes wrong.
    """
    # create an export request
    export_request = Export()
    export_request.from_json("incident", request.json)
    if export_request.save():
        # Record activity
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            export_request.to_mini(),
            Export.__table__.name,
        )
        # Notify admins
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.NEW_EXPORT,
            "New Export Request",
            f"Export (incident) request {export_request.id} has been created by {current_user.username} successfully.",
        )
        return HTTPResponse.created(
            message=f"Export request created successfully, id:  {export_request.id} ",
            data={"item": export_request.to_dict()},
        )
    return HTTPResponse.error("Error creating export request", status=417)


@export.get("/api/export/<int:id>")
def api_export_get(id: t.id) -> Response:
    """
    Endpoint to get a single export.

    Args:
        - id: The id of the export.

    Returns:
        - The export in json format / success or error.
    """
    export = db.session.get(Export, id)

    if export is None:
        return HTTPResponse.not_found("Export not found")
    # Same ownership guard as the list/download routes (BAY-01-015).
    if not current_user.has_role("Admin") and current_user.id != export.requester_id:
        return HTTPResponse.forbidden("Forbidden")
    return HTTPResponse.success(data=export.to_dict(), message="Export retrieved successfully")


@export.post("/api/exports/")
def api_exports() -> Response:
    """
    API endpoint to feed export request items in josn format - supports paging
    and generated based on user role.

    Returns:
        - successful json feed or error
    """
    page = request.json.get("page", 1)
    per_page = request.json.get("per_page", PER_PAGE)

    if current_user.has_role("Admin"):
        result = Export.query.order_by(-Export.id).paginate(
            page=page, per_page=per_page, count=True
        )

    else:
        # if a normal authenticated user, get own export requests only
        result = (
            Export.query.filter(Export.requester_id == current_user.id)
            .order_by(-Export.id)
            .paginate(page=page, per_page=per_page, count=True)
        )

    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": PER_PAGE,
        "total": result.total,
    }

    return HTTPResponse.success(data=response)


@export.put("/api/exports/status")
@roles_required("Admin")
def change_export_status() -> Response:
    """
    endpoint to approve or reject an export request.

    Returns:
        - success / error based on the operation outcome.
    """
    action = request.json.get("action")
    if not action or action not in ["approve", "reject"]:
        return HTTPResponse.error("Please check request action", status=417)
    export_id = request.json.get("exportId")

    if not export_id:
        return HTTPResponse.error("Invalid export request id", status=417)
    export_request = db.session.get(Export, export_id)

    if not export_request:
        return HTTPResponse.not_found("Export request does not exist")

    if action == "approve":
        export_request = export_request.approve()
        if export_request.save():
            # record activity
            Activity.create(
                current_user,
                Activity.ACTION_APPROVE_EXPORT,
                Activity.STATUS_SUCCESS,
                export_request.to_mini(),
                Export.__table__.name,
            )
            # implement celery task chaining
            res = generate_export(export_id)
            # not sure if there is a scenario where the result has no uuid
            # store export background task id, to be used for fetching progress
            export_request.uuid = res.id
            export_request.save()

            # Notify admins
            Notification.send_admin_notification_for_event(
                Constants.NotificationEvent.EXPORT_APPROVED,
                "Export Request Approved",
                f"Export request {export_request.id} has been approved by {current_user.username} successfully.",
            )

            return HTTPResponse.success(
                message="Export request approval will be processed shortly."
            )

    if action == "reject":
        export_request = export_request.reject()
        if export_request.save():
            # record activity
            Activity.create(
                current_user,
                Activity.ACTION_REJECT_EXPORT,
                Activity.STATUS_SUCCESS,
                export_request.to_mini(),
                Export.__table__.name,
            )

            return HTTPResponse.success(message="Export request rejected.")


@export.put("/api/exports/expiry")
@roles_required("Admin")
def update_expiry() -> Response:
    """
    endpoint to set expiry date of an approved export.

    Returns:
        - success / error based on the operation outcome
    """
    export_id = request.json.get("exportId")
    new_date = request.json.get("expiry")
    export_request = db.session.get(Export, export_id)

    if export_request.expired:
        return HTTPResponse.forbidden("Forbidden")
    else:
        try:
            export_request.set_expiry(new_date)
        except Exception:
            return HTTPResponse.error("Invalid expiry date", status=417)

        if export_request.save():
            return HTTPResponse.success(message=f"Updated Export #{export_id}")
        else:
            return HTTPResponse.error("Save failed", status=417)


@export.get("/api/exports/download")
def download_export_file() -> Response:
    """
    Endpoint to Download an export file. Expects the export id as a query parameter.

    Returns:
        - The file to download or access denied response if the export has expired.
    """
    uid = request.args.get("exportId")

    try:
        export_id = Export.decrypt_unique_id(uid)
        export = db.session.get(Export, export_id)

        # check permissions for download
        # either admin or user is requester
        if not current_user.has_role("Admin"):
            if current_user.id != export.requester.id:
                return HTTPResponse.forbidden("Forbidden")

        if not export_id or not export:
            return HTTPResponse.not_found("Export not found")
        # check expiry
        if not export.expired:
            # Record activity
            Activity.create(
                current_user,
                Activity.ACTION_DOWNLOAD,
                Activity.STATUS_SUCCESS,
                export.to_mini(),
                Export.__table__.name,
            )
            return send_from_directory(
                f"{Path(*Export.export_dir.parts[1:])}", f"{export.file_id}.zip"
            )
        else:
            return HTTPResponse.error("Request expired", status=410)

    except Exception as e:
        logger.error(f"Unable to decrypt export request uid {e}")
        return HTTPResponse.not_found("Unable to decrypt export request uid")


# ---------------------------------------------------------------------------
# Dossier export templates (smart blocks)
# ---------------------------------------------------------------------------


def _get_template(id: t.id) -> Optional[ExportTemplate]:
    template = db.session.get(ExportTemplate, id)
    if template is None or template.deleted:
        return None
    return template


@export.route("/templates/")
@roles_required("Admin")
def templates_editor() -> str:
    """Render the dossier template editor page."""
    return render_template("export-templates.html")


@export.get("/api/templates/meta")
@roles_required("Admin")
def api_templates_meta() -> Response:
    """Editor metadata: field whitelist, relation types, and column choices."""
    from enferno.admin.models import AtoaInfo
    from enferno.admin.models.DynamicField import DynamicField
    from enferno.export.blocks import (
        ACTOR_FIELDS,
        EVENT_COLUMNS,
        RELATED_ACTOR_COLUMNS,
        RELATED_BULLETIN_COLUMNS,
    )

    fields = [
        {"key": key, "label": spec["label"], "label_ar": spec["label_ar"]}
        for key, spec in ACTOR_FIELDS.items()
    ]
    fields += [
        {"key": f"dyn:{field.name}", "label": field.title, "label_ar": field.title}
        for field in DynamicField.query.filter_by(entity_type="actor", active=True, core=False)
    ]
    relation_types = [
        {"id": info.id, "title": info.title_tr or info.title}
        for info in AtoaInfo.query.filter(AtoaInfo.deleted == False).order_by(
            AtoaInfo.id
        )  # noqa: E712
    ]
    columns = {
        "family_members_table": [
            {"key": k, "label": v["label"]} for k, v in RELATED_ACTOR_COLUMNS.items()
        ],
        "related_items_table": [
            {"key": k, "label": v["label"]} for k, v in RELATED_BULLETIN_COLUMNS.items()
        ],
        "events_timeline": [{"key": k, "label": v["label"]} for k, v in EVENT_COLUMNS.items()],
    }
    return HTTPResponse.success(
        data={"fields": fields, "relation_types": relation_types, "columns": columns}
    )


@export.post("/api/templates/")
@roles_required("Admin")
def api_templates() -> Response:
    """Paged list of dossier templates."""
    page = request.json.get("page", 1)
    per_page = request.json.get("per_page", PER_PAGE)
    result = (
        ExportTemplate.query.filter(ExportTemplate.deleted == False)  # noqa: E712
        .order_by(-ExportTemplate.id)
        .paginate(page=page, per_page=per_page, count=True)
    )
    return HTTPResponse.success(
        data={
            "items": [item.to_dict() for item in result.items],
            "perPage": per_page,
            "total": result.total,
        }
    )


@export.post("/api/template/")
@roles_required("Admin")
def api_template_create() -> Response:
    template = ExportTemplate()
    try:
        template.from_json(request.json.get("item") or {})
    except ValueError as e:
        return HTTPResponse.error(str(e), status=417)
    template.user = current_user
    if template.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            template.to_mini(),
            ExportTemplate.__table__.name,
        )
        return HTTPResponse.created(
            message=f"Template #{template.id} created", data={"item": template.to_dict()}
        )
    return HTTPResponse.error("Error creating template", status=417)


@export.put("/api/template/<int:id>")
@roles_required("Admin")
def api_template_update(id: t.id) -> Response:
    template = _get_template(id)
    if template is None:
        return HTTPResponse.not_found("Template not found")
    try:
        template.from_json(request.json.get("item") or {})
    except ValueError as e:
        return HTTPResponse.error(str(e), status=417)
    if template.save():
        Activity.create(
            current_user,
            Activity.ACTION_UPDATE,
            Activity.STATUS_SUCCESS,
            template.to_mini(),
            ExportTemplate.__table__.name,
        )
        return HTTPResponse.success(
            message=f"Template #{template.id} updated", data={"item": template.to_dict()}
        )
    return HTTPResponse.error("Error saving template", status=417)


@export.put("/api/template/<int:id>/publish")
@roles_required("Admin")
def api_template_publish(id: t.id) -> Response:
    template = _get_template(id)
    if template is None:
        return HTTPResponse.not_found("Template not found")
    publish = bool(request.json.get("published", True))
    template.publish() if publish else template.unpublish()
    if template.save():
        Activity.create(
            current_user,
            Activity.ACTION_UPDATE,
            Activity.STATUS_SUCCESS,
            template.to_mini(),
            ExportTemplate.__table__.name,
        )
        return HTTPResponse.success(
            message=f"Template #{template.id} {'published' if publish else 'unpublished'}",
            data={"item": template.to_dict()},
        )
    return HTTPResponse.error("Error saving template", status=417)


@export.delete("/api/template/<int:id>")
@roles_required("Admin")
def api_template_delete(id: t.id) -> Response:
    template = _get_template(id)
    if template is None:
        return HTTPResponse.not_found("Template not found")
    template.deleted = True
    if template.save():
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            template.to_mini(),
            ExportTemplate.__table__.name,
        )
        return HTTPResponse.success(message=f"Template #{template.id} deleted")
    return HTTPResponse.error("Error deleting template", status=417)


def _render_dossier(
    template: ExportTemplate, actor: Actor, show_toolbar: bool = True, pdf_mode: bool = False
) -> str:
    from flask import current_app
    from enferno.export.blocks import build_dossier

    context = build_dossier(template, actor, current_user)
    # Browsers load the logo over HTTP; WeasyPrint reads it straight from disk
    # (the hardened fetcher allows file:// under the app root only).
    logo_src = (
        f"file://{current_app.root_path}/static/img/sjac-logo.png"
        if pdf_mode
        else "/static/img/sjac-logo.png"
    )
    media_base = f"file://{current_app.root_path}/media/" if pdf_mode else "/admin/api/serve/media/"
    return render_template(
        "dossier.html",
        show_toolbar=show_toolbar,
        pdf_mode=pdf_mode,
        logo_src=logo_src,
        media_base=media_base,
        **context,
    )


@export.get("/dossier/<int:template_id>/<int:actor_id>")
def dossier(template_id: t.id, actor_id: t.id) -> Response:
    """Render a dossier from a saved template: HTML with a print button, or
    PDF via WeasyPrint with ?format=pdf (both use the same HTML)."""
    template = _get_template(template_id)
    if template is None:
        return HTTPResponse.not_found("Template not found")
    if not template.published and not current_user.has_role("Admin"):
        return HTTPResponse.forbidden("Template is not published")
    actor = db.session.get(Actor, actor_id)
    if actor is None or actor.deleted:
        return HTTPResponse.not_found("Entity not found")
    if not current_user.can_access(actor):
        return HTTPResponse.forbidden("Forbidden")

    as_pdf = request.args.get("format") == "pdf"
    html = _render_dossier(template, actor, show_toolbar=not as_pdf, pdf_mode=as_pdf)
    Activity.create(
        current_user,
        Activity.ACTION_DOWNLOAD if as_pdf else Activity.ACTION_VIEW,
        Activity.STATUS_SUCCESS,
        {"template_id": template.id, "actor_id": actor.id, "class": "dossier"},
        ExportTemplate.__table__.name,
    )
    if not as_pdf:
        return Response(html, mimetype="text/html")

    from flask import current_app
    from weasyprint import CSS, HTML
    from enferno.utils.pdf_utils import _safe_url_fetcher

    stylesheet = CSS(filename=f"{current_app.root_path}/static/css/dossier.css")
    # WeasyPrint-only: running document title in the footer (string() is not
    # supported by browsers, so it stays out of the shared stylesheet).
    running_title = CSS(
        string="@page { @bottom-left { content: string(doctitle); "
        'font-family: "IBM Plex Sans Arabic", sans-serif; font-size: 8.5px; color: #6f6a60; } }'
    )
    pdf = HTML(string=html, url_fetcher=_safe_url_fetcher).write_pdf(
        stylesheets=[stylesheet, running_title]
    )
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=dossier-{template.id}-{actor.id}.pdf"
        },
    )
