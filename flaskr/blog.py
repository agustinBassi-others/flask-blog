from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from flask_paginate import Pagination, get_page_args

from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

from . __init__ import POSTS_PER_PAGE

bp = Blueprint('blog', __name__)

@bp.route('/')
def index():
    # Get arguments from pagination plugin    
    (page, per_page, offset) = get_page_args(page_parameter='page', per_page_parameter='per_page')
    #validate the index of page
    try:
        if int(page) <= 0:
            page = 1
    except:
        print("Exception parsing page")
        page = 1
    # calculate the offset
    offset = int(POSTS_PER_PAGE * (page - 1))
    # obtain the post in the range page/offset
    posts = get_posts(limit=POSTS_PER_PAGE, offset=offset)
    # get the amount of total posts
    total = get_amount_of_posts()
    # create the pagination object
    pagination = Pagination(page=page, per_page=POSTS_PER_PAGE, total=total, css_framework='bootstrap4')
    # pass the info to the template
    return render_template('blog/index.html', 
        posts=posts, 
        posts_tags=get_tags_list(),
        page=page,
        per_page=POSTS_PER_PAGE,
        pagination=pagination
        )

@bp.route('/filter_tag', methods=('GET',))
def filter_tag():
    db = get_db()
    multiple_tags = request.args.get('multiple_tags')
    # validate arg received
    if multiple_tags is not "" and multiple_tags is not None and "#" in multiple_tags:
        # create query that will be aggregated then
        query = """
            SELECT p.id, title, tags, created, author_id, username,
                (SELECT COUNT(1) FROM likes WHERE post_id = p.id) as likes,
                (SELECT COUNT(1) FROM dislikes WHERE post_id = p.id) AS dislikes 
            FROM post p 
            JOIN user u ON p.author_id = u.id 
            WHERE #tags#  
            ORDER BY created DESC """
        # clean up the tags string value
        multiple_tags = multiple_tags.replace(" ", "").split("#")[1::]
        # create the string to find coincidences of tags in posts
        tags_query = ""
        for tag in multiple_tags:
            # add content to the tag query
            tags_query += "instr(tags, '{}') ".format(tag)
            # if is not las item add and OR statement
            if tag != multiple_tags[-1]:
                tags_query += "OR "
        #replace the tags_query in the query that will be excecuted
        query = query.replace("#tags#", tags_query)
        #execute the query
        posts = db.execute(query).fetchall()
        multiple_tags = request.args.get('multiple_tags')
        return render_template('blog/index.html', posts=posts, multiple_tags=multiple_tags, posts_tags=get_tags_list())
    else:
        return redirect(url_for('blog.index'))

@bp.route('/filter_title', methods=('GET',))
def filter_title():
    db = get_db()
    title_to_find = request.args.get('title_to_find')
    # validate arg received
    if title_to_find is not "" and title_to_find is not None:
        query = """
            SELECT p.id, title, tags, created, author_id, username,
                (SELECT COUNT(1) FROM likes WHERE post_id = p.id) as likes,
                (SELECT COUNT(1) FROM dislikes WHERE post_id = p.id) AS dislikes 
            FROM post p 
            JOIN user u ON p.author_id = u.id 
            WHERE title LIKE "%{}%"   
            ORDER BY created DESC """.format(title_to_find)
        #execute the query
        posts = db.execute(query).fetchall()
        return render_template('blog/index.html', posts=posts, posts_tags=get_tags_list(), title_to_find=title_to_find)
    else:
        return redirect(url_for('blog.index'))

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        tags = request.form['tags']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO post (title, body, author_id, tags)'
                ' VALUES (?, ?, ?, ?)',
                (title, body, g.user['id'], tags)
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/create.html')

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        error = None
        title = request.form['title']
        body = request.form['body']
        tags = request.form['tags']

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ?, tags = ?'
                ' WHERE id = ?',
                (title, body, tags, id)
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
        'SELECT p.id, title, tags, body, created, author_id, username,'
            ' (SELECT COUNT(1) FROM likes WHERE post_id = ?) as likes,'
            ' (SELECT COUNT(1) FROM dislikes WHERE post_id = ?) AS dislikes '
        ' FROM post p'
        ' JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id, id, id)
    ).fetchall()
    
    comments = db.execute(
        'SELECT u.id as author_id, u.username AS username, c.id AS comment_id, created, body'
        ' FROM comments c'
        ' JOIN user u ON c.author_id = u.id'
        ' WHERE post_id = ?'
        ' ORDER BY created DESC',
        (id,)
    ).fetchall()

    return render_template('blog/detail.html', posts=posts, comments=comments)

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
    # redirect to detail page
    return redirect(url_for('blog.detail', id=id))

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
    # redirect to detail page
    return redirect(url_for('blog.detail', id=id))

