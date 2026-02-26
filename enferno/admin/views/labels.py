from __future__ import annotations

from flask import Response, request
from flask.templating import render_template
from flask_security.decorators import current_user, roles_accepted, roles_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from enferno.admin.constants import Constants
from enferno.admin.models import Label, Activity
from enferno.admin.models.Notification import Notification
from enferno.admin.validation.models import LabelRequestModel
from enferno.utils.http_response import HTTPResponse
from enferno.utils.validation_utils import validate_with
import enferno.utils.typing as t
from . import admin, PER_PAGE


# Labels routes
@admin.route("/labels/")
@roles_accepted("Admin", "Mod")
def labels() -> str:
    """
    Endpoint to render the labels backend page.

    Returns:
        - html template of the labels backend page.
    """
    return render_template("admin/labels.html")


@admin.route("/api/labels/")
def api_labels() -> Response:
    """
    API endpoint feed and filter labels with paging

    Returns:
        - json response of label objects.
    """
    query = []
    q = request.args.get("q", None)

    if q:
        words = q.split(" ")
        query.extend([Label.title.ilike(f"%{word}%") for word in words])

    typ = request.args.get("typ", None)
    if typ and typ in ["for_bulletin", "for_actor", "for_incident", "for_offline"]:
        query.append(getattr(Label, typ) == True)
    fltr = request.args.get("fltr", None)

    if fltr == "verified":
        query.append(Label.verified == True)
    elif fltr == "all":
        pass
    else:
        query.append(or_(Label.verified == False, Label.verified.is_(None)))

    # Exclude specific label IDs (useful for parent picker)
    exclude = request.args.get("exclude", None)
    if exclude:
        try:
            exclude_ids = [int(x) for x in exclude.split(",")]
            query.append(~Label.id.in_(exclude_ids))
        except ValueError:
            pass

    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)
    mode = request.args.get("mode", "1")

    # Eager load parent when mode=2 to avoid N+1 on _build_path()
    base_query = Label.query
    if mode == "2":
        base_query = base_query.options(joinedload(Label.parent))

    if q:
        result = base_query.filter(*query).all()
        labels = [label for label in result]
        ids = []
        children = Label.get_children(labels)
        for label in labels + children:
            ids.append(label.id)
        ids = list(set(ids))
        result = base_query.filter(Label.id.in_(ids)).paginate(
            page=page, per_page=per_page, count=True
        )
    else:
        result = base_query.filter(*query).paginate(page=page, per_page=per_page, count=True)

    response = {
        "items": [item.to_dict(mode) for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.route("/api/labels/tree")
@roles_accepted("Admin", "Mod")
def api_labels_tree() -> Response:
    """Return labels as nested tree structure for admin tree view."""
    verified_param = request.args.get("verified", None)
    verified = None
    if verified_param == "true":
        verified = True
    elif verified_param == "false":
        verified = False
    tree = Label.build_tree(verified=verified)
    return HTTPResponse.success(data={"items": tree})


@admin.post("/api/label/")
@roles_accepted("Admin", "Mod")
@validate_with(LabelRequestModel)
def api_label_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create a label.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    label = Label()
    created = label.from_json(validated_data["item"])
    if created.save():
        Activity.create(
            current_user, Activity.ACTION_CREATE, Activity.STATUS_SUCCESS, label.to_mini(), "label"
        )
        mode = request.args.get("mode", "1")
        return HTTPResponse.created(
            message=f"Created Label #{label.id}",
            data={"item": label.to_dict(mode=mode)},
        )
    else:
        return HTTPResponse.error("Save Failed", status=500)


@admin.put("/api/label/<int:id>")
@roles_accepted("Admin", "Mod")
@validate_with(LabelRequestModel)
def api_label_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update a label.

    Args:
        - id: id of the label.
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.

    """
    label = Label.query.get(id)
    if label is not None:
        label = label.from_json(validated_data["item"])
        label.save()
        Activity.create(
            current_user, Activity.ACTION_UPDATE, Activity.STATUS_SUCCESS, label.to_mini(), "label"
        )
        return HTTPResponse.success(message=f"Saved Label #{label.id}", status=200)
    else:
        return HTTPResponse.not_found("Label not found")


@admin.delete("/api/label/<int:id>")
@roles_required("Admin")
def api_label_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete a label.

    Args:
        - id: id of the label.

    Returns:
        - success/error string based on the operation result.
    """
    label = Label.query.get(id)
    if label is None:
        return HTTPResponse.not_found("Label not found")

    if label.delete():
        Activity.create(
            current_user, Activity.ACTION_DELETE, Activity.STATUS_SUCCESS, label.to_mini(), "label"
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "Label Deleted",
            f"Label {label.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"Deleted Label #{label.id}", status=200)
    else:
        return HTTPResponse.error("Error deleting Label", status=500)


@admin.post("/api/label/import/")
@roles_required("Admin")
def api_label_import() -> str:
    """
    Endpoint to import labels via CSV

    Returns:
        - success/error string based on the operation result.
    """
    if "csv" in request.files:
        Label.import_csv(request.files.get("csv"))
        return HTTPResponse.success(message="Success")
    else:
        return HTTPResponse.error("Error", status=400)
