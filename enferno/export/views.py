from pathlib import Path

from flask import request, Response, Blueprint, json, send_from_directory
from flask.templating import render_template
from flask_security.decorators import login_required, current_user, roles_required

from enferno.admin.models import Activity
from enferno.export.models import Export
from enferno.tasks import generate_export
from enferno.utils.http_response import HTTPResponse

export = Blueprint('export', __name__, static_folder='../static',
                   template_folder='../export/templates', cli_group=None,
                   url_prefix='/export')

PER_PAGE = 30


@export.before_request
@login_required
def export_before_request():
    # check user's permissions
    if not (current_user.has_role("Admin") or current_user.can_export):
        return HTTPResponse.FORBIDDEN

@export.route('/dashboard/')
@export.get('/dashboard/<int:id>')
def exports_dashboard(id=None):
    """
    Endpoint to render the exports dashboard
    :return: html page of the exports dashbaord
    """
    return render_template('export-dashboard.html')

@export.post('/api/bulletin/export')
def export_bulletins():
    """
    just creates an export request
    :return: success code / failure if something goes wrong
    """
    # create an export request
    export_request = Export()
    export_request.from_json('bulletin', request.json)
    if export_request.save():
        # Record activity
        Activity.create(current_user, Activity.ACTION_CREATE, export_request.to_mini(), Export.__table__.name)

        return f'Export request created successfully, id:  {export_request.id} ', 200
    return 'Error creating export request', 417


@export.get('/api/export/<int:id>')
def api_export_get(id):
    """
    Endpoint to get a single export
    :param id: id of the export
    :return: export in json format / success or error
    """
    export = Export.query.get(id)

    if export is None:
        return HTTPResponse.NOT_FOUND
    else:
        return json.dumps(export.to_dict()), 200


@export.get('/api/exports/', defaults={'page': 1})
@export.get('/api/exports/<int:page>/')
def api_exports(page):
    """
    API endpoint to feed export request items in josn format - supports paging
    and generated based on user role
    :param page: db query offset
    :return: successful json feed or error
    """
    if current_user.has_role('Admin'):
        result = Export.query.order_by(-Export.id).paginate(
            page=page, per_page=PER_PAGE, count=True)
    else:
        # if a normal authenticated user, get own export requests only
        result = Export.query.filter(
            Export.requester_id == current_user.id
        ).order_by(-Export.id).paginate(page=page, per_page=PER_PAGE, count=True)

    response = {'items': [item.to_dict() for item in result.items], 'perPage': PER_PAGE, 'total': result.total}

    return Response(json.dumps(response),
                    content_type='application/json')


@export.put('/api/exports/status')
@roles_required('Admin')
def change_export_status():
    """
    endpoint to approve or reject an export request
    :return: success / error based on the operation outcome
    """
    action = request.json.get('action')
    if not action or action not in ['approve', 'reject']:
        return 'Please check request action', 417
    export_id = request.json.get("exportId")

    if not export_id:
        return 'Invalid export request id', 417
    export_request = Export.query.get(export_id)

    if not export_request:
        return 'Export request does not exist', 404
    
    if action == 'approve':
        export_request = export_request.approve()
        if export_request.save():
            # record activity
            Activity.create(current_user, Activity.ACTION_APPROVE_EXPORT, export_request.to_mini(), Export.__table__.name)
            # implement celery task chaining
            generate_export(export_id)

            return 'Export request approval will be processed shortly.', 200

    if action == 'reject':
        export_request = export_request.reject()
        if export_request.save():
            # record activity
            Activity.create(current_user, Activity.ACTION_REJECT_EXPORT, export_request.to_mini(), Export.__table__.name)

            return 'Export request rejected.', 200


@export.put('/api/exports/expiry')
@roles_required('Admin')
def update_expiry():
    """
    endpoint to set expiry date of an approved export
    :return: success / error based on the operation outcome
    """
    export_id = request.json.get("exportId")
    new_date = request.json.get('expiry')
    export_request = Export.query.get(export_id)

    if export_request.expired:
        return HTTPResponse.FORBIDDEN
    else:
        try:
            export_request.set_expiry(new_date)
        except Exception as e:
            return 'Invalid expiry date', 417
        
        if export_request.save():
            return F"Updated Export #{export_id}", 200
        else:
            return 'Save failed', 417


@export.get('/api/exports/download')
def download_export_file():
    """
    Endpoint to Download an export file
    :param export id identifier
    :return: url to download the file or access denied response if the export has expired
    """
    uid = request.args.get('exportId')

    try:

        export_id = Export.decrypt_unique_id(uid)
        export = Export.query.get(export_id)

        # check permissions for download
        # either admin or user is requester
        if not current_user.has_role('Admin'):
            if current_user.id != export.requester.id:
                return HTTPResponse.FORBIDDEN

        if not export_id or not export:
            return HTTPResponse.NOT_FOUND
        # check expiry
        if not export.expired:
            return send_from_directory(f'{Path(*Export.export_dir.parts[1:])}', f'{export.file_id}.zip')
        else:
            return HTTPResponse.REQUEST_EXPIRED

    except Exception as e:
        print(f'Unable to decrypt export request uid {e}')
        return HTTPResponse.NOT_FOUND
