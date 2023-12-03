from pathlib import Path

import hashlib
import os

import shortuuid
from flask import request, Response, Blueprint, current_app, json
from flask.templating import render_template
from flask_security.decorators import auth_required, current_user, roles_accepted, roles_required
from sqlalchemy.orm.attributes import flag_modified
from werkzeug.utils import safe_join

from enferno.admin.models import Media
from enferno.data_import.models import DataImport, Mapping
from enferno.data_import.utils.sheet_import import SheetImport
from enferno.tasks import etl_process_file, process_row
from enferno.utils.data_helpers import media_check_duplicates
from enferno.utils.http_response import HTTPResponse

imports = Blueprint('imports', __name__, static_folder='../static',
                   template_folder='../data_import/templates', cli_group=None,
                   url_prefix='/import')

PER_PAGE = 50


@imports.before_request
@auth_required('session')
def data_import_before_request():
    # only admins allowed to interact with these routes
    if not (current_user.has_role("Admin")):
        return HTTPResponse.FORBIDDEN

@imports.route('/log/')
@imports.get('/log/<int:id>')
def data_import_dashboard(id=None):
    """
    Endpoint to render the log dashboard
    :return: html page of the log dashbaord
    """
    return render_template('import-log.html')

@imports.get('/api/imports/<int:id>')
def api_import_get(id):
    """
    Endpoint to get a single log item
    :param id: id of the log
    :return: log in json format / success or error
    """
    data_import = DataImport.query.get(id)

    if data_import is None:
        return HTTPResponse.NOT_FOUND
    else:
        return json.dumps(data_import.to_dict()), 200
    
@imports.post('/api/imports/')
def api_imports():
    """
    API endpoint to feed log request items in JSON format with paging
    :param page: db query offset
    :return: successful json feed or error
    """
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)
    q = request.json.get('q', None)
        
    if q and (batch_id := q.get('batch_id')):
        result = DataImport.query.filter(DataImport.batch_id == batch_id).order_by(-DataImport.id).paginate(
            page=page, per_page=per_page, count=True)
    else:
        result = DataImport.query.order_by(-DataImport.id).paginate(
            page=page, per_page=per_page, count=True)

    response = {'items': [item.to_dict() for item in result.items], 'perPage': PER_PAGE, 'total': result.total}

    return Response(json.dumps(response),
                    content_type='application/json')


# Data Import Backend API
@imports.route('/media/')
@roles_required('Admin')
def media_import():
    """
    Endpoint to render the etl backend
    :return: html page of the users backend.
    """
    if not current_app.config['ETL_TOOL']:
        return HTTPResponse.NOT_FOUND
    return render_template('media-import.html')


@imports.post('/media/path/')
@roles_required('Admin')
def path_process():
    # Check if path import is enabled and allowed path is set
    if not current_app.config.get('ETL_PATH_IMPORT') \
            or current_app.config.get('ETL_ALLOWED_PATH') is None:
        return HTTPResponse.FORBIDDEN

    allowed_path = Path(current_app.config.get('ETL_ALLOWED_PATH'))

    if not allowed_path.is_dir():
        return "Allowed import path is not configured correctly", 417

    sub_path = request.json.get('path')
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

    recursive = request.json.get('recursive', False)
    if recursive:
        items = import_path.rglob('*')
    else:
        items = import_path.glob('*')

    files = [str(file) for file in items]

    output = [{'filename': os.path.basename(file), 'path': file} for file in files]

    return json.dumps(output), 200


@imports.post('/media/process')
@roles_required('Admin')
def etl_process():
    """
    process a single file
    :return: response contains the processing result
    """

    files = request.json.pop('files')
    meta = request.json
    results = []
    batch_id = shortuuid.uuid()[:9]

    for file in files:
        f = file.get("path") or file.get("filename")
        # logging every file early in the process to track progress

        # Initialize log here, outside of the if condition
        data_import = DataImport(user_id=current_user.id,
                  table='bulletin',
                  file=f,
                  batch_id=batch_id,
                  data=meta)

        if meta.get('mode') == 2:
            # getting hash of file for deduplication
            # server-side import doesn't automatically 
            # retrieve files' hashes
            file_check = open(f, 'rb').read()
            data_import.file_hash = file["etag"] = hashlib.md5(file_check).hexdigest()
            data_import.save()

            # checking for existing media or pending or processing imports
            if media_check_duplicates(file.get("etag"), data_import.id):
                data_import.add_to_log(f"File already exists {f}.")
                data_import.fail()
                continue

        data_import.add_to_log(F"Added file {file} to import queue.")       
        #make sure we have a log id
        results.append(etl_process_file.delay(batch_id, file, meta, current_user.id, data_import.id))

    return batch_id, 200


# CSV Tool
@imports.route('/sheets/')
@roles_required('Admin')
def csv_dashboard():
    """
    Endpoint to render the csv backend
    :return: html page of the csv backend.
    """
    if not current_app.config.get('SHEET_IMPORT'):
        return HTTPResponse.NOT_FOUND
    return render_template('sheets-import.html')


