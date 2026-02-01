from __future__ import annotations

from flask import Response, request, json
from flask.templating import render_template
from flask_security.decorators import current_user, roles_accepted, roles_required
from sqlalchemy import select, func

from enferno.admin.models import (
    Activity,
    Query,
    AtobInfo,
    BtobInfo,
    AtoaInfo,
    ItobInfo,
    ItoaInfo,
    ItoiInfo,
    WorkflowStatus,
)
from enferno.admin.validation.models import ActivityQueryRequestModel, GraphVisualizeRequestModel
from enferno.extensions import rds, db
from enferno.tasks import (
    bulk_update_bulletins,
    bulk_update_actors,
    bulk_update_incidents,
    generate_graph,
)
from enferno.utils.graph_utils import GraphUtils
from enferno.utils.http_response import HTTPResponse
from enferno.utils.search_utils import SearchUtils
from enferno.utils.validation_utils import validate_with
import enferno.utils.typing as t
from . import admin, PER_PAGE


# Activity routes
@admin.route("/activity/")
@roles_required("Admin")
def activity() -> str:
    """
    Endpoint to render activity backend page.

    Returns:
        - html page of the activity backend.
    """
    atobInfo = [item.to_dict() for item in AtobInfo.query.all()]
    btobInfo = [item.to_dict() for item in BtobInfo.query.all()]
    atoaInfo = [item.to_dict() for item in AtoaInfo.query.all()]
    itobInfo = [item.to_dict() for item in ItobInfo.query.all()]
    itoaInfo = [item.to_dict() for item in ItoaInfo.query.all()]
    itoiInfo = [item.to_dict() for item in ItoiInfo.query.all()]
    statuses = [item.to_dict() for item in WorkflowStatus.query.all()]

    return render_template(
        "admin/activity.html",
        actions_types=Activity.get_action_values(),
        atoaInfo=atoaInfo,
        itoaInfo=itoaInfo,
        itoiInfo=itoiInfo,
        atobInfo=atobInfo,
        btobInfo=btobInfo,
        itobInfo=itobInfo,
        statuses=statuses,
    )


@admin.route("/api/activities/", methods=["POST", "GET"])
@roles_required("Admin")
@validate_with(ActivityQueryRequestModel)
def api_activities(validated_data: dict) -> Response:
    """Returns activities in JSON format, allows search and paging."""
    q = validated_data.get("q", {})
    su = SearchUtils(q, cls="activity")
    query = su.get_query()

    options = validated_data.get("options")
    page = options.get("page", 1)
    per_page = options.get("itemsPerPage", PER_PAGE)

    result = (
        Activity.query.filter(*query)
        .order_by(-Activity.id)
        .paginate(page=page, per_page=per_page, count=True)
    )

    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }

    return HTTPResponse.success(data=response)


@admin.route("/api/bulk/status/")
@roles_accepted("Admin", "Mod")
def bulk_status() -> Response:
    """Endpoint to get status update about background bulk operations."""
    uid = current_user.id
    cursor, jobs = rds.scan(0, f"user{uid}:*", 1000)
    tasks = []
    for key in jobs:
        result = {}
        id = key.decode("utf-8").split(":")[-1]
        type = request.args.get("type")
        status = None
        if type == "bulletin":
            status = bulk_update_bulletins.AsyncResult(id).status
        elif type == "actor":
            status = bulk_update_incidents.AsyncResult(id).status
        elif type == "incident":
            status = bulk_update_actors.AsyncResult(id).status
        else:
            return HTTPResponse.error("Invalid type")

        # handle job failure
        if status == "FAILURE":
            rds.delete(key)
        if status != "SUCCESS":
            result["id"] = id
            result["status"] = status
            tasks.append(result)

        else:
            rds.delete(key)
    return HTTPResponse.success(data=tasks)


# Saved Searches
@admin.route("/api/queries/")
def api_queries() -> Response:
    """
    Endpoint to get user saved searches.

    Returns:
        - successful json feed of saved searches or error.
    """
    user_id = current_user.id
    query_type = request.args.get("type")
    if query_type not in Query.TYPES:
        return HTTPResponse.error("Invalid query type")
    queries = Query.query.filter(Query.user_id == user_id, Query.query_type == query_type)
    return HTTPResponse.success(data=[query.to_dict() for query in queries])


@admin.get("/api/query/<string:name>/exists")
def api_query_check_name_exists(
    name: str,
) -> Response:
    """
    API Endpoint check if a query with that provided name exists.
    Queries are tied to the current (request) user.

    Args:
        - name: name of the query to check.

    Returns:
        - success/error string based on the operation result.
    """
    if Query.query.filter_by(name=name, user_id=current_user.id).first():
        return HTTPResponse.error("Query name already exists", status=409)

    return HTTPResponse.success(message="Query name is available")


