import os
from flask import Flask, flash, request, redirect, url_for, render_template
from werkzeug.utils import secure_filename
from tvnamer.main import tvnamer
from tvnamer.config_defaults import defaults
from tvnamer.config import Config

from tvnamer.tvnamer_exceptions import (
    ShowNotFound,
    SeasonNotFound,
    EpisodeNotFound,
    EpisodeNameNotFound,
    UserAbort,
    InvalidPath,
    NoValidFilesFoundError,
    SkipBehaviourAbort,
    InvalidFilename,
    DataRetrievalError,
)

UPLOAD_FOLDER = os.path.abspath('./uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PLEX_MOVIE_FOLDER'] = os.path.abspath('./uploads/movies')
app.config['PLEX_TV_FOLDER'] = os.path.abspath('./uploads/tv')

@app.route('/', methods=['GET'])
def upload_form():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload():
    media_type = request.form['media-type']
    for i in range(len(request.files)):
        name, ext = os.path.splitext(request.form[f'path-{i}'])
        filename = f"{media_type}/{name.title()}{ext}"
        file = request.files[f'files[{i}]']

        if 'movie/undefined' == filename.lower():
            name, ext = os.path.splitext(file.filename)
            filename = f"{media_type}/{name.title()}/{name.title()}{ext}"
        elif 'tv/undefined' == filename.lower():
            name, ext = os.path.splitext(file.filename)
            filename = f"{media_type}/{name.title()}{ext}"
        elif 'undefined' == filename.lower():
            print(filename)

        dirs = filename.split('/')
        if len(dirs) > 1:
            os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], "/".join(dirs[:-1])), exist_ok=True)


        if file and filename:
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    process_uploads()

    return("Uploaded Files")

@app.route('/process', methods=['POST'])
def process_uploads():
    # connect google drive / plex library folder

    media_type = 'tv' #request.data['media_type']

    if media_type == 'movie':
        # move uploaded file to plex/movies
        pass
    elif media_type == 'tv':
        Config = defaults
        Config['verbose'] = True
        
        paths = os.scandir(app.config['PLEX_TV_FOLDER'])

        for path in paths:
            print(path.path)
            path = path.path


        try:
            tvnamer(paths=sorted(paths))
        except NoValidFilesFoundError:
            return("No valid files were supplied")
        except UserAbort as errormsg:
            return(errormsg)
        except SkipBehaviourAbort as errormsg:
            return(errormsg)
        # check if tv show already exists
        # if yes: 
            # check if season(s) already exists
            # if yes: move only episodes
            # if no: move season directories
        # if no: move entire directory
        pass
    else:
        return 'Unsupported media type'

    return "Imported Files to Plex"