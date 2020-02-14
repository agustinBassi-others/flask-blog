"""
To run the application in the CLI do this:

- export FLASK_APP=flaskr
- export FLASK_ENV=development

flask run
"""

import os

from flask import Flask
from flask import g
from flaskext.markdown import Markdown

APP_CONFIG = {
    "POSTS_PER_PAGE"     : 10,
    "POST_IMAGES_FOLDER" : "flaskr/static/post_images",
    "POST_IMAGES_PREFIX" : "static/post_images",
    "ALLOWED_EXTENSIONS" : {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
}

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )
    # create the markdown object and instanciate it with the Flask app
    markdown = Markdown(app, extensions=['fenced_code'])

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    app.logger.info('Stating application "{}"'.format(__name__))

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # ensure the images folder exists
    try:
        os.makedirs(APP_CONFIG["POST_IMAGES_FOLDER"])
    except OSError:
        pass

    from . import db
    db.init_app(app)
    app.logger.info('DB is running')

    from . import auth
    app.register_blueprint(auth.bp)
    app.logger.info('Authentication blueprint is running')

    from . import topic
    app.register_blueprint(topic.bp)
    app.logger.info('Topics blueprint is running')

    from . import blog
    app.register_blueprint(blog.bp)
    app.add_url_rule('/', endpoint='index') 
    app.logger.info('Blog blueprint is running')
    
    return app