@admin.post("/api/query/")
def api_query_create() -> Response:
    """
    API Endpoint save a query search object (advanced search.)

    Returns:
        - success/error string based on the operation result.
    """
    q = request.json.get("q", None)
    name = request.json.get("name", None)
    query_type = request.json.get("type")
    # current saved searches types
    if query_type not in Query.TYPES:
        return HTTPResponse.error("Invalid Request")
    if q and name:
        query = Query()
        query.name = name
        query.data = q
        query.query_type = query_type
        query.user_id = current_user.id
        query.save()
        return HTTPResponse.created(
            message="Query successfully saved", data={"item": query.to_dict()}
        )
    else:
        return HTTPResponse.error("Error parsing query data", status=400)


@admin.put("/api/query/<int:id>")
def api_query_update(
    id: t.id,
) -> Response:
    """
    API Endpoint update a query search object (advanced search).
    Updated searches are tied to the current (request) user.

    Args:
        - id: id of the query to update.

    Returns:
        - success/error string based on the operation result.
    """
    if not (q := request.json.get("q")):
        return HTTPResponse.error("q parameter not provided", status=400)

    query = Query.query.get(id)

    if not query:
        return HTTPResponse.not_found("Query not found")

    if query.user_id != current_user.id:
        return HTTPResponse.forbidden("Restricted Access")

    query.data = q
    if query.save():
        return HTTPResponse.success(message=f"Query {query.name} updated")

    return HTTPResponse.error("Query update failed", status=409)


@admin.delete("/api/query/<int:id>")
def api_query_delete(
    id: t.id,
) -> Response:
    """
    API Endpoint delete a query search object (advanced search).
    Deleted searches are tied to the current (request) user.

    Args:
        - id: id of the query to delete.

    Returns:
        - success/error string based on the operation result.
    """
    query = Query.query.get(id)

    if not query:
        return HTTPResponse.not_found("Query not found")

    if query.user_id != current_user.id:
        return HTTPResponse.forbidden("Restricted Access")

    if query.delete():
        return HTTPResponse.success(message=f"Query {query.name} deleted")

    return HTTPResponse.error("Query delete failed", status=409)


@admin.get("/api/graph/json")
def graph_json() -> Optional[str]:
    """
    API Endpoint to return graph data in json format.

    Returns:
        - graph data in json format.
    """
    id = request.args.get("id")
    entity_type = request.args.get("type")
    expanded = request.args.get("expanded")
    graph_utils = GraphUtils(current_user)
    if expanded == "false":
        return HTTPResponse.success(data=json.loads(graph_utils.get_graph_json(entity_type, id)))
    else:
        return HTTPResponse.success(data=json.loads(graph_utils.expanded_graph(entity_type, id)))


@admin.post("/api/graph/visualize")
@validate_with(GraphVisualizeRequestModel)
def graph_visualize(validated_data: dict) -> Response:
    """
    Endpoint to visualize a graph.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - task_id of the graph visualization task.
    """
    user_id = current_user.id
    # Get the type from URL query parameter
    graph_type = request.args.get("type")
    q = validated_data.get("q", None)

    if not q:
        return HTTPResponse.error("No query provided")

    # Check if the type is valid
    if graph_type not in ["actor", "bulletin", "incident"]:
        return HTTPResponse.error("Invalid type provided")

    task_id = generate_graph.delay(q, graph_type, user_id)
    return HTTPResponse.success(data={"task_id": task_id.id})


@admin.get("/api/graph/data")
def get_graph_data() -> Response:
    """
    Endpoint to retrieve graph data from Redis.

    Returns:
        - graph data in JSON format.
    """
    user_id = current_user.id

    # Construct the key to retrieve the graph data from Redis
    graph_data_key = f"user{user_id}:graph:data"

    # Retrieve the graph data from Redis
    graph_data = rds.get(graph_data_key)

    if graph_data:
        # Return the graph data as a JSON response
        return HTTPResponse.success(data=json.loads(graph_data))
    else:
        # If data is not found in Redis
        return HTTPResponse.not_found("Graph data not found")


@admin.get("/api/graph/status")
def check_graph_status() -> Response:
    """Returns the status of the graph visualization task."""
    user_id = current_user.id

    status_key = f"user{user_id}:graph:status"
    status = rds.get(status_key)

    if not status:
        return HTTPResponse.not_found("Graph status not found")

    return HTTPResponse.success(data={"status": status.decode("utf-8")})
