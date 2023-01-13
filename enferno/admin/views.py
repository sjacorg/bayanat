import hashlib
import os
from pathlib import Path
from uuid import uuid4

import boto3
import passlib
import shortuuid
from flask import request, abort, Response, Blueprint, current_app, json, g, session, send_from_directory
from flask.templating import render_template
from flask_bouncer import requires
from flask_security.decorators import roles_required, login_required, current_user, roles_accepted
from flask_security.utils import hash_password
from sqlalchemy import desc, or_, text
from sqlalchemy.orm.attributes import flag_modified

from enferno.admin.models import (Bulletin, Label, Source, Location, Eventtype, Media, Actor, Incident,
                                  IncidentHistory, BulletinHistory, ActorHistory, LocationHistory, PotentialViolation, ClaimedViolation,
                                  Activity, Query, Mapping, Log, APIKey, LocationAdminLevel, LocationType)
from enferno.extensions import bouncer, rds, babel
from enferno.extensions import cache
from enferno.tasks import bulk_update_bulletins, bulk_update_actors, bulk_update_incidents, etl_process_file, \
    process_sheet
from enferno.user.models import User, Role
from enferno.utils.search_utils import SearchUtils
from enferno.utils.sheet_utils import SheetUtils

root = os.path.abspath(os.path.dirname(__file__))
admin = Blueprint('admin', __name__,
                  template_folder=os.path.join(root, 'templates'),
                  static_folder=os.path.join(root, 'static'),
                  url_prefix='/admin')

# default global items per page
PER_PAGE = 30
REL_PER_PAGE = 5


@babel.localeselector
def get_locale():
    """
    Sets the system global language.
    :return: system language from the current session.
    """
    # override = request.args.get('lang')
    # if override:
    #     session['lang'] = override
    try:
        default = current_app.config.get('DEFAULT_LANGUAGE')
    except Exception as e:
        print(e)
        default = 'en'
    if not current_user.is_authenticated:
        # will return default language
        pass
    else:
        if current_user.settings:
            if current_user.settings.get('language'):
                session['lang'] = current_user.settings.get('language')
    return session.get('lang', default)


@admin.before_request
@login_required
def before_request():
    """
    Attaches the user object to all requests
    and a version number that is used to clear the static files cache globally.
    :return: None
    """
    g.user = current_user
    g.version = '4'


