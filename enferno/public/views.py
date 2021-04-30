from flask import request, redirect, Blueprint, send_from_directory

bp_public = Blueprint('public', __name__, static_folder='../static')


@bp_public.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'public, max-age=10800'
    return response


@bp_public.route('/')
def index():
    return redirect('/dashboard')


@bp_public.route('/robots.txt')
def static_from_root():
    return send_from_directory(bp_public.static_folder, request.path[1:])
