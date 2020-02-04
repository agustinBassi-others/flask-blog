from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint('blog', __name__)

@bp.route('/')
def index():
    db = get_db()
    posts = db.execute(
        'SELECT p.id, title, body, created, author_id, username,'
            ' (SELECT COUNT(1) FROM likes WHERE post_id = p.id) as likes,'
            ' (SELECT COUNT(1) FROM dislikes WHERE post_id = p.id) AS dislikes '
        ' FROM post p'
        ' JOIN user u ON p.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    return render_template('blog/index.html', posts=posts)

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO post (title, body, author_id)'
                ' VALUES (?, ?, ?)',
                (title, body, g.user['id'])
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/create.html')

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/update.html', post=post)

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index'))

@bp.route('/<int:id>/detail', methods=('GET', ))
def detail(id):
    db = get_db()
    posts = db.execute(
        'SELECT p.id, title, body, created, author_id, username,'
            ' (SELECT COUNT(1) FROM likes WHERE post_id = ?) as likes,'
            ' (SELECT COUNT(1) FROM dislikes WHERE post_id = ?) AS dislikes '
        ' FROM post p'
        ' JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id, id, id)
    ).fetchall()
    return render_template('blog/detail.html', posts=posts)

@bp.route('/<int:id>/like', methods=('GET',))
@login_required
def like(id):
    db = get_db()
    # check if a user did the same like before
    like_done_before = db.execute(
        'SELECT COUNT(1)'
        ' FROM likes'
        ' WHERE author_id = ? AND post_id = ?', 
        (g.user['id'], id)
        ).fetchone()[0]
    # if like not done before
    if not like_done_before:
        db.execute(
            'INSERT INTO likes'
            ' (author_id, post_id)'
            ' VALUES ( ?, ? )', 
            (g.user['id'], id,)
        )
        db.commit()
    # if not delete the like done
    else:
        db.execute(
            'DELETE FROM likes'
            ' WHERE author_id = ? AND post_id = ?', 
            (g.user['id'], id,)
        )
        db.commit()
    # redirect to main page
    return redirect(url_for('blog.index'))

@bp.route('/<int:id>/dislike', methods=('GET',))
@login_required
def dislike(id):
    db = get_db()
    # check if a user did the same like before
    dislike_done_before = db.execute(
        'SELECT COUNT(1)'
        ' FROM dislikes'
        ' WHERE author_id = ? AND post_id = ?', 
        (g.user['id'], id)
        ).fetchone()[0]
    # if like not done before
    if not dislike_done_before:
        db.execute(
            'INSERT INTO dislikes'
            ' (author_id, post_id)'
            ' VALUES ( ?, ? )', 
            (g.user['id'], id,)
        )
        db.commit()
    # if not delete the dislike done
    else:
        db.execute(
            'DELETE FROM dislikes'
            ' WHERE author_id = ? AND post_id = ?', 
            (g.user['id'], id,)
        )
        db.commit()
    # redirect to main page
    return redirect(url_for('blog.index'))

#####[ Functions and APIs ]####################################################

def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, "Post id {0} doesn't exist.".format(id))

    if check_author and post['author_id'] != g.user['id']:
        abort(403)

    return post

def get_post_likes(id):
    db = get_db()
    # check if a user did the same like before
    likes = db.execute(
        'SELECT COUNT(1)'
        ' FROM likes'
        ' WHERE post_id = ?', 
        (id)
        ).fetchone()[0]
    return likes

def get_post_dislikes(id):
    db = get_db()
    # check if a user did the same like before
    dislikes = db.execute(
        'SELECT COUNT(1)'
        ' FROM dislikes'
        ' WHERE post_id = ?', 
        (id)
        ).fetchone()[0]
    return dislikes