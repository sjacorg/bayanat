# -*- coding: utf-8 -*-
import json
from multiprocessing import Pool, cpu_count

import click
import pandas as pd
from flask import Blueprint, render_template, Response, request
from flask.cli import with_appcontext
from flask_security import login_required
from flask_security import roles_required, roles_accepted, current_user

from enferno.deduplication.models import DedupRelation
from enferno.extensions import db, rds

deduplication = Blueprint('deduplication', __name__, static_folder='../static',
                          template_folder='../deduplication/templates', cli_group=None)


@deduplication.before_request
@login_required
def dedup_before_request():
    pass


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
@roles_accepted('Admin', 'MOD')
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
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', 1000, int)
    data = DedupRelation.query.paginate(page, per_page)
    items = data.items
    total = data.total
    items = [item.to_dict() for item in items]
    # calculate the number of unprocessed items , this totally simplifies calculating progress
    pending = DedupRelation.query.filter(DedupRelation.status == 0).count()
    print (pending)
    response = {'items': items, 'perPage': per_page, 'total': total, 'pending': pending}
    return Response(json.dumps(response), content_type='application/json'), 200


@deduplication.route('/api/deduplication/process', methods=['POST'])
@roles_required('Admin')
def api_process():
    """
    Endpoint used to process all deduplication data
    """
    items = DedupRelation.query.filter_by(status=0)

    for item in items:
        # add all item ids to redis with current user id
        rds.sadd('dedq', '{}|{}'.format(item.id, current_user.id))
    # activate redis flag to process data
    rds.set('dedup', 1)
    return 'Data queued successfully', 200


@deduplication.route('/api/deduplication/stop', methods=['POST'])
@roles_required('Admin')
def api_process_stop():
    """
    Endpoint used to stop processing dedup data
    """
    # just remove the redis flag
    rds.delete('dedup')

    return 'Success, processing will stop shortly.', 200


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
@click.option('-d', '--distance', type=float, default=0.7)
@with_appcontext
def dedup_import(file, remove, distance):
    """Imports data from deduplication compatible file, with an option to clear existing data."""
    if remove:
        DedupRelation.query.delete()
        db.session.commit()
        print('Cleared all existing matches.')

    # create pandas data frame
    print('Reading CSV file...')
    df = pd.read_csv(file)
    print('Droping self-referencing matches...')
    df = df[df.query_video != df.match_video]
    print('Droping matches with out-of-scope distances...')
    df = df[df.distance < distance]
    print('Droping duplicate matches based on unique_index column...')
    df.drop_duplicates(subset='unique_index', keep='first', inplace=True)
    print('Droping duplicate matches for same query and match videos...')
    # to handle duplicate in both directions , generate a computed column first
    df['match_id'] = df.apply(lambda x: str(sorted([x.query_video, x.match_video])), axis=1)
    df.drop_duplicates(subset=['match_id'], keep='first', inplace=True)

    records = df.to_dict(orient='records')
    with click.progressbar(records, label='Importing Matches', show_pos=True) as bar:
        for item in bar:
            br = DedupRelation()
            br.query_video = item.get('query_video')
            br.match_video = item.get('match_video')
            br.distance = item.get('distance')
            # to create a unique string for the match and disallow duplicate matches
            br.match_id = sorted((br.query_video, br.match_video))
            br.notes = item.get('notes')
            if not br.save():
                print('Error importing match {}-{}.'.format(item.get('query_video'), item.get('match_video')))
    print('=== Done ===')


@deduplication.cli.command()
@click.option('-p', '--no-of-processes', type=int, default=int(cpu_count() / 2))
@with_appcontext
def fast_process(no_of_processes):
    """Process deduplication matches in a faster way"""
    pool = Pool(processes=no_of_processes)
    items = DedupRelation.query.filter_by(status=0)
    if items:
        pool.map(DedupRelation.process, items, 1)


# statistics endpoints


def process_stream():
    pubsub = rds.pubsub()
    pubsub.subscribe('dedprocess')
    # avoid sending first subscribtion message
    for msg in pubsub.listen():
        if msg['type'] == 'message':
            yield 'data:{}\n\n'.format(msg['data'])
    return ''


@deduplication.route('/stream')
def stream():
    return Response(process_stream(), mimetype="text/event-stream")
