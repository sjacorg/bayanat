# -*- coding: utf-8 -*-
import click
from flask import Blueprint, render_template, Response, request
from flask.cli import with_appcontext

from enferno.deduplication.models import DedupRelation
from enferno.extensions import db
from flask_security import roles_required
import json
import pandas as pd

deduplication = Blueprint('deduplication', __name__, static_folder='../static', template_folder='../deduplication/templates', cli_group=None)

@deduplication.app_context_processor
def deduplication_app_context():
    """
    pass a global flag to indicate that the deduplciation plugin(Blueprint) is enabled.
    used to display/hide deduplication menu item inside templates
    :return: True if this blueprint is registered
    """
    return {
        'deduplication': True
    }


@deduplication.route('/deduplication/dashboard/')
@roles_required('Admin')
def deduplication_dash():
    """
    Endpoint for rendering deduplication dashboard page
    """
    return render_template('deduplication.html')





@deduplication.route('/api/deduplication/')
@roles_required('Admin')
def api_deduplication():
    """
    Provides APIs for imported deduplication CSV data, supports paging
    """
    page = request.args.get('page',1,int)
    per_page = request.args.get('per_page',1000,int)
    data = DedupRelation.query.paginate(page, per_page)
    items = data.items
    total = data.total
    items = [item.to_dict() for item in items]
    response = {'items': items, 'perPage': per_page, 'total': total}
    return Response(json.dumps(response), content_type='application/json'),200


@deduplication.route('/api/deduplication/process',methods=['POST'])
@roles_required('Admin')
def api_process():
    """
    Endpoint used to process all deduplication data
    """
    items = DedupRelation.query.all()
    for item in items:
        if not item.status:
            item.process()
    # commit once after all processing is done
    db.session.commit()
    return 'Success', 200

'''
@deduplication.route('/api/deduplication/clear',methods=['DELETE'])
@roles_required('Admin')
def api_clear():
    """
    API Endpoint to clear all deduplication Data
    """
    try:
        DedupRelation.query.delete()
        db.session.commit()
        return 'Data cleared', 200
    except Exception as e:
        print (e)
        return 'Error clearing deduplication data'
'''

@deduplication.cli.command()
@click.argument('file', type=click.File('r'))
@click.option('-r', '--remove', is_flag=True, prompt='Are you sure you want to remove existing data?')
@with_appcontext
def dedup_import(file, remove):
    """imports data from deduplication compatible file, with an option to clear existing data """
    if remove:
        DedupRelation.query.delete()
        db.session.commit()
        print ('cleared all existing data')

    #create pandas data frame
    df = pd.read_csv(file)
    records = df.to_dict(orient='records')
    for item in records:
        br = DedupRelation()
        br.query_video = item.get('query_video')
        br.match_video = item.get('match_video')
        br.distance = item.get('distance')
        br.notes = item.get('notes')
        br.save()
        print ('imported item {}'.format(br.id))
    print ('=== Done ===')