@admin.app_context_processor
def ctx():
    """
    passes all users to the application, based on the current user's permissions.
    :return: None
    """
    users = User.query.order_by(User.username).all()
    if current_user.is_authenticated:
        if current_user.has_role('Admin') or current_user.view_usernames:
            hide_name = False
        else:
            hide_name = True
        users = [u.to_dict(hide_name=hide_name) for u in users]
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
    :param page: db query offset
    :return: json response of label objects.
    """
    query = []
    q = request.args.get('q', None)

    if q:
        words = q.split(' ')
        query.extend([Label.title.ilike('%{}%'.format(word)) for word in words])

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
            page, per_page, True)
    else:
        result = Label.query.filter(*query).paginate(page, per_page, True)

    response = {'items': [item.to_dict(request.args.get('mode', 1)) for item in result.items], 'perPage': per_page,
                'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json')


@admin.route('/api/label/', methods=['POST'])
@roles_accepted('Admin', 'Mod')
def api_label_create():
    """
    Endpoint to create a label.
    :return: success/error based on the operation result.
    """
    if request.method == 'POST':
        label = Label()
        created = label.from_json(request.json['item'])
        if created.save():
            return 'Created Label #{}'.format(label.id)
        else:
            return 'Save Failed', 417


@admin.route('/api/label/<int:id>', methods=['PUT'])
@roles_accepted('Admin', 'Mod')
def api_label_update(id):
    """
    Endpoint to update a label.
    :param id: id of the label
    :return: success/error based on the operation result.
    """
    if request.method == 'PUT':
        label = Label.query.get(id)
        if label is not None:
            label = label.from_json(request.json['item'])
            label.save()
            return 'Saved Label #{}'.format(label.id), 200
        else:
            return 'Not Found!', 404

    else:
        return 'Unauthorized', 403


@admin.route('/api/label/<int:id>', methods=['DELETE'])
@roles_required('Admin')
def api_label_delete(id):
    """
    Endpoint to delete a label.
    :param id: id of the label
    :return: Success/error based on operation's result.
    """
    if request.method == 'DELETE':
        label = Label.query.get(id)
        label.delete()
        return 'Deleted Label #{}'.format(label.id)
    else:
        return 'Error', 417


@admin.route('/api/label/import/', methods=['POST'])
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
    :param page: db query offset
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
        *query).order_by(Eventtype.id).paginate(
        page, per_page, True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': per_page, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json')


@admin.route('/api/eventtype/', methods=['POST'])
@roles_accepted('Admin', 'Mod')
def api_eventtype_create():
    """
    Endpoint to create an Event Type
    :return: Success/Error based on operation's result
    """
    if request.method == 'POST':
        eventtype = Eventtype()
        created = eventtype.from_json(request.json['item'])
        if created.save():
            return 'Created Event #{}'.format(eventtype.id)
        else:
            return 'Save Failed', 417


@admin.route('/api/eventtype/<int:id>', methods=['PUT'])
@roles_accepted('Admin', 'Mod')
def api_eventtype_update(id):
    """
    Endpoint to update an Event Type
    :param id: id of the item to be updated
    :return: success/error based on the operation's result
    """
    if request.method == 'PUT':
        eventtype = Eventtype.query.get(id)
        if eventtype is not None:
            eventtype = eventtype.from_json(request.json['item'])
            eventtype.save()
            return 'Saved Event #{}'.format(eventtype.id), 200
        else:
            return 'Not Found!', 404

    else:
        return 'Unauthorized', 403


@admin.route('/api/eventtype/<int:id>', methods=['DELETE'])
@roles_required('Admin')
def api_eventtype_delete(id):
    """
    Endpoint to delete an event type
    :param id: id of the item
    :return: success/error based on the operation's result
    """
    if request.method == 'DELETE':
        eventtype = Eventtype.query.get(id)
        eventtype.delete()
        return 'Deleted Event #{}'.format(eventtype.id)
    else:
        return 'Error', 417


@admin.route('/api/eventtype/import/', methods=['POST'])
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
        *query).order_by(PotentialViolation.id).paginate(
        page, PER_PAGE, True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': PER_PAGE, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json')


@admin.route('/api/potentialviolation/', methods=['POST'])
@roles_accepted('Admin', 'Mod')
def api_potentialviolation_create():
    """
    Endpoint to create a potential violation
    :return: success/error based on operation's result
    """
    if request.method == 'POST':
        potentialviolation = PotentialViolation()
        created = potentialviolation.from_json(request.json['item'])
        if created.save():
            return 'Created Potential Violation #{}'.format(potentialviolation.id)
        else:
            return 'Save Failed', 417


@admin.route('/api/potentialviolation/<int:id>', methods=['PUT'])
@roles_accepted('Admin', 'Mod')
def api_potentialviolation_update(id):
    """
    Endpoint to update a potential violation
    :param id: id of the item to be updated
    :return: success/error based on the operation's result
    """
    if request.method == 'PUT':
        potentialviolation = PotentialViolation.query.get(id)
        if potentialviolation is not None:
            potentialviolation = potentialviolation.from_json(request.json['item'])
            potentialviolation.save()
            return 'Saved Potential Violation #{}'.format(potentialviolation.id), 200
        else:
            return 'Not Found!', 404

    else:
        return 'Unauthorized', 403


@admin.route('/api/potentialviolation/<int:id>', methods=['DELETE'])
@roles_required('Admin')
def api_potentialviolation_delete(id):
    """
    Endpoint to delete a potential violation
    :param id: id of the item to delete
    :return: success/error based on the operation's result
    """
    if request.method == 'DELETE':
        potentialviolation = PotentialViolation.query.get(id)
        potentialviolation.delete()
        return 'Deleted Potential Violation #{}'.format(potentialviolation.id)
    else:
        return 'Error', 417


@admin.route('/api/potentialviolation/import/', methods=['POST'])
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
        *query).order_by(ClaimedViolation.id).paginate(
        page, PER_PAGE, True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': PER_PAGE, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json')


@admin.route('/api/claimedviolation/', methods=['POST'])
@roles_accepted('Admin', 'Mod')
def api_claimedviolation_create():
    """
    Endpoint to create a claimed violation
    :return: success / error based on operation's result
    """
    if request.method == 'POST':
        claimedviolation = ClaimedViolation()
        created = claimedviolation.from_json(request.json['item'])
        if created.save():
            return 'Created Claimed Violation #{}'.format(claimedviolation.id)
        else:
            return 'Save Failed', 417


@admin.route('/api/claimedviolation/<int:id>', methods=['PUT'])
@roles_accepted('Admin', 'Mod')
def api_claimedviolation_update(id):
    """
    Endpoint to update a claimed violation
    :param id: id of the item to update
    :return: success/error based on operation's result
    """
    if request.method == 'PUT':
        claimedviolation = ClaimedViolation.query.get(id)
        if claimedviolation is not None:
            claimedviolation = claimedviolation.from_json(request.json['item'])
            claimedviolation.save()
            return 'Saved Claimed Violation #{}'.format(claimedviolation.id), 200
        else:
            return 'Not Found!', 404

    else:
        return 'Unauthorized', 403


@admin.route('/api/claimedviolation/<int:id>', methods=['DELETE'])
@roles_required('Admin')
def api_claimedviolation_delete(id):
    """
    Endpoint to delete a claimed violation
    :param id: id of the item to delete
    :return: success/ error based on operation's result
    """
    if request.method == 'DELETE':
        claimedviolation = ClaimedViolation.query.get(id)
        claimedviolation.delete()
        return 'Deleted Claimed Violation #{}'.format(claimedviolation.id)


@admin.route('/api/claimedviolation/import/', methods=['POST'])
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
    :param page: db query offset
    :return: json feed of sources or error code based on operation's result
    """
    query = []
    q = request.args.get('q', None)

    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)

    if q is not None:
        words = q.split(' ')
        query.extend([Source.title.ilike('%{}%'.format(word)) for word in words])

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
            page, per_page, True)
    else:
        result = Source.query.filter(*query).paginate(
            page, per_page, True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': per_page, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


@admin.route('/api/source/', methods=['POST'])
@roles_accepted('Admin', 'Mod')
def api_source_create():
    """
    Endpoint to create a source
    :return: success/error based on operation's result
    """
    if request.method == 'POST':
        source = Source()
        created = source.from_json(request.json['item'])
        if created.save():
            return 'Created Source #{}'.format(source.id)
        else:
            return 'Save Failed', 417


@admin.route('/api/source/<int:id>', methods=['PUT'])
@roles_accepted('Admin', 'Mod')
def api_source_update(id):
    """
    Endpoint to update a source
    :param id: id of the item to update
    :return: success/error based on the operation's result
    """
    if request.method == 'PUT':
        source = Source.query.get(id)
        if source is not None:
            source = source.from_json(request.json['item'])
            source.save()
            return 'Saved Source #{}'.format(source.id), 200
        else:
            return 'Not Found!', 404

    else:
        return 'Unauthorized', 403


@admin.route('/api/source/<int:id>', methods=['DELETE'])
@roles_required('Admin')
def api_source_delete(id):
    """
    Endopint to delete a source item
    :param id: id of the item to delete
    :return: success/error based on operation's result
    """
    if request.method == 'DELETE':
        source = Source.query.get(id)
        source.delete()
        return 'Deleted Source #{}'.format(source.id)


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

    result = Location.query.filter(*query).order_by(Location.id).paginate(
        page, per_page, True)
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
        return 'Created Location #{}'.format(location.id)



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
            return 'Saved Location #{}'.format(location.id), 200
        else:
            return 'Save Failed', 417
    else:
        return 'Not Found!', 404




@admin.route('/api/location/<int:id>', methods=['DELETE'])
@roles_required('Admin')
def api_location_delete(id):
    """Endpoint for deleting locations. """

    if request.method == 'DELETE':
        location = Location.query.get(id)
        location.delete()
        return 'Deleted Location #{}'.format(location.id)


@admin.route('/api/location/import/', methods=['POST'])
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

    if not location:
        abort(404)
    else:
        return json.dumps(location.to_dict()), 200


# location admin level endpoints
@admin.route('/api/location-admin-levels/', methods=['GET', 'POST'])
def api_location_admin_levels():
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)

    query = []
    result = LocationAdminLevel.query.filter(
        *query).order_by(-LocationAdminLevel.id).paginate(
        page, per_page, True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': per_page, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json')


