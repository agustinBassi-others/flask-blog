from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, send_from_directory
)
from flask import current_app as app

from flask_paginate import Pagination, get_page_args

from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

import os
import time

from werkzeug.utils import secure_filename

from . __init__ import APP_CONFIG

bp = Blueprint('topic', __name__)

@bp.route('/topic_create', methods=('GET', 'POST'))
@login_required
def create():

    if request.method == 'POST':
        name = request.form['name']
        error = None

        if not name:
            error = 'Name is required.'

        if error is not None:
            flash(error)
            return redirect(request.url)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO topics (author_id, name)'
                ' VALUES (?, ?)',
                (g.user['id'], name)
            )
            db.commit()
            return redirect(url_for('blog.index'))
    else:
        db = get_db()
        topics = db.execute(
            'SELECT id, name, author_id FROM topics'
        ).fetchall()
        return render_template('topic/create.html', topics=topics)

@bp.route('/<int:id>/topic_update', methods=('GET', 'POST'))
@login_required
def update(id):
    topic = get_topic(id)
    if request.method == 'POST':
        name = request.form['name']
        error = None

        if not name:
            error = 'Name is required.'

        if error is not None:
            flash(error)
            return redirect(request.url)
        else:
            db = get_db()
            db.execute(
                'UPDATE topics SET name = ? WHERE id = ?',
                (name, id)
            )
            db.commit()
            return redirect(url_for('blog.index'))
    else:
        return render_template('topic/update.html', topic=topic)

@bp.route('/<int:id>/topic_delete', methods=('POST',))
@login_required
def delete(id):
    app.logger.info('Deleting the topic id {}'.format(id))
    get_topic(id)
    db = get_db()
    db.execute('DELETE FROM topics WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index'))

#####[ Topics functions and APIs ]##############################################

def get_topic(id, check_author=True):
    app.logger.debug('Getting information of topic id: {}'.format(id))
    topic = get_db().execute(
        'SELECT id, name, author_id FROM topics WHERE id = ?',
        (id,)
    ).fetchone()

    if topic is None:
        abort(404, "Topic id {0} doesn't exist.".format(id))

    if check_author and topic['author_id'] != g.user['id']:
        abort(403)

    return topic

def get_topics():
    db = get_db()
    topics = db.execute(
        'SELECT id, name, author_id FROM topics'
    ).fetchall()
    return topics

def get_topics_list():
    db = get_db()
    topics = db.execute(
        'SELECT name FROM topics'
    ).fetchall()
    topic_list = []
    for topic in topics:
        topic_list.append(topic["name"])
    return topic_list