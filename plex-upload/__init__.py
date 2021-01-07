import os

from flask import Flask, render_template

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'db.sqlite'),
    )  

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=False)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Index: main view
    @app.route('/', methods=['GET'])
    def index():
        return render_template('upload.html')
    
    with app.app_context():
        # File API endpoints
        from . import files
        app.register_blueprint(files.bp)

        # Authentication views
        from . import auth
        app.register_blueprint(auth.bp)


    return app