@admin.post('/api/location-admin-level')
@roles_required('Admin')
def api_location_admin_level_create():
    admin_level = LocationAdminLevel()
    admin_level.from_json(request.json['item'])

    if admin_level.save():
        return f'Item created successfully ID ${admin_level.id} !', 200
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
        return 'Not Found!', 404


# location type endpoints
@admin.route('/api/location-types/', methods=['GET', 'POST'])
def api_location_types():
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)

    query = []
    result = LocationType.query.filter(
        *query).order_by(-LocationType.id).paginate(
        page, per_page, True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': per_page, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json')


@admin.post('/api/location-type')
@roles_required('Admin')
def api_location_type_create():
    location_type = LocationType()
    location_type.from_json(request.json['item'])

    if location_type.save():
        return f'Item created successfully ID ${location_type.id} !', 200
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
        return 'Not Found!', 404


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
        return 'Location Type Deleted #{}'.format(location_type.id), 200
        # Record Activity
        Activity.create(current_user, Activity.ACTION_DELETE, location_type.to_mini(), 'location_type')
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

    nested = False
    if len(queries) > 0:
        nested = True
        while queries:
            nextOp = ops.pop(0)
            nextQuery = queries.pop(0)
            if nextOp == 'union':
                result = result.union(Bulletin.query.filter(*nextQuery))
            elif nextOp == 'intersect':
                result = result.intersect(Bulletin.query.filter(*nextQuery))
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)
    # handle sort
    # default
    sort = '-Bulletin.id'

    options = request.json.get('options')
    if options:
        sort_by = options.get('sortBy')
        sort_desc = options.get('sortDesc')
        if sort_by:
            sort = sort_by[0]
            if sort_desc and sort_desc[0]:
                sort = '{} desc'.format(sort)

    # can't sort nested queries
    if nested:
        result = result.paginate(page, per_page, True)
    else:
        result = result.order_by(text(sort)).paginate(page, per_page, True)

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
    return 'Created Bulletin #{}'.format(bulletin.id)


