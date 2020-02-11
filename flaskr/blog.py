from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, send_from_directory
)
from flask_paginate import Pagination, get_page_args

from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

import os
import time

from werkzeug.utils import secure_filename

from . __init__ import POSTS_PER_PAGE, POST_IMAGES_FOLDER, ALLOWED_EXTENSIONS, POST_IMAGES_PREFIX

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
        pagination=pagination,
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

    def validate_form():
        #TODO: crear esta funcion en la que se validen todas las entradas y flashee el error
        # agregar la vaidacion del file tambien
        pass

    def insert_post():

        pass

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        tags = request.form['tags']
        error = None

        if not title:
            error = 'Title is required.'
        if not tags:
            error = 'Tags are required.'
        if not body:
            error = 'Body is required.'
        if 'file' not in request.files:
            error = 'Image is required.'
        
        # add the hashtag in case if not introduced by user
        tags = "#" + tags if not "#" in tags else tags

        
        file = request.files['file']

        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            error = 'No selected file'
        if file and is_image_valid_format(file.filename):
            filename = secure_filename(file.filename)
            # add timestamp to filename
            filename = add_timestamp_to_filename(filename)
            filepath = os.path.join(POST_IMAGES_FOLDER, filename)
            file.save(filepath)
            blob_icon = convert_file_to_binary_data(filepath)

        if error is not None:
            flash(error)
            return redirect(request.url)
        else:
            db = get_db()
            # TODO: Una opcion podria ser guardar la imagen en la DB,
            # cuando el HTML pida la imagen que la sirva en un directorio temporal
            # de esta manera se puede ir guardando todo en la base y no duplicarlo en el FS
            # REFUTADA porque es una operacion de I/O
            db.execute(
                'INSERT INTO post (title, body, author_id, tags, icon, image)'
                ' VALUES (?, ?, ?, ?, ?, ?)',
                (title, body, g.user['id'], tags, blob_icon, filename)
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
        ' WHERE post_id = ? AND repplied_to = 0'
        ' ORDER BY created DESC',
        (id,)
    ).fetchall()

    subcomments = {}
    for comment in comments:
        comment_id = int(comment['comment_id'])
        temp_subcomments = db.execute(
            'SELECT u.id as author_id, u.username AS username, c.id AS comment_id, created, body'
            ' FROM comments c'
            ' JOIN user u ON c.author_id = u.id'
            ' WHERE repplied_to = ?'
            ' ORDER BY created ASC',
            (comment_id,)
        ).fetchall()
        subcomments[comment_id] = temp_subcomments

    return render_template('blog/detail.html', posts=posts, comments=comments, subcomments=subcomments)

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

@bp.route('/<int:id>/repply', methods=('GET', 'POST',))
# @login_required
def repply(id):
    if request.method == 'POST':
        repply = request.form['repply']
        author_id = request.form['author_id']
        post_id = request.form['post_id']

        print("Comment: {} - by {} - Associated to id: {} - Post id: {}".format(
            repply, author_id, id, post_id))

        error = None

        if not repply:
            error = 'Repply is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO comments (author_id, post_id, body, repplied_to)'
                ' VALUES (?, ?, ?, ?)',
                (g.user['id'], post_id, repply, id)
            )
            db.commit()
            return redirect(url_for('blog.detail', id=post_id))
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

@bp.route('/<int:id>/image', methods=('GET', ))
def image(id):
    db = get_db()
    image_path = db.execute( """
        SELECT image AS image_path 
        FROM post  
        WHERE id = ?""",
        (id,)
    ).fetchall()[0][0]
    return send_from_directory(POST_IMAGES_PREFIX, image_path)


#####[ Posts functions and APIs ]##############################################

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

#####[ Image utils ]###########################################################

def is_image_valid_format(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_file_to_binary_data(filename):
    #Convert digital data to binary format
    with open(filename, 'rb') as file:
        blobData = file.read()
    return blobData

def add_timestamp_to_filename(filename):
    if filename is not None and filename != "" and "." in filename:
        timestamp = str(int(time.time()))
        splitted_filename = filename.split(".")
        new_filename = splitted_filename[0] + "_" + timestamp + "." + splitted_filename[1]
        print("The new file is: " + new_filename)
        return new_filename
    else:
        return filename
    