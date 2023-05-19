
import hashlib
import os
import shutil
from pathlib import Path
from uuid import uuid4

import boto3
import passlib
import shortuuid
from flask import request, abort, Response, Blueprint, current_app, json, g, session, send_from_directory
from flask.templating import render_template
from flask_bouncer import requires
from flask_security.decorators import roles_required, login_required, current_user, roles_accepted
from sqlalchemy import desc, or_
from sqlalchemy.orm.attributes import flag_modified
from werkzeug.utils import safe_join, secure_filename

from enferno.admin.models import (Bulletin, Label, Source, Location, Eventtype, Media, Actor, Incident, IncidentHistory,
                                  BulletinHistory, ActorHistory, LocationHistory, PotentialViolation, ClaimedViolation,
                                  Activity, Query, Mapping, Log, APIKey, LocationAdminLevel, LocationType)
from enferno.extensions import bouncer, rds
from enferno.extensions import cache
from enferno.tasks import bulk_update_bulletins, bulk_update_actors, bulk_update_incidents, etl_process_file, \
    process_sheet
from enferno.user.models import User, Role
from enferno.utils.search_utils import SearchUtils
from enferno.utils.sheet_utils import SheetUtils
from enferno.utils.http_response import HTTPResponse

root = os.path.abspath(os.path.dirname(__file__))
admin = Blueprint('admin', __name__,
                  template_folder=os.path.join(root, 'templates'),
                  static_folder=os.path.join(root, 'static'),
                  url_prefix='/admin')

# default global items per page
PER_PAGE = 30
REL_PER_PAGE = 5


@admin.before_request
@login_required
def before_request():
    """
    Attaches the user object to all requests
    and a version number that is used to clear the static files cache globally.
    :return: None
    """
    g.user = current_user
    g.version = '5'


@admin.app_context_processor
def ctx():
    """
    passes all users to the application, based on the current user's permissions.
    :return: None
    """
    users = User.query.order_by(User.username).all()
    if current_user.is_authenticated:
        users = [u.to_compact() for u in users]
        return {'users': users}
    return {}


@bouncer.authorization_method
def define_authorization(user, ability):
    """
    Defines users abilities based on their stored permissions.
    :param user: system user
    :param ability: used to restrict/allow what a user can do
    :return: None
    """
    if user.view_usernames:
        ability.can('view', 'usernames')
    if user.view_simple_history or user.view_full_history:
        ability.can('view', 'history')
    # if user.has_role('Admin'):
    #     ability.can('edit', 'Bulletin')
    # else:
    #     def if_assigned(bulletin):
    #         return bulletin.assigned_to_id == user.id

    #     ability.can('edit', Bulletin, if_assigned)


@admin.route('/dashboard')
def dashboard():
    """
    Endpoint to render the dashboard.
    :return: html template for dashboard.
    """
    return render_template('index.html')


# Labels routes
@admin.route('/labels/')
@roles_accepted('Admin', 'Mod')
def labels():
    """
    Endpoint to render the labels backend page.
    :return: html template for labels management.
    """
    return render_template('admin/labels.html')