@admin.route('/api/bulletin/<int:id>', methods=['PUT'])
@roles_accepted('Admin', 'DA')
def api_bulletin_update(id):
    """Updates a bulletin."""

    if request.method == 'PUT':
        bulletin = Bulletin.query.get(id)
        if bulletin is not None:
            bulletin = bulletin.from_json(request.json['item'])
            # Create a revision using latest values
            # this method automatically commits
            # bulletin changes (referenced)           
            bulletin.create_revision()

            # Record Activity
            Activity.create(current_user, Activity.ACTION_UPDATE, bulletin.to_mini(), 'bulletin')
            return 'Saved Bulletin #{}'.format(bulletin.id), 200
        else:
            return 'Not Found!', 404

    else:
        return 'Unauthorized', 403


# Add/Update review bulletin endpoint
@admin.route('/api/bulletin/review/<int:id>', methods=['PUT'])
@roles_accepted('Admin', 'DA')
def api_bulletin_review_update(id):
    """
    Endpoint to update a bulletin review
    :param id: id of the bulletin
    :return: success/error based on the outcome
    """
    if request.method == 'PUT':
        bulletin = Bulletin.query.get(id)
        if bulletin is not None:
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

            # Create a revision using latest values
            # this method automatically commits
            #  bulletin changes (referenced)           
            bulletin.create_revision()

            # Record Activity
            Activity.create(current_user, Activity.ACTION_UPDATE, bulletin.to_mini(), 'bulletin')
            return 'Bulletin review updated #{}'.format(bulletin.id), 200
        else:
            return 'Not Found!', 404

    else:
        return 'Unauthorized', 403


# bulk update bulletin endpoint
@admin.route('/api/bulletin/bulk/', methods=['PUT'])
@roles_accepted('Admin', 'Mod')
def api_bulletin_bulk_update():
    """
    Endpoint to bulk update bulletins
    :return: success / error
    """
    if request.method == 'PUT':
        ids = request.json['items']
        bulk = request.json['bulk']

        if ids and len(bulk):
            job = bulk_update_bulletins.delay(ids, bulk, current_user.id)
            # store job id in user's session for status monitoring
            key = 'user{}:{}'.format(current_user.id, job.id)
            rds.set(key, job.id)
            # expire in 3 hour
            rds.expire(key, 60 * 60 * 3)
            return '{}'.format('Bulk update queued successfully.'), 200
        else:
            return 'No items selected, or nothing to update', 417

    else:
        return 'Unauthorized', 403


'''
@admin.route('/api/bulletin/<int:id>', methods=['DELETE'])
@roles_required('Admin')
def api_bulletin_delete(id):
    """
    Endpoint to delete a bulletin
    :param id: id of the bulletin to be deleted
    :return: success/error
    """
    if request.method == 'DELETE':
        bulletin = Bulletin.query.get(id)
        bulletin.delete()

        # Record Activity
        Activity.create(current_user, Activity.ACTION_DELETE, bulletin.to_mini(), 'bulletin')
        return 'Deleted!'
'''


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
        abort(404)
    else:
        # hide review from view-only users
        if not current_user.roles:
            bulletin.review = None
        return json.dumps(bulletin.to_dict(mode)), 200


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
        abort(404)
    bulletin = Bulletin.query.get(id)
    if not bulletin:
        abort(404)
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
        return 'Saved Bulletin #{}'.format(bulletin.id), 200
    else:
        abort(404)


@admin.route('/api/actor/assign/<int:id>', methods=['PUT'])
@roles_accepted('Admin', 'DA')
def api_actor_self_assign(id):
    """ self assign an actor to the user"""

    # permission check
    if not current_user.can_self_assign:
        return 'User not allowed to self assign', 400

    actor = Actor.query.get(id)
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
        return 'Saved Actor #{}'.format(actor.id), 200
    else:
        abort(404)


@admin.route('/api/incident/assign/<int:id>', methods=['PUT'])
@roles_accepted('Admin', 'DA')
def api_incident_self_assign(id):
    """ self assign an incident to the user"""

    # permission check
    if not current_user.can_self_assign:
        return 'User not allowed to self assign', 400

    incident = Incident.query.get(id)
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
        return 'Saved Actor #{}'.format(incident.id), 200
    else:
        abort(404)