@bp.route('/<int:id>/comment', methods=('POST',))
@login_required
def comment(id):
    if request.method == 'POST':
        body = request.form['body']
        error = None

        if not body:
            error = 'Comment body is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO comments (author_id, post_id, body)'
                ' VALUES (?, ?, ?)',
                (g.user['id'], id, body)
            )
            db.commit()
            return redirect(url_for('blog.detail', id=id))
    else:
        error = 'Invalid HTTP method.'
        flash(error)

@bp.route('/<int:id>/uncomment', methods=('POST',))
@login_required
def uncomment(id):
    if request.method == 'POST':
        error = None

        author_id = request.form['author_id']
        post_id = request.form['post_id']

        if author_id is None:
            error = 'The author_id must be passed to delete the comment'
        
        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'DELETE FROM comments'
                ' WHERE id = ?',
                (id,)
            )
            db.commit()
            return redirect(url_for('blog.detail', id=post_id))
    else:
        error = 'Invalid HTTP method.'
        flash(error)

#####[ Functions and APIs ]####################################################

def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, title, tags, body, created, author_id, username'
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

def get_tags_list():
    db = get_db()
    # get text of tags of each post
    tags_query = db.execute("SELECT tags FROM post").fetchall()
    tags = ""
    for tag in tags_query:
        # append each tag text into tags variable
        tags += tag[0]
    #from appended tags variable, remove spaces and split string
    #by '#'. After that remove the first element (a white space),
    #and then create a set to remove repeated values.
    tags = list(set(tags.replace(" ", "").split("#")[1::]))
    # add '#' again to each tag after processing
    tags = ["#" + tag for tag in tags]
    tags.sort()
    return tags

def get_posts(offset=0, limit=POSTS_PER_PAGE):
    db = get_db()
    amount_of_posts = get_amount_of_posts()
    # check and correct the limit before to execute the query 
    if offset + limit >= amount_of_posts:
        limit = int(amount_of_posts - offset)
    posts = db.execute( """
        SELECT p.id, title, tags, created, author_id, username,
            (SELECT COUNT(1) FROM likes WHERE post_id = p.id) as likes,
            (SELECT COUNT(1) FROM dislikes WHERE post_id = p.id) AS dislikes 
        FROM post p 
        JOIN user u ON p.author_id = u.id 
        ORDER BY created DESC 
        LIMIT ? OFFSET ?""",
        (limit, offset)
    ).fetchall()
    return posts

def get_all_posts():
    db = get_db()
    posts = db.execute(
        'SELECT p.id, title, tags, created, author_id, username,'
            ' (SELECT COUNT(1) FROM likes WHERE post_id = p.id) as likes,'
            ' (SELECT COUNT(1) FROM dislikes WHERE post_id = p.id) AS dislikes '
        ' FROM post p'
        ' JOIN user u ON p.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    return posts

def get_amount_of_posts():
    db = get_db()
    posts = db.execute("SELECT COUNT(1) AS amount FROM post").fetchall()[0][0]
    return int(posts)


    