@admin.route('/api/labels/')
def api_labels():
    """
    API endpoint feed and filter labels with paging
    :return: json response of label objects.
    """
    query = []
    q = request.args.get('q', None)

    if q:
        words = q.split(' ')
        query.extend([Label.title.ilike(F'%{word}%') for word in words])

    typ = request.args.get('typ', None)
    if typ and typ in ['for_bulletin', 'for_actor', 'for_incident', 'for_offline']:
        query.append(
            getattr(Label, typ) == True
        )
    fltr = request.args.get('fltr', None)

    if fltr == 'verified':
        query.append(
            Label.verified == True
        )
    elif fltr == 'all':
        pass
    else:
        query.append(
            Label.verified == False
        )

    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)

    # pull children only when specific labels are searched
    if q:
        result = Label.query.filter(*query).all()
        labels = [label for label in result]
        ids = []
        children = Label.get_children(labels)
        for label in labels + children:
            ids.append(label.id)
        # remove dups
        ids = list(set(ids))
        result = Label.query.filter(
            Label.id.in_(ids)).paginate(
            page=page, per_page=per_page, count=True)
    else:
        result = Label.query.filter(*query).paginate(page=page, per_page=per_page, count=True)

    response = {'items': [item.to_dict(request.args.get('mode', 1)) for item in result.items], 'perPage': per_page,
                'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


@admin.post('/api/label/')
@roles_accepted('Admin', 'Mod')
def api_label_create():
    """
    Endpoint to create a label.
    :return: success/error based on the operation result.
    """
    label = Label()
    created = label.from_json(request.json['item'])
    if created.save():
        return F'Created Label #{label.id}', 200
    else:
        return 'Save Failed', 417


@admin.put('/api/label/<int:id>')
@roles_accepted('Admin', 'Mod')
def api_label_update(id):
    """
    Endpoint to update a label.
    :param id: id of the label
    :return: success/error based on the operation result.
    """
    label = Label.query.get(id)
    if label is not None:
        label = label.from_json(request.json['item'])
        label.save()
        return F'Saved Label #{label.id}', 200
    else:
        return HTTPResponse.NOT_FOUND


@admin.delete('/api/label/<int:id>')
@roles_required('Admin')
def api_label_delete(id):
    """
    Endpoint to delete a label.
    :param id: id of the label
    :return: Success/error based on operation's result.
    """
    label = Label.query.get(id)
    label.delete()
    return F'Deleted Label #{label.id}', 200


@admin.post('/api/label/import/')
@roles_required('Admin')
def api_label_import():
    """
    Endpoint to import labels via CSV
    :return: Success/error based on operation's result.
    """
    if 'csv' in request.files:
        Label.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 400


# EventType routes
@admin.route('/eventtypes/')
@roles_accepted('Admin', 'Mod')
def eventtypes():
    """
    Endpoint to render event types backend
    :return: html template of the event types backend
    """
    return render_template('admin/eventtypes.html')


@admin.route('/api/eventtypes/')
def api_eventtypes():
    """
    API endpoint to serve json feed of even types with paging support
    :return: json feed/success or error/404 based on request data
    """
    query = []
    q = request.args.get('q', None)
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)

    if q is not None:
        query.append(Eventtype.title.ilike('%' + q + '%'))

    typ = request.args.get('typ', None)
    if typ and typ in ['for_bulletin', 'for_actor']:
        query.append(
            getattr(Eventtype, typ) == True
        )
    result = Eventtype.query.filter(
        *query).order_by(Eventtype.id).paginate(page=page, per_page=per_page, count=True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': per_page, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


@admin.post('/api/eventtype/')
@roles_accepted('Admin', 'Mod')
def api_eventtype_create():
    """
    Endpoint to create an Event Type
    :return: Success/Error based on operation's result
    """
    eventtype = Eventtype()
    created = eventtype.from_json(request.json['item'])
    if created.save():
        return F'Created Event #{eventtype.id}', 200
    else:
        return 'Save Failed', 417


@admin.put('/api/eventtype/<int:id>')
@roles_accepted('Admin', 'Mod')
def api_eventtype_update(id):
    """
    Endpoint to update an Event Type
    :param id: id of the item to be updated
    :return: success/error based on the operation's result
    """
    eventtype = Eventtype.query.get(id)
    if eventtype is None:
        return HTTPResponse.NOT_FOUND

    eventtype = eventtype.from_json(request.json['item'])
    eventtype.save()
    return F'Saved Event #{eventtype.id}', 200


@admin.delete('/api/eventtype/<int:id>')
@roles_required('Admin')
def api_eventtype_delete(id):
    """
    Endpoint to delete an event type
    :param id: id of the item
    :return: success/error based on the operation's result
    """
    eventtype = Eventtype.query.get(id)
    if eventtype is None:
        return HTTPResponse.NOT_FOUND

    eventtype.delete()
    return F'Deleted Event #{eventtype.id}', 200


@admin.post('/api/eventtype/import/')
@roles_required('Admin')
def api_eventtype_import():
    """
    Endpoint to bulk import event types from a CSV file
    :return: success/error based on the operation's result
    """
    if 'csv' in request.files:
        Eventtype.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 400


@admin.route('/api/potentialviolation/', defaults={'page': 1})
@admin.route('/api/potentialviolation/<int:page>/')
def api_potentialviolations(page):
    """
    API endpoint that feeds json data of potential violations with paging and search support
    :param page: db query offset
    :return: json feed / success or error based on the operation/request data
    """
    query = []
    q = request.args.get('q', None)
    if q is not None:
        query.append(PotentialViolation.title.ilike('%' + q + '%'))
    result = PotentialViolation.query.filter(
        *query).order_by(PotentialViolation.id).paginate(page=page, per_page=per_page, count=True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': PER_PAGE, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


@admin.post('/api/potentialviolation/')
@roles_accepted('Admin', 'Mod')
def api_potentialviolation_create():
    """
    Endpoint to create a potential violation
    :return: success/error based on operation's result
    """
    potentialviolation = PotentialViolation()
    created = potentialviolation.from_json(request.json['item'])
    if created.save():
        return F'Created Potential Violation #{potentialviolation.id}', 200
    else:
        return 'Save Failed', 417


@admin.put('/api/potentialviolation/<int:id>')
@roles_accepted('Admin', 'Mod')
def api_potentialviolation_update(id):
    """
    Endpoint to update a potential violation
    :param id: id of the item to be updated
    :return: success/error based on the operation's result
    """
    potentialviolation = PotentialViolation.query.get(id)
    if potentialviolation is None:
        return HTTPResponse.NOT_FOUND

    potentialviolation = potentialviolation.from_json(request.json['item'])
    potentialviolation.save()
    return F'Saved Potential Violation #{potentialviolation.id}', 200


@admin.delete('/api/potentialviolation/<int:id>')
@roles_required('Admin')
def api_potentialviolation_delete(id):
    """
    Endpoint to delete a potential violation
    :param id: id of the item to delete
    :return: success/error based on the operation's result
    """
    potentialviolation = PotentialViolation.query.get(id)
    if potentialviolation is None:
        return HTTPResponse.NOT_FOUND
    potentialviolation.delete()
    return F'Deleted Potential Violation #{potentialviolation.id}', 200


@admin.post('/api/potentialviolation/import/')
@roles_required('Admin')
def api_potentialviolation_import():
    """
    Endpoint to import potential violations from csv file
    :return: success/error based on operation's result
    """
    if 'csv' in request.files:
        PotentialViolation.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 400


@admin.route('/api/claimedviolation/', defaults={'page': 1})
@admin.route('/api/claimedviolation/<int:page>')
def api_claimedviolations(page):
    """
    API endpoint to feed json items of claimed violations, supports paging and search
    :param page: db query offset
    :return: json feed / success or error code
    """
    query = []
    q = request.args.get('q', None)
    if q is not None:
        query.append(ClaimedViolation.title.ilike('%' + q + '%'))
    result = ClaimedViolation.query.filter(
        *query).order_by(ClaimedViolation.id).paginate(page=page, per_page=per_page, count=True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': PER_PAGE, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


@admin.post('/api/claimedviolation/')
@roles_accepted('Admin', 'Mod')
def api_claimedviolation_create():
    """
    Endpoint to create a claimed violation
    :return: success / error based on operation's result
    """
    claimedviolation = ClaimedViolation()
    created = claimedviolation.from_json(request.json['item'])
    if created.save():
        return F'Created Claimed Violation #{claimedviolation.id}', 200
    else:
        return 'Save Failed', 417


@admin.put('/api/claimedviolation/<int:id>')
@roles_accepted('Admin', 'Mod')
def api_claimedviolation_update(id):
    """
    Endpoint to update a claimed violation
    :param id: id of the item to update
    :return: success/error based on operation's result
    """
    claimedviolation = ClaimedViolation.query.get(id)
    if claimedviolation is None:
        return HTTPResponse.NOT_FOUND

    claimedviolation = claimedviolation.from_json(request.json['item'])
    claimedviolation.save()
    return F'Saved Claimed Violation #{claimedviolation.id}', 200


@admin.delete('/api/claimedviolation/<int:id>')
@roles_required('Admin')
def api_claimedviolation_delete(id):
    """
    Endpoint to delete a claimed violation
    :param id: id of the item to delete
    :return: success/ error based on operation's result
    """
    claimedviolation = ClaimedViolation.query.get(id)
    if claimedviolation is None:
        return HTTPResponse.NOT_FOUND

    claimedviolation.delete()
    return F'Deleted Claimed Violation #{claimedviolation.id}', 200


@admin.post('/api/claimedviolation/import/')
@roles_required('Admin')
def api_claimedviolation_import():
    """
    Endpoint to import claimed violations from a CSV file
    :return: success/error based on operation's result
    """
    if 'csv' in request.files:
        ClaimedViolation.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 400


# Sources routes
@admin.route('/sources/')
@roles_accepted('Admin', 'Mod')
def sources():
    """
    Endpoint to render sources backend page
    :return: html of the sources page
    """
    return render_template('admin/sources.html')


@admin.route('/api/sources/')
def api_sources():
    """
    API Endpoint to feed json data of sources, supports paging and search
    :return: json feed of sources or error code based on operation's result
    """
    query = []
    q = request.args.get('q', None)

    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)

    if q is not None:
        words = q.split(' ')
        query.extend([Source.title.ilike(F'%{word}%') for word in words])

    # ignore complex recursion when pulling all sources without filters
    if q:
        result = Source.query.filter(*query).all()
        sources = [source for source in result]
        ids = []
        children = Source.get_children(sources)
        for source in sources + children:
            ids.append(source.id)

        # remove dups
        ids = list(set(ids))

        result = Source.query.filter(
            Source.id.in_(ids)).order_by(-Source.id).paginate(
            page=page, per_page=per_page, count=True)
    else:
        result = Source.query.filter(*query).paginate(
            page=page, per_page=per_page, count=True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': per_page, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


@admin.post('/api/source/')
@roles_accepted('Admin', 'Mod')
def api_source_create():
    """
    Endpoint to create a source
    :return: success/error based on operation's result
    """
    source = Source()
    created = source.from_json(request.json['item'])
    if created.save():
        return F'Created Source #{source.id}', 200
    else:
        return 'Save Failed', 417


@admin.put('/api/source/<int:id>')
@roles_accepted('Admin', 'Mod')
def api_source_update(id):
    """
    Endpoint to update a source
    :param id: id of the item to update
    :return: success/error based on the operation's result
    """
    source = Source.query.get(id)
    if source is not None:
        return HTTPResponse.NOT_FOUND

    source = source.from_json(request.json['item'])
    source.save()
    return F'Saved Source #{source.id}', 200


@admin.delete('/api/source/<int:id>')
@roles_required('Admin')
def api_source_delete(id):
    """
    Endopint to delete a source item
    :param id: id of the item to delete
    :return: success/error based on operation's result
    """
    source = Source.query.get(id)
    if source is None:
        return HTTPResponse.NOT_FOUND
    source.delete()
    return F'Deleted Source #{source.id}', 200


@admin.route('/api/source/import/', methods=['POST'])
@roles_required('Admin')
def api_source_import():
    """
    Endpoint to import sources from CSV data
    :return: success/error based on operation's result
    """
    if 'csv' in request.files:
        Source.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 400


# locations routes

@admin.route('/locations/', defaults={'id': None})
@admin.route('/locations/<int:id>')
@roles_accepted('Admin', 'Mod', 'DA')
def locations(id):
    """Endpoint for locations management."""
    return render_template('admin/locations.html')


@admin.get('/api/locations/')
def api_locations():
    """Returns locations in JSON format, allows search and paging."""
    query = []
    q = request.args.get('q', None)
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)

    if q:
        search = '%' + q.replace(' ', '%') + '%'
        query.append(
            or_(
                Location.full_location.ilike(search),
                Location.title_ar.ilike(search),
            )

        )

    lvl = request.args.get('lvl', None)
    if lvl:
        lvls = [al.code for al in LocationAdminLevel.query.all()]
        if int(lvl) in lvls:
            # finds all children of specific location type
            lal = LocationAdminLevel.query.filter(LocationAdminLevel.code == int(lvl)).first()
            query.append(Location.admin_level == lal)

    result = Location.query.filter(*query).order_by(Location.id).paginate(page=page, per_page=per_page, count=True)
    items = [item.to_dict() for item in result.items]
    response = {'items': items, 'perPage': per_page,
                'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


@admin.post('/api/location/')
@roles_accepted('Admin', 'Mod', 'DA')
def api_location_create():
    """Endpoint for creating locations."""

    if not current_user.roles_in(['Admin', 'Mod']) and not current_user.can_edit_locations:
        return 'User not allowed to create Locations', 400

    location = Location()
    location = location.from_json(request.json['item'])

    if location.save():
        location.full_location = location.get_full_string()
        location.id_tree = location.get_id_tree()
        location.create_revision()
        return F'Created Location #{location.id}', 200

@admin.put('/api/location/<int:id>')
@roles_accepted('Admin', 'Mod', 'DA')
def api_location_update(id):
    """Endpoint for updating locations. """

    if not current_user.roles_in(['Admin', 'Mod']) and not current_user.can_edit_locations:
        return 'User not allowed to create Locations', 400

    location = Location.query.get(id)
    if location is not None:
        location = location.from_json(request.json.get('item'))
        # we need to commit this change to db first, to utilize CTE
        if location.save():
            # then update the location full string
            location.full_location = location.get_full_string()
            location.id_tree = location.get_id_tree()
            location.create_revision()
            return F'Saved Location #{location.id}', 200
        else:
            return 'Save Failed', 417
    else:
        return HTTPResponse.NOT_FOUND


@admin.delete('/api/location/<int:id>')
@roles_required('Admin')
def api_location_delete(id):
    """Endpoint for deleting locations. """

    if request.method == 'DELETE':
        location = Location.query.get(id)
        location.delete()
        return F'Deleted Location #{location.id}', 200


@admin.post('/api/location/import/')
@roles_required('Admin')
def api_location_import():
    """Endpoint for importing locations."""
    if 'csv' in request.files:
        Location.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 400

# get one location
@admin.get('/api/location/<int:id>')
def api_location_get(id):
    """
    Endpoint to get a single location
    :param id: id of the location
    :return: location in json format / success or error
    """
    location = Location.query.get(id)

    if location is None:
        return HTTPResponse.NOT_FOUND
    else:
        return json.dumps(location.to_dict()), 200


# location admin level endpoints
@admin.route('/api/location-admin-levels/', methods=['GET', 'POST'])
def api_location_admin_levels():
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)

    query = []
    result = LocationAdminLevel.query.filter(
        *query).order_by(-LocationAdminLevel.id).paginate(page=page, per_page=per_page, count=True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': per_page, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


@admin.post('/api/location-admin-level')
@roles_required('Admin')
def api_location_admin_level_create():
    admin_level = LocationAdminLevel()
    admin_level.from_json(request.json['item'])

    if admin_level.save():
        return F'Item created successfully ID ${admin_level.id} !', 200
    else:
        return 'Creation failed.', 417


@admin.put('/api/location-admin-levels/<int:id>')
@roles_required('Admin')
def api_location_admin_level_update(id):
    admin_level = LocationAdminLevel.query.get(id)
    if admin_level:
        admin_level.from_json(request.json.get('item'))
        if admin_level.save():
            return 'Updated !', 200
        else:
            return 'Error saving item', 417
    else:
        return HTTPResponse.NOT_FOUND


# location type endpoints
@admin.route('/api/location-types/', methods=['GET', 'POST'])
def api_location_types():
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)

    query = []
    result = LocationType.query.filter(
        *query).order_by(-LocationType.id).paginate(page=page, per_page=per_page, count=True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': per_page, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


@admin.post('/api/location-type')
@roles_required('Admin')
def api_location_type_create():
    location_type = LocationType()
    location_type.from_json(request.json['item'])

    if location_type.save():
        return F'Item created successfully ID ${location_type.id} !', 200
    else:
        return 'Creation failed.', 417


@admin.put('/api/location-type/<int:id>')
@roles_required('Admin')
def api_location_type_update(id):
    location_type = LocationType.query.get(id)

    if location_type:
        location_type.from_json(request.json.get('item'))
        if location_type.save():
            return 'Updated !', 200
        else:
            return 'Error saving item', 417
    else:
        return HTTPResponse.NOT_FOUND


@admin.delete('/api/location-type/<int:id>')
@roles_required('Admin')
def api_location_type_delete(id):
    """
    Endpoint to delete a location type
    :param id: id of the location type to be deleted
    :return: success/error
    """
    location_type = LocationType.query.get(id)
    if location_type.delete():
        # Record Activity
        Activity.create(current_user, Activity.ACTION_DELETE, location_type.to_mini(), 'location_type')
        return F'Location Type Deleted #{location_type.id}', 200
    else:
        return 'Error deleting location type', 417


# Bulletin routes
@admin.route('/bulletins/', defaults={'id': None})
@admin.route('/bulletins/<int:id>')
def bulletins(id):
    """Endpoint for bulletins management."""
    return render_template('admin/bulletins.html')


def make_cache_key(*args, **kwargs):
    json_key = str(hash(str(request.json)))
    args_key = request.args.get('page') + request.args.get('per_page', PER_PAGE) + request.args.get('cache', '')
    return json_key + args_key


@admin.route('/api/bulletins/', methods=['POST', 'GET'])
@cache.cached(15, make_cache_key)
def api_bulletins():
    """Returns bulletins in JSON format, allows search and paging."""
    su = SearchUtils(request.json, cls='Bulletin')
    queries, ops = su.get_query()
    result = Bulletin.query.filter(*queries.pop(0))

    if len(queries) > 0:
        while queries:
            nextOp = ops.pop(0)
            nextQuery = queries.pop(0)
            if nextOp == 'union':
                result = result.union_all(Bulletin.query.filter(*nextQuery)).distinct(Bulletin.id)
            elif nextOp == 'intersect':
                result = result.intersect_all(Bulletin.query.filter(*nextQuery)).distinct(Bulletin.id)
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)

    result = result.order_by(-Bulletin.id).paginate(page=page, per_page=per_page, count=True)

    # Select json encoding type
    mode = request.args.get('mode', '1')
    response = {'items': [item.to_dict(mode=mode) for item in result.items], 'perPage': per_page, 'total': result.total}

    return Response(json.dumps(response),
                    content_type='application/json'), 200


@admin.post('/api/bulletin/')
@roles_accepted('Admin', 'DA')
def api_bulletin_create():
    """Creates a new bulletin."""
    bulletin = Bulletin()
    bulletin.from_json(request.json['item'])

    # assign automatically to the creator user
    bulletin.assigned_to_id = current_user.id
    bulletin.save()

    # the below will create the first revision by default
    bulletin.create_revision()
    # Record activity
    Activity.create(current_user, Activity.ACTION_CREATE, bulletin.to_mini(), 'bulletin')
    return F'Created Bulletin #{bulletin.id}', 200


@admin.put('/api/bulletin/<int:id>')
@roles_accepted('Admin', 'DA')
def api_bulletin_update(id):
    """Updates a bulletin."""

    bulletin = Bulletin.query.get(id)
    if bulletin is not None:
        if not current_user.can_access(bulletin):
            return 'Restricted Access', 403
        bulletin = bulletin.from_json(request.json['item'])
        bulletin.create_revision()
        # Record Activity
        Activity.create(current_user, Activity.ACTION_UPDATE, bulletin.to_mini(), 'bulletin')
        return F'Saved Bulletin #{bulletin.id}', 200
    else:
        return HTTPResponse.NOT_FOUND


# Add/Update review bulletin endpoint
@admin.put('/api/bulletin/review/<int:id>')
@roles_accepted('Admin', 'DA')
def api_bulletin_review_update(id):
    """
    Endpoint to update a bulletin review
    :param id: id of the bulletin
    :return: success/error based on the outcome
    """
    bulletin = Bulletin.query.get(id)
    if bulletin is not None:
        if not current_user.can_access(bulletin):
            return 'Restricted Access', 403

        bulletin.review = request.json['item']['review'] if 'review' in request.json['item'] else ''
        bulletin.review_action = request.json['item']['review_action'] if 'review_action' in request.json[
            'item'] else ''

        if bulletin.status == 'Peer Review Assigned':
            bulletin.comments = 'Added Peer Review'
        if bulletin.status == 'Peer Reviewed':
            bulletin.comments = 'Updated Peer Review'

        bulletin.status = 'Peer Reviewed'

        # append refs
        refs = request.json.get('item', {}).get('revrefs', [])

        bulletin.ref = bulletin.ref + refs

        if bulletin.save():
            # Create a revision using latest values
            # this method automatically commits
            #  bulletin changes (referenced)           
            bulletin.create_revision()

            # Record Activity
            Activity.create(current_user, Activity.ACTION_UPDATE, bulletin.to_mini(), 'bulletin')
            return F'Bulletin review updated #{bulletin.id}', 200
        else:
            return F'Error saving Bulletin #{id}', 417
    else:
        return HTTPResponse.NOT_FOUND


# bulk update bulletin endpoint
@admin.put('/api/bulletin/bulk/')
@roles_accepted('Admin', 'Mod')
def api_bulletin_bulk_update():
    """
    Endpoint to bulk update bulletins
    :return: success / error
    """

    ids = request.json['items']
    bulk = request.json['bulk']

    # non-intrusive hard validation for access roles based on user
    if not current_user.has_role('Admin'):
        # silently discard access roles
        bulk.pop('roles', None)

    if ids and len(bulk):
        job = bulk_update_bulletins.delay(ids, bulk, current_user.id)
        # store job id in user's session for status monitoring
        key = F'user{current_user.id}:{job.id}'
        rds.set(key, job.id)
        # expire in 3 hours
        rds.expire(key, 60 * 60 * 3)
        return 'Bulk update queued successfully', 200
    else:
        return 'No items selected, or nothing to update', 417


# get one bulletin
@admin.get('/api/bulletin/<int:id>')
def api_bulletin_get(id):
    """
    Endpoint to get a single bulletin
    :param id: id of the bulletin
    :return: bulletin in json format / success or error
    """
    bulletin = Bulletin.query.get(id)
    mode = request.args.get('mode', None)
    if not bulletin:
        return 'Not found', 404
    else:
        # hide review from view-only users
        if not current_user.roles:
            bulletin.review = None
        if current_user.can_access(bulletin):
            return json.dumps(bulletin.to_dict(mode)), 200
        else:
            # block access altogether here, doesn't make sense to send only the id
            return 'Restricted Access', 403


# get bulletin relations
@admin.get('/api/bulletin/relations/<int:id>')
def bulletin_relations(id):
    """
    Endpoint to return related entities of a bulletin
    :return:
    """
    cls = request.args.get('class', None)
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', REL_PER_PAGE, int)
    if not cls or cls not in ['bulletin', 'actor', 'incident']:
        return HTTPResponse.NOT_FOUND
    bulletin = Bulletin.query.get(id)
    if not bulletin:
        return HTTPResponse.NOT_FOUND
    items = []

    if cls == 'bulletin':
        items = bulletin.bulletin_relations
    elif cls == 'actor':
        items = bulletin.actor_relations
    elif cls == 'incident':
        items = bulletin.incident_relations

    start = (page - 1) * per_page
    end = start + per_page
    data = items[start:end]

    load_more = False if end >= len(items) else True
    if data:
        if cls == 'bulletin':
            data = [item.to_dict(exclude=bulletin) for item in data]
        else:
            data = [item.to_dict() for item in data]

    return json.dumps({'items': data, 'more': load_more}), 200


@admin.route('/api/bulletin/import/', methods=['POST'])
@roles_required('Admin')
def api_bulletin_import():
    """
    Endpoint to import bulletins from csv data
    :return: success / error
    """
    if 'csv' in request.files:
        Bulletin.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 400


# ----- self assign endpoints -----

@admin.route('/api/bulletin/assign/<int:id>', methods=['PUT'])
@roles_accepted('Admin', 'DA')
def api_bulletin_self_assign(id):
    """assign a bulletin to the user"""

    # permission check
    if not current_user.can_self_assign:
        return 'User not allowed to self assign', 400

    bulletin = Bulletin.query.get(id)

    if not current_user.can_access(bulletin):
        return 'Restricted Access', 403

    if bulletin:
        b = request.json.get('bulletin')
        # workflow check
        if bulletin.assigned_to_id and bulletin.assigned_to.active:
            return 'Item already assigned to an active user', 400

        # update bulletin assignement
        bulletin.assigned_to_id = current_user.id
        bulletin.comments = b.get('comments')
        bulletin.ref = bulletin.ref or []
        bulletin.ref = bulletin.ref + b.get('ref', [])

        # Change status to assigned if needed
        if bulletin.status == 'Machine Created' or bulletin.status == 'Human Created':
            bulletin.status = 'Assigned'

        # Create a revision using latest values
        # this method automatically commits
        # bulletin changes (referenced)
        bulletin.create_revision()

        # Record Activity
        Activity.create(current_user, Activity.ACTION_UPDATE, bulletin.to_mini(), 'bulletin')
        return F'Saved Bulletin #{bulletin.id}', 200
    else:
        return HTTPResponse.NOT_FOUND


@admin.route('/api/actor/assign/<int:id>', methods=['PUT'])
@roles_accepted('Admin', 'DA')
def api_actor_self_assign(id):
    """ self assign an actor to the user"""

    # permission check
    if not current_user.can_self_assign:
        return 'User not allowed to self assign', 400

    actor = Actor.query.get(id)

    if not current_user.can_access(actor):
        return 'Restricted Access', 403

    if actor:
        a = request.json.get('actor')
        # workflow check
        if actor.assigned_to_id and actor.assigned_to.active:
            return 'Item already assigned to an active user', 400

        # update bulletin assignement
        actor.assigned_to_id = current_user.id
        actor.comments = a.get('comments')

        # Change status to assigned if needed
        if actor.status == 'Machine Created' or actor.status == 'Human Created':
            actor.status = 'Assigned'

        actor.create_revision()

        # Record Activity
        Activity.create(current_user, Activity.ACTION_UPDATE, actor.to_mini(), 'actor')
        return F'Saved Actor #{actor.id}', 200
    else:
        return HTTPResponse.NOT_FOUND


@admin.route('/api/incident/assign/<int:id>', methods=['PUT'])
@roles_accepted('Admin', 'DA')
def api_incident_self_assign(id):
    """ self assign an incident to the user"""

    # permission check
    if not current_user.can_self_assign:
        return 'User not allowed to self assign', 400

    incident = Incident.query.get(id)

    if not current_user.can_access(incident):
        return 'Restricted Access', 403

    if incident:
        i = request.json.get('incident')
        # workflow check
        if incident.assigned_to_id and incident.assigned_to.active:
            return 'Item already assigned to an active user', 400

        # update bulletin assignement
        incident.assigned_to_id = current_user.id
        incident.comments = i.get('comments')

        # Change status to assigned if needed
        if incident.status == 'Machine Created' or incident.status == 'Human Created':
            incident.status = 'Assigned'

        incident.create_revision()

        # Record Activity
        Activity.create(current_user, Activity.ACTION_UPDATE, incident.to_mini(), 'incident')
        return F'Saved Incident #{incident.id}', 200
    else:
        return HTTPResponse.NOT_FOUND


# Media special endpoints

@admin.post('/api/media/chunk')
@roles_accepted('Admin', 'DA')
def api_medias_chunk():
    file = request.files['file']

    # we can immediately validate the file type here
    if not Media.validate_media_extension(file.filename):
        return 'This file type is not allowed', 415
    filename = Media.generate_file_name(file.filename)
    filepath = (Media.media_dir / filename).as_posix()

    dz_uuid = request.form.get("dzuuid")
    if not dz_uuid:
        # Assume this file has not been chunked
        with open(f"{filepath}", "wb") as f:
            file.save(f)
        return "File Saved", 200

    # Chunked upload
    try:
        current_chunk = int(request.form["dzchunkindex"])
        total_chunks = int(request.form["dztotalchunkcount"])
        total_size = int(request.form["dztotalfilesize"])
    except KeyError as err:
        raise abort(400, body=f"Not all required fields supplied, missing {err}")
    except ValueError:
        raise abort(400, body=f"Values provided were not in expected format")

    # validate dz_uuid
    if not safe_join(str(Media.media_file), dz_uuid):
        return 'Invalid Request', 425

    save_dir = Media.media_dir / secure_filename(dz_uuid)

    # validate current chunk
    if not safe_join(str(save_dir), str(current_chunk)) or current_chunk.__class__ != int:
        return 'Invalid Request', 425

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
            raise abort(400, body=f"Error uploading the file")

        print(f"{file.filename} has been uploaded")
        shutil.rmtree(save_dir)
        # get md5 hash
        f = open(filepath, 'rb').read()
        etag = hashlib.md5(f).hexdigest()

        # validate etag here // if it exists // reject the upload and send an error code
        if Media.query.filter(Media.etag == etag).first():
            return 'Error, file already exists', 409

        if not current_app.config.get('FILESYSTEM_LOCAL') and not 'etl' in request.referrer:
            print('uploading file to s3 :::>')
            s3 = boto3.resource('s3')
            s3.Bucket(current_app.config['S3_BUCKET']).upload_file(filepath, filename)
            # Clean up file if s3 mode is selected
            try:
                os.remove(filepath)
            except Exception as e:
                print(e)

        response = {'etag': etag, 'filename': filename}
        return Response(json.dumps(response), content_type='application/json'), 200

    return "Chunk upload successful", 200


@admin.route('/api/media/upload/', methods=['POST'])
@roles_accepted('Admin', 'DA')
def api_medias_upload():
    """
    Endpoint to upload files (based on file system settings : s3 or local file system)
    :return: success /error based on operation's result
    """
    file = request.files.get('file')
    if file:
        if current_app.config['FILESYSTEM_LOCAL'] or (
                'etl' in request.referrer and not current_app.config['FILESYSTEM_LOCAL']):
            return api_local_medias_upload(request)
        else:

            s3 = boto3.resource('s3', aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
                                aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'])

            # final file
            filename = Media.generate_file_name(file.filename)
            # filepath = (Media.media_dir/filename).as_posix()

            response = s3.Bucket(current_app.config['S3_BUCKET']).put_object(Key=filename, Body=file)
            # print(response.get())
            etag = response.get()['ETag'].replace('"', '')

            # check if file already exists
            if Media.query.filter(Media.etag == etag).first():
                return 'Error: File already exists', 409

            return json.dumps({'filename': filename, 'etag': etag}), 200

    return 'Invalid request params', 417


# return signed url from s3 valid for some time
@admin.route('/api/media/<filename>')
def serve_media(filename):
    """
    Endpoint to generate  file urls to be served (based on file system type)
    :param filename: name of the file
    :return: temporarily accessible url of the file
    """

    if current_app.config['FILESYSTEM_LOCAL']:
        file_path = safe_join('/admin/api/serve/media', filename)
        if file_path:
            return file_path, 200
        else:
            return 'Invalid Request', 425
    else:
        # validate access control
        media = Media.query.filter(Media.media_file == filename).first()
        if not current_user.can_access(media):
            return 'Restricted Access', 403
        s3 = boto3.client('s3',
                          aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
                          aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
                          region_name=current_app.config['AWS_REGION']
                          )
        params = {'Bucket': current_app.config['S3_BUCKET'], 'Key': filename}
        if filename.lower().endswith('pdf'):
            params['ResponseContentType'] = 'application/pdf'
        url = s3.generate_presigned_url('get_object', Params=params, ExpiresIn=36000)
        return url, 200


def api_local_medias_upload(request):
    # file pond sends multiple requests for multiple files (handle each request as a separate file )
    try:
        file = request.files.get('file')
        # final file
        filename = Media.generate_file_name(file.filename)
        filepath = (Media.media_dir / filename).as_posix()
        file.save(filepath)
        # get md5 hash
        f = open(filepath, 'rb').read()
        etag = hashlib.md5(f).hexdigest()
        # check if file already exists
        if Media.query.filter(Media.etag == etag).first():
            return 'Error: File already exists', 409

        response = {'etag': etag, 'filename': filename}

        return Response(json.dumps(response), content_type='application/json'), 200
    except Exception as e:
        print(e)
        return F'Request Failed', 417


@admin.route('/api/serve/media/<filename>')
def api_local_serve_media(filename):
    """
    serves file from local file system
    """

    media = Media.query.filter(Media.media_file == filename).first()
    if media and not current_user.can_access(media):
        return 'Restricted Access', 403
    else:
        return send_from_directory('media', filename)


@admin.post('/api/inline/upload')
def api_inline_medias_upload():
    try:
        f = request.files.get('file')

        # final file
        filename = Media.generate_file_name(f.filename)
        filepath = (Media.inline_dir / filename).as_posix()
        f.save(filepath)
        response = {'location': filename}

        return Response(json.dumps(response), content_type='application/json'), 200
    except Exception as e:
        print(e)
        return F'Request Failed', 417


@admin.route('/api/serve/inline/<filename>')
def api_local_serve_inline_media(filename):
    """
    serves inline media files - only for authenticated users
    """
    return send_from_directory('media/inline', filename)


# Medias routes

@admin.route('/api/media/<int:id>', methods=['PUT'])
@roles_accepted('Admin', 'DA')
def api_media_update(id):
    """
    Endpoint to update a media item
    :param id: id of the item to be updated
    :return: success / error
    """
    if request.method == 'PUT':
        media = Media.query.get(id)
        if media is not None:
            media = media.from_json(request.json['item'])
            media.save()
            return 'Saved!', 200
        else:
            return HTTPResponse.NOT_FOUND

    else:
        return HTTPResponse.FORBIDDEN


# Actor routes
@admin.route('/actors/', defaults={'id': None})
@admin.route('/actors/<int:id>')
def actors(id):
    """Endpoint to render actors page."""
    return render_template('admin/actors.html')


@admin.route('/api/actors/', methods=['POST', 'GET'])
def api_actors():
    """Returns actors in JSON format, allows search and paging."""
    su = SearchUtils(request.json, cls='Actor')
    queries, ops = su.get_query()
    result = Actor.query.filter(*queries.pop(0))
    # print (queries, ops)
    if len(queries) > 0:
        while queries:
            nextOp = ops.pop(0)
            nextQuery = queries.pop(0)
            if nextOp == 'union':
                result = result.union(Actor.query.filter(*nextQuery))
            elif nextOp == 'intersect':
                result = result.intersect(Actor.query.filter(*nextQuery))

    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)
    result = result.order_by(Actor.id.desc()).paginate(page=page, per_page=per_page, count=True)
    # Select json encoding type
    mode = request.args.get('mode', '1')
    response = {'items': [item.to_dict(mode=mode) for item in result.items], 'perPage': per_page, 'total': result.total}

    return Response(json.dumps(response),
                    content_type='application/json'), 200


# create actor endpoint
@admin.post('/api/actor/')
@roles_accepted('Admin', 'DA')
def api_actor_create():
    """
    Endpoint to create an Actor item
    :return: success/error based on the operation's result
    """
    actor = Actor()
    actor.from_json(request.json['item'])
    # assign actor to creator by default
    actor.assigned_to_id = current_user.id
    result = actor.save()
    if result:
        # the below will create the first revision by default
        actor.create_revision()
        # Record activity
        Activity.create(current_user, Activity.ACTION_CREATE, actor.to_mini(), 'actor')
        return F'Created Actor #{actor.id}', 200
    else:
        return 'Error creating actor', 417


# update actor endpoint
@admin.put('/api/actor/<int:id>')
@roles_accepted('Admin', 'DA')
def api_actor_update(id):
    """
    Endpoint to update an Actor item
    :param id: id of the actor to be updated
    :return: success/error
    """
    actor = Actor.query.get(id)
    if actor is not None:
        # check for restrictions
        if not current_user.can_access(actor):
            return 'Restricted Access', 403

        actor = actor.from_json(request.json['item'])
        # Create a revision using latest values
        # this method automatically commits
        # actor changes (referenced)
        if actor:
            actor.create_revision()
            # Record activity
            Activity.create(current_user, Activity.ACTION_UPDATE, actor.to_mini(), 'actor')
            return F'Saved Actor #{actor.id}', 200
        else:
            return F'Error saving Actor #{id}', 417
    else:
        return HTTPResponse.NOT_FOUND


# Add/Update review actor endpoint
@admin.put('/api/actor/review/<int:id>')
@roles_accepted('Admin', 'DA')
def api_actor_review_update(id):
    """
    Endpoint to update an Actor's review item
    :param id: id of the actor
    :return: success/error
    """
    actor = Actor.query.get(id)
    if actor is not None:
        if not current_user.can_access(actor):
            return 'Restricted Access', 403

        actor.review = request.json['item']['review'] if 'review' in request.json['item'] else ''
        actor.review_action = request.json['item']['review_action'] if 'review_action' in request.json[
            'item'] else ''

        actor.status = 'Peer Reviewed'

        # Create a revision using latest values
        # this method automatically commits
        #  actor changes (referenced)
        if actor.save():
            actor.create_revision()
            # Record activity
            Activity.create(current_user, Activity.ACTION_UPDATE, actor.to_mini(), 'actor')
            return F'Actor review updated #{id}', 200
        else:
            return F'Error saving Actor #{id}\'s Review', 417
    else:
        return HTTPResponse.NOT_FOUND


# bulk update actor endpoint
@admin.put('/api/actor/bulk/')
@roles_accepted('Admin', 'Mod')
def api_actor_bulk_update():
    """
    Endpoint to bulk update actors
    :return: success/error
    """

    ids = request.json['items']
    bulk = request.json['bulk']

    # non-intrusive hard validation for access roles based on user
    if not current_user.has_role('Admin'):
        # silently discard access roles
        bulk.pop('roles', None)

    if ids and len(bulk):
        job = bulk_update_actors.delay(ids, bulk, current_user.id)
        # store job id in user's session for status monitoring
        key = F'user{current_user.id}:{job.id}'
        rds.set(key, job.id)
        # expire in 3 hour
        rds.expire(key, 60 * 60 * 3)
        return 'Bulk update queued successfully.', 200
    else:
        return 'No items selected, or nothing to update', 417


# get one actor

@admin.get('/api/actor/<int:id>')
def api_actor_get(id):
    """
    Endpoint to get a single actor
    :param id: id of the actor
    :return: actor data in json format + success or error in case of failure
    """
    actor = Actor.query.get(id)
    if not actor:
        return 'Not found', 404
    else:
        mode = request.args.get('mode', None)
        if current_user.can_access(actor):
            return json.dumps(actor.to_dict(mode)), 200
        else:
            # block access altogether here, doesn't make sense to send only the id
            return 'Restricted Access', 403


# get actor relations
@admin.get('/api/actor/relations/<int:id>')
def actor_relations(id):
    """
    Endpoint to return related entities of an Actor
    :return:
    """
    cls = request.args.get('class', None)
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', REL_PER_PAGE, int)
    if not cls or cls not in ['bulletin', 'actor', 'incident']:
        return HTTPResponse.NOT_FOUND
    actor = Actor.query.get(id)
    if not actor:
        return HTTPResponse.NOT_FOUND
    items = []

    if cls == 'bulletin':
        items = actor.bulletin_relations
    elif cls == 'actor':
        items = actor.actor_relations
    elif cls == 'incident':
        items = actor.incident_relations

    # pagination
    start = (page - 1) * per_page
    end = start + per_page
    data = items[start:end]

    load_more = False if end >= len(items) else True

    if data:
        if cls == 'actor':
            data = [item.to_dict(exclude=actor) for item in data]
        else:
            data = [item.to_dict() for item in data]

    return json.dumps({'items': data, 'more': load_more}), 200


@admin.route('/api/actormp/<int:id>', methods=['GET'])
def api_actor_mp_get(id):
    """
    Endpoint to get missing person data for an actor
    :param id: id of the actor
    :return: actor data in json format + success or error in case of failure
    """
    if request.method == 'GET':
        actor = Actor.query.get(id)
        if not actor:
            return HTTPResponse.NOT_FOUND
        else:
            return json.dumps(actor.mp_json()), 200


# Bulletin History Helpers

@admin.route('/api/bulletinhistory/<int:bulletinid>')
@requires('view', 'history')
def api_bulletinhistory(bulletinid):
    """
    Endpoint to get revision history of a bulletin
    :param bulletinid: id of the bulletin item
    :return: json feed of item's history , or error
    """
    result = BulletinHistory.query.filter_by(bulletin_id=bulletinid).order_by(desc(BulletinHistory.created_at)).all()
    # For standardization 
    response = {'items': [item.to_dict() for item in result]}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


# Actor History Helpers 

@admin.route('/api/actorhistory/<int:actorid>')
@requires('view', 'history')
def api_actorhistory(actorid):
    """
        Endpoint to get revision history of an actor
        :param actorid: id of the actor item
        :return: json feed of item's history , or error
        """
    result = ActorHistory.query.filter_by(actor_id=actorid).order_by(desc(ActorHistory.created_at)).all()
    # For standardization 
    response = {'items': [item.to_dict() for item in result]}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


# Incident History Helpers

@admin.route('/api/incidenthistory/<int:incidentid>')
@requires('view', 'history')
def api_incidenthistory(incidentid):
    """
        Endpoint to get revision history of an incident item
        :param incidentid: id of the incident item
        :return: json feed of item's history , or error
        """
    result = IncidentHistory.query.filter_by(incident_id=incidentid).order_by(desc(IncidentHistory.created_at)).all()
    # For standardization 
    response = {'items': [item.to_dict() for item in result]}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


# Location History Helpers

@admin.route('/api/locationhistory/<int:locationid>')
@requires('view', 'history')
def api_locationhistory(locationid):
    """
    Endpoint to get revision history of a location
    :param locationid: id of the location item
    :return: json feed of item's history , or error
    """
    result = LocationHistory.query.filter_by(location_id=locationid).order_by(desc(LocationHistory.created_at)).all()
    # For standardization
    response = {'items': [item.to_dict() for item in result]}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


# user management routes

@admin.route('/api/users/')
@roles_accepted('Admin', 'Mod')
def api_users():
    """
    API endpoint to feed users data in json format , supports paging and search
    :return: success and json feed of items or error
    """
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)
    q = request.args.get('q')
    query = []
    if q is not None:
        query.append(User.name.ilike('%' + q + '%'))
    result = User.query.filter(
        *query).order_by(User.username).paginate(page=page, per_page=per_page, count=True)

    response = {'items':    [item.to_dict() if current_user.has_role('Admin')
                            else item.to_compact()
                            for item in result.items],
                            'perPage': per_page, 'total': result.total}

    return Response(json.dumps(response),
                    content_type='application/json'), 200


@admin.route('/users/')
@roles_required('Admin')
def users():
    """
    Endpoint to render the users backend page
    :return: html page of the users backend.
    """
    return render_template('admin/users.html')


@admin.post('/api/user/')
@roles_required('Admin')
def api_user_create():
    """
    Endpoint to create a user item
    :return: success / error baesd on operation's outcome
    """
    # validate existing
    u = request.json.get('item')
    username = u.get('username')

    exists = User.query.filter(User.username == username).first()
    if len(username) < 4:
        return 'Error, username too short', 417
    if len(username) > 32:
        return 'Error, username too long', 417
    if exists:
        return 'Error, username already exists', 417
    user = User()
    user.fs_uniquifier = uuid4().hex
    user.from_json(u)
    result = user.save()
    if result:
        # Record activity
        Activity.create(current_user, Activity.ACTION_CREATE, user.to_mini(), 'user')
        return F'User {username} has been created successfully', 200
    else:
        return 'Error creating user', 417


@admin.route('/api/checkuser/', methods=['POST'])
@roles_required('Admin')
def api_user_check():
    data = request.json.get('item')
    if not data:
        return 'Please select a username', 417
    u = User.query.filter(User.username == data).first()
    if u:
        return 'Username already exists', 417
    else:
        return 'Username ok', 200


@admin.put('/api/user/<int:uid>')
@roles_required('Admin')
def api_user_update(uid):
    """Endpoint to update a user."""

    user = User.query.get(uid)
    if user is not None:
        u = request.json.get('item')
        user = user.from_json(u)
        if user.save():
            # Record activity
            Activity.create(current_user, Activity.ACTION_UPDATE, user.to_mini(), 'user')
            return F'Saved User {user.id} {user.name}', 200
        else:
            return F'Error saving User {user.id} {user.name}', 417
    else:
        return HTTPResponse.NOT_FOUND


@admin.delete('/api/user/<int:id>')
@roles_required('Admin')
def api_user_delete(id):
    """
    Endpoint to delete a user
    :param id: id of the user to be deleted
    :return: success/error
    """
    if request.method == 'DELETE':
        user = User.query.get(id)
        if user.active:
            return 'User is active, make inactive before deleting', 403
        user.delete()

        # Record activity
        Activity.create(current_user, Activity.ACTION_DELETE, user.to_mini(), 'user')
        return 'Deleted!', 200


# Roles routes
@admin.route('/roles/')
@roles_required('Admin')
def roles():
    """
    Endpoint to redner roles backend page
    :return: html of the page
    """
    return render_template('admin/roles.html')


@admin.route('/api/roles/', defaults={'page': 1})
@admin.route('/api/roles/<int:page>/')
@roles_required('Admin')
def api_roles(page):
    """
    API endpoint to feed roles items in josn format - supports paging and search
    :param page: db query offset
    :return: successful json feed or error
    """
    query = []
    q = request.args.get('q', None)
    if q is not None:
        query.append(
            Role.name.ilike('%' + q + '%')
        )
    result = Role.query.filter(
        *query).order_by(Role.id).paginate(page=page, per_page=PER_PAGE, count=True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': PER_PAGE, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


@admin.post('/api/role/')
@roles_required('Admin')
def api_role_create():
    """
    Endpoint to create a role item
    :return: success/error
    """
    role = Role()
    created = role.from_json(request.json['item'])
    if created.save():
        # Record activity
        Activity.create(current_user, Activity.ACTION_CREATE, role.to_mini(), 'role')
        return 'Created!', 200

    else:
        return 'Save Failed', 417


@admin.put('/api/role/<int:id>')
@roles_required('Admin')
def api_role_update(id):
    """
    Endpoint to update a role item
    :param id: id of the role to be updated
    :return: success / error
    """
    role = Role.query.get(id)
    if role is None:
        return HTTPResponse.NOT_FOUND

    if role.name in ['Admin', 'Mod', 'DA']:
        return 'Cannot edit System Roles', 403

    role = role.from_json(request.json['item'])
    role.save()
    # Record activity
    Activity.create(current_user, Activity.ACTION_UPDATE, role.to_mini(), 'role')
    return 'Saved!', 200


@admin.delete('/api/role/<int:id>')
@roles_required('Admin')
def api_role_delete(id):
    """
    Endpoint to delete a role item
    :param id: id of the role to be deleted
    :return: success / error
    """
    role = Role.query.get(id)

    if role is None:
        return HTTPResponse.NOT_FOUND

    # forbid deleting system roles
    if role.name in ['Admin', 'Mod', 'DA']:
        return 'Cannot delete System Roles', 403
    # forbid delete roles assigned to restricted items
    if role.bulletins.first() or role.actors.first() or role.incidents.first():
        return 'Role assigned to restricted items', 403

    role.delete()
    # Record activity
    Activity.create(current_user, Activity.ACTION_DELETE, role.to_mini(), 'role')
    return 'Deleted!', 200


@admin.post('/api/role/import/')
@roles_required('Admin')
def api_role_import():
    """
    Endpoint to import role items from a CSV file
    :return: success / error
    """
    if 'csv' in request.files:
        Role.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 400


# Incident routes
@admin.route('/incidents/', defaults={'id': None})
@admin.route('/incidents/<int:id>')
def incidents(id):
    """
    Endpoint to render incidents backend page
    :return: html page of the incidents backend management
    """
    # Pass all users to the template
    return render_template('admin/incidents.html')


@admin.route('/api/incidents/', methods=['POST', 'GET'])
def api_incidents():
    """Returns actors in JSON format, allows search and paging."""
    query = []

    su = SearchUtils(request.json, cls='Incident')

    query = su.get_query()

    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)

    result = Incident.query.filter(
        *query).order_by(Incident.id.desc()).paginate(page=page, per_page=per_page, count=True)
    # Select json encoding type
    mode = request.args.get('mode', '1')
    response = {'items': [item.to_dict(mode=mode) for item in result.items], 'perPage': per_page, 'total': result.total}

    return Response(json.dumps(response),
                    content_type='application/json'), 200


@admin.post('/api/incident/')
@roles_accepted('Admin', 'DA')
def api_incident_create():
    """API endpoint to create an incident."""

    incident = Incident()
    incident.from_json(request.json['item'])
    # assign to creator by default
    incident.assigned_to_id = current_user.id
    incident.save()
    # the below will create the first revision by default
    incident.create_revision()
    # Record activity
    Activity.create(current_user, Activity.ACTION_CREATE, incident.to_mini(), 'incident')
    return F'Created Incident #{incident.id}', 200


# update incident endpoint
@admin.put('/api/incident/<int:id>')
@roles_accepted('Admin', 'DA')
def api_incident_update(id):
    """API endpoint to update an incident."""

    incident = Incident.query.get(id)

    if incident is not None:
        if not current_user.can_access(incident):
            return 'Restricted Access', 403
        incident = incident.from_json(request.json['item'])
        # Create a revision using latest values
        # this method automatically commits
        # incident changes (referenced)
        if incident:
            incident.create_revision()
            # Record activity
            Activity.create(current_user, Activity.ACTION_UPDATE, incident.to_mini(), 'incident')
            return F'Saved Incident #{id}', 200
        else:
            return F'Error saving Incident {id}', 417
    else:
        return HTTPResponse.NOT_FOUND


# Add/Update review incident endpoint
@admin.put('/api/incident/review/<int:id>')
@roles_accepted('Admin', 'DA')
def api_incident_review_update(id):
    """
    Endpoint to update an incident review item
    :param id: id of the incident
    :return: success / error
    """
    incident = Incident.query.get(id)
    if incident is not None:
        if not current_user.can_access(incident):
            return 'Restricted Access', 403

        incident.review = request.json['item']['review'] if 'review' in request.json['item'] else ''
        incident.review_action = request.json['item']['review_action'] if 'review_action' in request.json[
            'item'] else ''

        incident.status = 'Peer Reviewed'
        if incident.save():
            # Create a revision using latest values
            # this method automatically commi
            # incident changes (referenced)
            incident.create_revision()
            # Record activity
            Activity.create(current_user, Activity.ACTION_UPDATE, incident.to_mini(), 'incident')
            return F'Bulletin review updated #{id}', 200
        else:
            return F'Error saving Incident #{id}\'s Review', 417
    else:
        return HTTPResponse.NOT_FOUND


# bulk update incident endpoint
@admin.put('/api/incident/bulk/')
@roles_accepted('Admin', 'Mod')
def api_incident_bulk_update():
    """endpoint to handle bulk incidents updates."""

    ids = request.json['items']
    bulk = request.json['bulk']

    # non-intrusive hard validation for access roles based on user
    if not current_user.has_role('Admin'):
        # silently discard access roles
        bulk.pop('roles', None)
        bulk.pop('rolesReplace', None)
        bulk.pop('restrictRelated', None)

    if ids and len(bulk):
        job = bulk_update_incidents.delay(ids, bulk, current_user.id)
        # store job id in user's session for status monitoring
        key = F'user{current_user.id}:{job.id}'
        rds.set(key, job.id)
        # expire in 3 hour
        rds.expire(key, 60 * 60 * 3)
        return 'Bulk update queued successfully', 200
    else:
        return 'No items selected, or nothing to update', 417


# get one incident
@admin.get('/api/incident/<int:id>')
def api_incident_get(id):
    """
    Endopint to get a single incident by id
    :param id: id of the incident item
    :return: successful incident item in json format or error
    """
    incident = Incident.query.get(id)
    if not incident:
        return 'Not Found', 404
    else:
        mode = request.args.get('mode', None)
        if current_user.can_access(incident):
            return json.dumps(incident.to_dict(mode)), 200
        else:
            # block access altogether here, doesn't make sense to send only the id
            return 'Restricted Access', 403


# get incident relations
@admin.get('/api/incident/relations/<int:id>')
def incident_relations(id):
    """
    Endpoint to return related entities of an Incident
    :return:
    """
    cls = request.args.get('class', None)
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', REL_PER_PAGE, int)
    if not cls or cls not in ['bulletin', 'actor', 'incident']:
        return HTTPResponse.NOT_FOUND
    incident = Incident.query.get(id)
    if not incident:
        return HTTPResponse.NOT_FOUND
    items = []

    if cls == 'bulletin':
        items = incident.bulletin_relations
    elif cls == 'actor':
        items = incident.actor_relations
    elif cls == 'incident':
        items = incident.incident_relations

    # add support for loading all relations at once
    if page == 0:
        if cls == 'incident':
            data = [item.to_dict(exclude=incident) for item in items]
        else:
            data = [item.to_dict() for item in items]

        return json.dumps({'items': data, 'more': False}), 200

    # pagination
    start = (page - 1) * per_page
    end = start + per_page
    data = items[start:end]

    load_more = False if end >= len(items) else True

    if data:
        if cls == 'incident':
            data = [item.to_dict(exclude=incident) for item in data]
        else:
            data = [item.to_dict() for item in data]

    return json.dumps({'items': data, 'more': load_more}), 200


@admin.route('/api/incident/import/', methods=['POST'])
@roles_required('Admin')
def api_incident_import():
    """
    Endpoint to handle incident imports.
    :return: successful response or error code in case of failure.
    """
    if 'csv' in request.files:
        Incident.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 417


# Activity routes
@admin.route('/activity/')
@roles_required('Admin')
def activity():
    """
    Endpoint to render activity backend page
    :return: html of the page
    """
    return render_template('admin/activity.html')


@admin.route('/api/activity', methods=['POST', 'GET'])
@roles_required('Admin')
def api_activity():
    """
    API endpoint to feed activity items in json format, supports paging and filtering by tag
    :return: successful json feed or error
    """
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)
    query = []
    tag = request.json.get('tag', None)
    if tag:
        query.append(Activity.tag == tag)

    result = Activity.query.filter(
        *query).order_by(-Activity.id).paginate(page=page, per_page=per_page, count=True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': per_page, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


@admin.route('/api/bulk/status/')
def bulk_status():
    """Endpoint to get status update about background bulk operations"""
    uid = current_user.id
    cursor, jobs = rds.scan(0, F'user{uid}:*', 1000)
    tasks = []
    for key in jobs:
        result = {}
        id = key.decode('utf-8').split(':')[-1]
        type = request.args.get('type')
        status = None
        if type == 'bulletin':
            status = bulk_update_bulletins.AsyncResult(id).status
        elif type == 'actor':
            status = bulk_update_incidents.AsyncResult(id).status
        elif type == 'incident':
            status = bulk_update_actors.AsyncResult(id).status
        else:
            return HTTPResponse.NOT_FOUND

        # handle job failure
        if status == 'FAILURE':
            rds.delete(key)
        if status != 'SUCCESS':
            result['id'] = id
            result['status'] = status
            tasks.append(result)

        else:
            rds.delete(key)
    return json.dumps(tasks)


@admin.post('/api/key')
@roles_required('Admin')
def gen_api_key():
    global_key = APIKey.query.first()
    if not global_key:
        global_key = APIKey()
    global_key.key = passlib.totp.generate_secret()
    global_key.save()
    return global_key.key, 200


@roles_required(['Admin'])
@admin.route('/api/key')
def get_api_key():
    return APIKey.get_global_key(), 200


# Saved Searches
@admin.route('/api/queries/')
def api_queries():
    """
    Endpoint to get user saved searches
    :return: successful json feed of saved searches or error
    """
    user_id = current_user.id
    queries = Query.query.filter(Query.user_id == user_id)
    return json.dumps([query.to_dict() for query in queries]), 200


@admin.post('/api/query/')
@roles_accepted('Admin', 'DA')
def api_query_create():
    """
    API Endpoint save a query search object (advanced search)
    :return: success if save is successful, error otherwise
    """
    q = request.json.get('q', None)

    name = request.json.get('name', None)
    if q and name:
        query = Query()
        query.name = name
        query.data = q
        query.user_id = current_user.id
        query.save()
        return 'Query successfully saved!', 200
    else:
        return 'Error parsing query data', 417


# Data Import Backend API
@admin.route('/etl/')
@roles_required('Admin')
def etl_dashboard():
    """
    Endpoint to render the etl backend
    :return: html page of the users backend.
    """
    if not current_app.config['ETL_TOOL']:
        return HTTPResponse.NOT_FOUND
    return render_template('admin/etl-dashboard.html')


@admin.route('/etl/status')
@roles_required('Admin')
def etl_status():
    """
    Endpoint to render etl tasks monitoring
    :return: html page of the users backend.
    """
    return render_template('admin/etl-status.html')


@admin.post('/etl/path/')
@roles_required('Admin')
def path_process():
    # Check if path import is enabled and allowed path is set
    if not current_app.config.get('ETL_PATH_IMPORT') \
            or current_app.config.get('ETL_ALLOWED_PATH') is None:
        return HTTPResponse.FORBIDDEN

    allowed_path = Path(current_app.config.get('ETL_ALLOWED_PATH'))
    path = Path(request.json.get('path'))

    if not allowed_path.is_dir():
        return "Allowed import path is not configured correctly", 417

    if not request.json.get('path') or not path.is_dir():
        return "Invalid path specified", 417

    # check if supplied path is either the allowed path or a sub-path
    if not (path == allowed_path or allowed_path in path.parents):
        return HTTPResponse.FORBIDDEN

    recursive = request.json.get('recursive', False)
    if recursive:
        items = path.rglob('*')
    else:
        items = path.glob('*')

    files = [str(file) for file in items]

    output = [{'filename': os.path.basename(file), 'path': file} for file in files]

    return json.dumps(output), 200


@admin.post('/etl/process')
@roles_required('Admin')
def etl_process():
    """
    process a single file
    :return: response contains the processing result
    """

    files = request.json.pop('files')
    meta = request.json
    results = []
    batch_id = 'ETL' + shortuuid.uuid()[:9]
    batch_log = batch_id + '.log'
    open('logs/' + batch_log, 'a')

    for file in files:
        results.append(etl_process_file.delay(batch_id, file, meta, user_id=current_user.id, log=batch_log))

    ids = [r.id for r in results]
    session['etl-tasks'] = ids
    return 'ETL operation queued successfully.', 200


@admin.route('/api/etl/status/')
@roles_required('Admin')
def etl_task_status():
    """
    API endpoing for ETL task status
    :return: response contains every task with status
    """
    ids = session['etl-tasks']
    results = [etl_process_file.AsyncResult(i) for i in ids]
    output = [r.state for r in results]
    return json.dumps(output), 200


# CSV Tool


@admin.route('/csv/dashboard/')
@roles_required('Admin')
def csv_dashboard():
    """
    Endpoint to render the csv backend
    :return: html page of the csv backend.
    """
    if not current_app.config.get('SHEET_IMPORT'):
        return HTTPResponse.NOT_FOUND
    return render_template('admin/csv-dashboard.html')


@admin.post('/api/csv/upload')
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


@admin.delete('/api/csv/upload/')
@roles_required('Admin')
def api_local_csv_delete():
    """
    API endpoint for removing files ::
    :return:  success if file is removed
    keeping uploaded sheets for now, used as a handler for http calls from filepond for now.
    """
    return ''


@admin.post('/api/csv/analyze')
@roles_required('Admin')
def api_csv_analyze():
    # locate file
    filename = request.json.get('file').get('filename')
    import_dir = Path(current_app.config.get('IMPORT_DIR'))

    filepath = (import_dir / filename).as_posix()
    su = SheetUtils(filepath)
    result = su.parse_sheet()
    # print(Bulletin.get_columns())
    # result['fields'] = Bulletin.get_columns()
    if result:
        return json.dumps(result)
    else:
        return 'Problem parsing sheet file', 417


# Excel sheet selector
@admin.post('/api/xls/sheets')
@roles_required('Admin')
def api_xls_sheet():
    filename = request.json.get('file').get('filename')
    import_dir = Path(current_app.config.get('IMPORT_DIR'))

    filepath = (import_dir / filename).as_posix()
    su = SheetUtils(filepath)
    sheets = su.get_sheets()
    # print(Bulletin.get_columns())
    # result['fields'] = Bulletin.get_columns()
    return json.dumps(sheets)


@admin.post('/api/xls/analyze')
@roles_required('Admin')
def api_xls_analyze():
    # locate file
    filename = request.json.get('file').get('filename')
    import_dir = Path(current_app.config.get('IMPORT_DIR'))

    filepath = (import_dir / filename).as_posix()
    su = SheetUtils(filepath)
    sheet = request.json.get('sheet')
    result = su.parse_xsheet(sheet)

    # print(result['head'])
    # print(Bulletin.get_columns())
    # result['fields'] = Bulletin.get_columns()
    if result:
        return Response(json.dumps(result, sort_keys=False), content_type='application/json'), 200
    else:
        return 'Problem parsing sheet file', 417


# Saved Searches
@admin.route('/api/mappings/')
def api_mappings():
    """
    Endpoint to get sheet mappings
    :return: successful json feed of mappings or error
    """
    mappings = Mapping.query.all()
    return json.dumps([map.to_dict() for map in mappings]), 200


@admin.post('/api/mapping/')
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

        map.save()
        return {'message': F'Mapping saved successfully - Mapping ID : {map.id}', 'id': map.id}, 200
    else:
        return 'Error saving mapping data', 417


@admin.put('/api/mapping/<int:id>')
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
            map.save()
            return {'message': F'Mapping saved successfully - Mapping ID : {map.id}', 'id': map.id}, 200
        else:
            return "Update request missing parameters data", 417

    else:
        return HTTPResponse.NOT_FOUND


@admin.post('/api/process-sheet')
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
    batch_id = request.json.get('batch')
    sheet = request.json.get('sheet')
    lang = request.json.get('lang', 'en')
    actor_config = request.json.get('actorConfig')
    roles = request.json.get('roles')

    for filename in files:
        filepath = (import_dir / filename).as_posix()
        target = request.json.get('target')
        process_sheet.delay(filepath, map, 'actor', batch_id, vmap, sheet, actor_config, lang, roles)

    return F'Import process queued successfully! batch id: {batch_id}', 200


@admin.get('/api/logs')
@roles_accepted('Admin')
def api_logs():
    """
    API Endpoint to provide status updates for a given sheet import batch id
    """
    batch_id = request.args.get('batch')
    logs = Log.query.filter(Log.tag == batch_id).all()
    logs = [log.to_dict() for log in logs]

    return Response(json.dumps(logs), content_type='application/json'), 200


@admin.get('/system-administration/')
@roles_accepted('Admin')
def system_admin():
    """Endpoint for system administration."""
    return render_template('admin/system-administration.html')