# Media special endpoints
@admin.route('/api/media/upload/', methods=['POST'])
@roles_accepted('Admin', 'DA')
def api_medias_upload():
    """
    Endpoint to upload files (based on file system settings : s3 or local file system)
    :return: success /error based on operation's result
    """

    if 'media' in request.files:
        if current_app.config['FILESYSTEM_LOCAL'] or (
                'etl' in request.referrer and not current_app.config['FILESYSTEM_LOCAL']):
            return api_local_medias_upload(request)
        else:

            s3 = boto3.resource('s3', aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
                                aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'])

            f = request.files.get('media')

            # final file
            filename = Media.generate_file_name(f.filename)
            # filepath = (Media.media_dir/filename).as_posix()

            response = s3.Bucket(current_app.config['S3_BUCKET']).put_object(Key=filename, Body=f)
            # print(response.get())
            etag = response.get()['ETag'].replace('"', '')

            # check if file already exists
            if Media.query.filter(Media.etag == etag).first():
                return 'Error: File already exists', 409

            return json.dumps({'filename': filename, 'etag': etag}), 200

    return 'Invalid request params', 417


''' #File delete is disabled for now 
@admin.route('/api/media/upload/', methods=['DELETE'])
@roles_required('Admin')
def api_media_file_delete():
    """
    Endpoint to handle file deletions
    :return: success/error
    """
    data = request.get_json(force=True)
    try:
        os.remove((Media.media_dir / data['filename']).as_posix())
        return 'Removed', 200
    except Exception as e:
        print(str(e))
        return 'Error', 417
'''


# return signed url from s3 valid for some time
@admin.route('/api/media/<filename>')
def serve_media(filename):
    """
    Endpoint to generate  file urls to be served (based on file system type)
    :param filename: name of the file
    :return: temporarily accesssible url of the file
    """

    if current_app.config['FILESYSTEM_LOCAL']:
        return '/admin/api/serve/media/{}'.format(filename)
    else:
        s3 = boto3.client('s3',
                          aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
                          aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
                          region_name=current_app.config['AWS_REGION']
                          )
        params = {'Bucket': current_app.config['S3_BUCKET'], 'Key': filename}
        if filename.lower().endswith('pdf'):
            params['ResponseContentType'] = 'application/pdf'
        url = s3.generate_presigned_url('get_object', Params=params, ExpiresIn=36000)
        return url


def api_local_medias_upload(request):
    # file pond sends multiple requests for multiple files (handle each request as a separate file )
    try:
        f = request.files.get('media')
        # final file
        filename = Media.generate_file_name(f.filename)
        filepath = (Media.media_dir / filename).as_posix()
        f.save(filepath)
        # get md5 hash
        f = open(filepath, 'rb').read()
        etag = hashlib.md5(f).hexdigest()
        # check if file already exists
        if Media.query.filter(Media.etag == etag).first():
            return 'Error: File already exists', 409

        response = {'etag': etag, 'filename': filename}

        return Response(json.dumps(response), content_type='application/json'), 200
    except Exception as e:
        return 'Problem uploading file: {}'.format(e), 417


@admin.route('/api/serve/media/<filename>')
def api_local_serve_media(filename):
    """
    serves file from local file system
    """
    return send_from_directory('media', filename)

@admin.post('/api/inline/upload')
def api_inline_medias_upload():
    # file pond sends multiple requests for multiple files (handle each request as a separate file )
    try:
        f = request.files.get('file')

        # final file
        filename = Media.generate_file_name(f.filename)
        filepath = (Media.inline_dir / filename).as_posix()
        f.save(filepath)
        # get md5 hash
        #f = open(filepath, 'rb').read()
        #etag = hashlib.md5(f).hexdigest()
        # check if file already exists
        #if Media.query.filter(Media.etag == etag).first():
        #    return 'Error: File already exists', 409
        #response = {'etag': etag, 'filename': filename}
        response = {'location': filename}

        return Response(json.dumps(response), content_type='application/json'), 200
    except Exception as e:
        return 'Problem uploading file: {}'.format(e), 417

@admin.route('/api/serve/inline/<filename>')
def api_local_serve_inline_media(filename):
    """
    serves inline media files - only for authenticated users
    """
    return send_from_directory('media/inline', filename)


# Medias routes

@admin.route('/api/medias/', defaults={'page': 1})
@admin.route('/api/medias/<int:page>/')
def api_medias(page):
    """
    Endopint to feed json data of media items , supports paging and search
    :param page: db query offset
    :return: success + json feed or error in case of failure
    """
    query = []
    q = request.args.get('q', None)
    if q is not None:
        search = '%' + q.replace(' ', '%') + '%'
        query.append(
            Media.search.ilike(search)
        )
    result = Media.query.filter(
        *query).order_by(Media.id).paginate(
        page, PER_PAGE, True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': PER_PAGE, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json')


@admin.route('/api/media/', methods=['POST'])
@roles_accepted('Admin', 'DA')
def api_media_create():
    """
    Endpoint to create a media item
    :return: success / error
    """
    if request.method == 'POST':
        media = Media()
        created = media.from_json(request.json['item'])
        if created.save():
            return 'Created!'
        else:
            return 'Save Failed', 417


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
            return 'Not Found!', 404

    else:
        return 'Unauthorized', 403


@admin.route('/api/media/<int:id>', methods=['DELETE'])
@roles_required('Admin')
def api_media_delete(id):
    """
    Endpoint to handle media deletion
    :param id: id of the media to be deleted
    :return: success / error
    """
    if request.method == 'DELETE':
        media = Media.query.get(id)
        media.delete()
        return 'Deleted!'


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
    result = result.order_by(Actor.id.desc()).paginate(
        page, per_page, True)
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
        return 'Created Actor #{}'.format(actor.id)
    else:
        return 'Error creating actor', 417


# update actor endpoint
@admin.route('/api/actor/<int:id>', methods=['PUT'])
@roles_accepted('Admin', 'DA')
def api_actor_update(id):
    """
    Endpoint to update an Actor item
    :param id: id of the actor to be updated
    :return: success/error
    """

    actor = Actor.query.get(id)
    if not actor:
        abort(404)

    actor = actor.from_json(request.json['item'])
    # Create a revision using latest values
    # this method automatically commits
    #  actor changes (referenced)
    result = actor.save()
    if result:
        actor.create_revision()
        # Record Activity
        Activity.create(current_user, Activity.ACTION_UPDATE, actor.to_mini(), 'actor')
        return 'Saved Actor #{}'.format(actor.id), 200
    else:
        return 'Error saving actor', 417


# Add/Update review actor endpoint
@admin.route('/api/actor/review/<int:id>', methods=['PUT'])
@roles_accepted('Admin', 'DA')
def api_actor_review_update(id):
    """
    Endpoint to update an Actor's review item
    :param id: id of the actor
    :return: success/error
    """
    if request.method == 'PUT':
        actor = Actor.query.get(id)
        if actor is not None:
            actor.review = request.json['item']['review'] if 'review' in request.json['item'] else ''
            actor.review_action = request.json['item']['review_action'] if 'review_action' in request.json[
                'item'] else ''

            actor.status = 'Peer Reviewed'

            # Create a revision using latest values
            # this method automatically commi
            #  bulletin changes (referenced)           
            actor.create_revision()

            # Record activity
            Activity.create(current_user, Activity.ACTION_UPDATE, actor.to_mini(), 'actor')
            return 'Actor review updated #{}'.format(actor.id), 200
        else:
            return 'Not Found!', 404

    else:
        return 'Unauthorized', 403


# bulk update actor endpoint
@admin.route('/api/actor/bulk/', methods=['PUT'])
@roles_accepted('Admin', 'Mod')
def api_actor_bulk_update():
    """
    Endpoint to bulk update actors
    :return: success/error
    """
    if request.method == 'PUT':
        ids = request.json['items']
        bulk = request.json['bulk']
        if ids and len(bulk):
            job = bulk_update_actors.delay(ids, bulk, current_user.id)
            # store job id in user's session for status monitoring
            key = 'user{}:{}'.format(current_user.id, job.id)
            rds.set(key, job.id)
            # expire in 3 hour
            rds.expire(key, 60 * 60 * 3)
            return '{}'.format('Bulk update queued successfully.'), 200
        else:
            return 'No items selected, or nothing to update', 417

    else:
        return 'Unauthorized', 403


'''
@roles_required('Admin')
@admin.route('/api/actor/<int:id>', methods=['DELETE'])
def api_actor_delete(id):
    """
    Endpoint to delete an actor
    :param id: id of the actor to be deleted
    :return: success/error
    """
    if request.method == 'DELETE':
        actor = Actor.query.get(id)
        actor.delete()
        # Record activity
        Activity.create(current_user, Activity.ACTION_DELETE, actor.to_mini(), 'actor')
        return 'Deleted!'
'''


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
        abort(404)
    else:
        mode = request.args.get('mode', None)
        return json.dumps(actor.to_dict(mode=mode)), 200


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
        abort(404)
    actor = Actor.query.get(id)
    if not actor:
        abort(404)
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
            abort(404)
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
                    content_type='application/json')


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
                    content_type='application/json')


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
                    content_type='application/json')

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
                    content_type='application/json')