@imports.post('/api/csv/upload')
@roles_required('Admin')
def api_local_csv_upload():
    import_dir = Path(current_app.config.get('IMPORT_DIR'))
    # file pond sends multiple requests for multiple files (handle each request as a separate file )
    try:
        f = request.files.get('file')
        # validate immediately
        if not Media.validate_sheet_extension(f.filename):
            return 'This file type is not allowed', 415
        # final file
        filename = Media.generate_file_name(f.filename)
        filepath = (import_dir / filename).as_posix()
        f.save(filepath)
        # get md5 hash
        f = open(filepath, 'rb').read()
        etag = hashlib.md5(f).hexdigest()

        response = {'etag': etag, 'filename': filename}
        return Response(json.dumps(response), content_type='application/json'), 200
    except Exception as e:
        print(e)
        return F'Request Failed', 417


@imports.delete('/api/csv/upload/')
@roles_required('Admin')
def api_local_csv_delete():
    """
    API endpoint for removing files ::
    :return:  success if file is removed
    keeping uploaded sheets for now, used as a handler for http calls from filepond for now.
    """
    return ''


@imports.post('/api/csv/analyze')
@roles_required('Admin')
def api_csv_analyze():
    # locate file
    filename = request.json.get('file').get('filename')
    import_dir = Path(current_app.config.get('IMPORT_DIR'))

    filepath = (import_dir / filename).as_posix()
    result = SheetImport.parse_csv(filepath)

    if result:
        return json.dumps(result)
    else:
        return 'Problem parsing sheet file', 417


# Excel sheet selector
@imports.post('/api/xls/sheets')
@roles_required('Admin')
def api_xls_sheet():
    filename = request.json.get('file').get('filename')
    import_dir = Path(current_app.config.get('IMPORT_DIR'))

    filepath = (import_dir / filename).as_posix()
    sheets = SheetImport.get_sheets(filepath)

    return json.dumps(sheets)


@imports.post('/api/xls/analyze')
@roles_required('Admin')
def api_xls_analyze():
    # locate file
    filename = request.json.get('file').get('filename')
    import_dir = Path(current_app.config.get('IMPORT_DIR'))

    filepath = (import_dir / filename).as_posix()
    sheet = request.json.get('sheet')

    result = SheetImport.parse_excel(filepath, sheet)

    if result:
        return Response(json.dumps(result, sort_keys=False), content_type='application/json'), 200
    else:
        return 'Problem parsing sheet file', 417


# Saved Searches
@imports.route('/api/mappings/')
def api_mappings():
    """
    Endpoint to get sheet mappings
    :return: successful json feed of mappings or error
    """
    mappings = Mapping.query.all()
    return json.dumps([map.to_dict() for map in mappings]), 200


@imports.post('/api/mapping/')
@roles_accepted('Admin')
def api_mapping_create():
    """
    API Endpoint save a mapping object
    :return: success if save is successful, error otherwise
    """
    d = request.json.get('data', None)

    name = request.json.get('name', None)
    if d and name:
        map = Mapping()
        map.name = name
        map.data = d
        map.user_id = current_user.id
        # Important : flag json field to enable correct update
        flag_modified(map, 'data')

        if map.save():
            return {'message': F'Mapping #{map.id} created successfully', 'id': map.id}, 200
        else:
            return F'Error creating Mapping', 417
    else:
        return "Update request missing parameters data", 417


@imports.put('/api/mapping/<int:id>')
@roles_accepted('Admin')
def api_mapping_update(id):
    """
    API Endpoint update a mapping object
    :return: success if save is successful, error otherwise
    """
    map = Mapping.query.get(id)
    if map:
        data = request.json.get('data')
        m = data.get('map', None)
        name = request.json.get('name', None)
        if m and name:
            map.name = name
            map.data = data
            map.user_id = current_user.id
            if map.save():
                return {'message': F'Mapping #{map.id} updated successfully', 'id': map.id}, 200
            else:
                return F'Error updating Mapping', 417
        else:
            return "Update request missing parameters data", 417

    else:
        return HTTPResponse.NOT_FOUND


@imports.post('/api/process-sheet')
@roles_accepted('Admin')
def api_process_sheet():
    """
    API Endpoint invoke sheet import into target model via a CSV mapping
    :return: success if save is successful, error otherwise
    """
    files = request.json.get('files')
    import_dir = Path(current_app.config.get('IMPORT_DIR'))
    map = request.json.get('map')
    vmap = request.json.get('vmap')
    sheet = request.json.get('sheet')
    lang = request.json.get('lang', 'en')
    actor_config = request.json.get('actorConfig')
    roles = request.json.get('roles')
                             
    batch_id = shortuuid.uuid()[:9]

    for filename in files:
        filepath = (import_dir / filename).as_posix()
        f = open(filepath, 'rb').read()
        etag = hashlib.md5(f).hexdigest()

        df = SheetImport.sheet_to_df(filepath, sheet)
        for row_id, row in df.iterrows():
            data_import = DataImport(user_id=current_user.id, 
                        table='actor', 
                        file=filename,
                        file_hash=etag,
                        batch_id=batch_id,
                        data=row.to_json(orient='index'),
                        log='')
            
            data_import.file_format = 'xls' if sheet else 'csv'

            string = F"Added row {row_id} from file {filename}"
            if sheet: 
                string += F" sheet {sheet}"
            string += F" to import queue."
            data_import.add_to_log(string)

            process_row.delay(filepath, sheet, row_id, data_import.id, map, batch_id, vmap, actor_config, lang, roles)

    return batch_id, 200