# user management routes

@admin.route('/api/users/')
@roles_accepted('Admin', 'Mod')
def api_users():
    """
    API endpoint to feed users data in json format , supports paging and search
    :param page: db query offset
    :return: success and json feed of items or error
    """
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)
    q = request.args.get('q')
    query = []
    if q is not None:
        query.append(User.name.ilike('%' + q + '%'))
    result = User.query.filter(
        *query).order_by(User.username).paginate(
        page, per_page, True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': per_page, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json')


@admin.route('/users/')
@roles_required('Admin')
def users():
    """
    Endpoint to render the users backend page
    :return: html page of the users backend.
    """
    return render_template('admin/users.html')


@admin.route('/api/user/', methods=['POST'])
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
    if exists:
        return 'Error, username already exists', 417
    user = User()
    user.fs_uniquifier = uuid4().hex
    user.from_json(u)
    result = user.save()
    if result:
        # Record activity
        Activity.create(current_user, Activity.ACTION_CREATE, user.to_mini(), 'user')
        return 'User {} has been created successfully'.format(username), 200
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


@admin.route('/api/user/<int:uid>', methods=['PUT'])
@roles_required('Admin')
def api_user_update(uid):
    """Endpoint to update a user."""
    if request.method == 'PUT':
        user = User.query.get(uid)
        if user is not None:
            # set password only if user updated it 
            if len(request.json['item']['password']) > 0:
                user.password = hash_password(request.json['item']['password'])
            user.active = request.json['item']['active']
            if 'roles' in request.json['item']:
                role_ids = [r['id'] for r in request.json['item']['roles']]
                roles = Role.query.filter(Role.id.in_(role_ids)).all()
                user.roles = roles
            user.view_usernames = request.json['item']['view_usernames']
            user.view_simple_history = request.json['item']['view_simple_history']
            user.view_full_history = request.json['item']['view_full_history']
            user.can_self_assign = request.json['item'].get('can_self_assign', False)
            user.can_edit_locations = request.json['item'].get('can_edit_locations', False)
            user.name = request.json['item']['name']
            email = request.json.get('item').get('email')
            if email:
                user.email = email
            else:
                user.email = None
            user.save()

            # Record activity
            Activity.create(current_user, Activity.ACTION_UPDATE, user.to_mini(), 'user')
            return 'Success.', 200
        else:
            return 'Not Found!', 404

    else:
        return 'Error', 417


@admin.route('/api/user/<int:id>', methods=['DELETE'])
@roles_required('Admin')
def api_user_delete(id):
    """
    Endpoint to delete a user
    :param id: id of the user to be deleted
    :return: success/error
    """
    if request.method == 'DELETE':
        user = User.query.get(id)
        user.delete()

        # Record activity
        Activity.create(current_user, Activity.ACTION_DELETE, user.to_mini(), 'user')
        return 'Deleted!'


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
            Role.title.ilike('%' + q + '%')
        )
    result = Role.query.filter(
        *query).order_by(Role.id).paginate(
        page, PER_PAGE, True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': PER_PAGE, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json')


@admin.route('/api/role/', methods=['POST'])
@roles_required('Admin')
def api_role_create():
    """
    Endpoint to create a role item
    :return: success/error
    """
    if request.method == 'POST':
        role = Role()
        created = role.from_json(request.json['item'])
        if created.save():
            # Record activity
            Activity.create(current_user, Activity.ACTION_CREATE, role.to_mini(), 'user')
            return 'Created!'

        else:
            return 'Save Failed', 417


@admin.route('/api/role/<int:id>', methods=['PUT'])
@roles_required('Admin')
def api_role_update(id):
    """
    Endpoint to update a role item
    :param id: id of the role to be updated
    :return: success / error
    """
    if request.method == 'PUT':
        role = Role.query.get(id)
        if role is not None:
            role = role.from_json(request.json['item'])
            role.save()
            # Record activity
            Activity.create(current_user, Activity.ACTION_UPDATE, role.to_mini(), 'user')
            return 'Saved!', 200
        else:
            return 'Not Found!', 404

    else:
        return 'Unauthorized', 403


@admin.route('/api/role/<int:id>', methods=['DELETE'])
@roles_required('Admin')
def api_role_delete(id):
    """
    Endpoint to delete a role item
    :param id: id of the role to be deleted
    :return: success / error
    """
    if request.method == 'DELETE':
        role = Role.query.get(id)
        role.delete()
        # Record activity
        Activity.create(current_user, Activity.ACTION_DELETE, role.to_mini(), 'user')
        return 'Deleted!'


@admin.route('/api/role/import/', methods=['POST'])
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
        *query).order_by(Incident.id.desc()).paginate(
        page, per_page, True)
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
    return 'Created Incident #{}'.format(incident.id)


# update incident endpoint
@admin.route('/api/incident/<int:id>', methods=['PUT'])
@roles_accepted('Admin', 'DA')
def api_incident_update(id):
    """API endpoint to update an incident."""
    if request.method == 'PUT':
        incident = Incident.query.get(id)
        if incident is not None:
            incident = incident.from_json(request.json['item'])
            # Create a revision using latest values
            # this method automatically commits
            # incident changes (referenced)           
            incident.create_revision()
            # Record activity
            Activity.create(current_user, Activity.ACTION_UPDATE, incident.to_mini(), 'incident')
            return 'Saved Incident #{}'.format(incident.id), 200
        else:
            return 'Not Found!', 404

    else:
        return 'Unauthorized', 403


# Add/Update review incident endpoint
@admin.route('/api/incident/review/<int:id>', methods=['PUT'])
@roles_accepted('Admin', 'DA')
def api_incident_review_update(id):
    """
    Endpoint to update an incident review item
    :param id: id of the incident
    :return: success / error
    """
    if request.method == 'PUT':
        incident = Incident.query.get(id)
        if incident is not None:
            incident.review = request.json['item']['review'] if 'review' in request.json['item'] else ''
            incident.review_action = request.json['item']['review_action'] if 'review_action' in request.json[
                'item'] else ''

            incident.status = 'Peer Reviewed'
            # Create a revision using latest values
            # this method automatically commi
            #  incident changes (referenced)           
            incident.create_revision()
            # Record activity
            Activity.create(current_user, Activity.ACTION_UPDATE, incident.to_mini(), 'incident')
            return 'Bulletin review updated #{}'.format(incident.id), 200
        else:
            return 'Not Found!', 404

    else:
        return 'Unauthorized', 403


# bulk update incident endpoint
@admin.route('/api/incident/bulk/', methods=['PUT'])
@roles_accepted('Admin', 'Mod')
def api_incident_bulk_update():
    """endpoint to handle bulk incidents updates."""
    if request.method == 'PUT':
        ids = request.json['items']
        bulk = request.json['bulk']
        if ids and len(bulk):
            job = bulk_update_incidents.delay(ids, bulk, current_user.id)
            # store job id in user's session for status monitoring
            key = 'user{}:{}'.format(current_user.id, job.id)
            rds.set(key, job.id)
            # expire in 3 hour
            rds.expire(key, 60 * 60 * 3)
            return '{}'.format('Bulk update queued successfully.'), 200
        else:
            return 'No items selected, or nothing to update', 417

    else:
        return 'Unauthorized', 403


'''
@admin.route('/api/incident/<int:id>', methods=['DELETE'])
@roles_required('Admin')
def api_incident_delete(id):
    """endpoint handles deletion of incidents."""
    if request.method == 'DELETE':
        incident = Incident.query.get(id)
        incident.delete()

        # Record activity
        Activity.create(current_user, Activity.ACTION_DELETE, incident.to_mini(), 'incident')
        return 'Deleted!'
'''


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
        abort(404)
    else:
        mode = request.args.get('mode', None)
        return json.dumps(incident.to_dict(mode)), 200


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
        abort(404)
    incident = Incident.query.get(id)
    if not incident:
        abort(404)
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
        *query).order_by(-Activity.id).paginate(
        page, per_page, True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': per_page, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json')


@admin.route('/api/bulk/status/')
def bulk_status():
    """Endpoint to get status update about background bulk operations"""
    uid = current_user.id
    cursor, jobs = rds.scan(0, 'user{}:*'.format(uid), 1000)
    tasks = []
    for key in jobs:
        result = {}
        id = key.split(':')[-1]
        type = request.args.get('type')
        if type == 'bulletin':
            status = bulk_update_bulletins.AsyncResult(id).status
        elif type == 'actor':
            status = bulk_update_incidents.AsyncResult(id).status
        elif type == 'incident':
            status = bulk_update_actors.AsyncResult(id).status
        else:
            abort(404)

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


""" 
# Unused 
@admin.route('/api/key', methods=['POST'])
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

"""


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


@admin.route('/api/query/', methods=['POST'])
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
        abort(404)
    return render_template('admin/etl-dashboard.html')


@admin.route('/etl/status')
@roles_required('Admin')
def etl_status():
    """
    Endpoint to render etl tasks monitoring
    :return: html page of the users backend.
    """
    return render_template('admin/etl-status.html')


@admin.route('/etl/path/', methods=['POST'])
@roles_required('Admin')
def path_process():
    path = request.json.get('path')
    recursive = request.json.get('recursive', False)
    if not path or not os.path.isdir(path):
        return "invalid path specified ", 417
    p = Path(path)

    if recursive:
        items = p.rglob('*')
    else:
        items = p.glob('*')
    files = [str(file) for file in items]

    output = [{'file': {'name': os.path.basename(file), 'path': file}} for file in files]

    return json.dumps(output), 200


@admin.route('/etl/process', methods=['POST'])
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
    open(batch_log, 'a')

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
        abort(404)
    return render_template('admin/csv-dashboard.html')


@admin.post('/api/csv/upload/')
@roles_required('Admin')
def api_local_csv_upload():
    import_dir = Path(current_app.config.get('IMPORT_DIR'))
    # file pond sends multiple requests for multiple files (handle each request as a separate file )
    try:
        f = request.files.get('media')
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
        return 'Problem uploading file: {}'.format(e), 417


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
        return {'message': 'Mapping saved successfully - Mapping ID : {}'.format(map.id), 'id': map.id}, 200
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
            return {'message': 'Mapping saved successfully - Mapping ID : {}'.format(map.id), 'id': map.id}, 200
        else:
            return "Update request missing parameters data", 417

    else:
        abort(404)


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
    actor_config = request.json.get('actorConfig')

    for file in files:
        filename = file.get('filename')
        filepath = (import_dir / filename).as_posix()
        target = request.json.get('target')
        process_sheet.delay(filepath, map, 'actor', batch_id, vmap, sheet, actor_config)

    return 'Import process queued successfully! batch id: {}'.format(batch_id)


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
