import json
import os
import re
import shutil

from flask import Flask, flash, redirect, render_template, request, url_for
from tvnamer.tvnamer_exceptions import (NoValidFilesFoundError,
                                        SkipBehaviourAbort, UserAbort)
from werkzeug.utils import secure_filename

from tv import detect_shows

UPLOAD_FOLDER = os.path.abspath('./uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PLEX_MOVIE_FOLDER'] = os.path.abspath('./plex/movies')
app.config['PLEX_TV_FOLDER'] = os.path.abspath('./plex/tv')

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

    #process_uploads(media_type=media_type)

    return("Uploaded Files")

@app.route('/process', methods=['GET'])
def process_uploads(media_type = None):
    # connect google drive / plex library folder
    if media_type == None:
        media_type = request.args['media_type']
    print(media_type)
    #media_type = 'movie' #request.data['media_type']
    UPLOADS = os.path.join(app.config['UPLOAD_FOLDER'], media_type)

    if media_type == 'movie':
        # move uploaded file to plex/movies
        dirs = os.listdir(UPLOADS)
        for dir in dirs:
            shutil.move(os.path.join(UPLOADS, dir), app.config['PLEX_MOVIE_FOLDER'])
        
        return(json.dumps(dirs))
    elif media_type == 'tv':
        # Detect tv show using tvnamer
        try:
            episodes = detect_shows(UPLOADS)
            episodes_response = [episode.generateFilename() for episode in episodes]
        except NoValidFilesFoundError:
            return("No valid files were supplied")
        except UserAbort as errormsg:
            return(errormsg)
        except SkipBehaviourAbort as errormsg:
            return(errormsg)

        # move uploaded file to plex folder
        for episode in episodes:
            if episode.seriesname:
                dest_dir = os.path.join(
                    app.config['PLEX_TV_FOLDER'],
                    episode.seriesname.lower(),
                    "season_{:02d}".format(episode.seasonnumber)
                    )

                os.makedirs(dest_dir, exist_ok=True)

                parent_dir = "/".join(episode.fullpath.split("/")[:-1])
                filename = episode.generateFilename()
                fullpath = os.path.join(parent_dir, filename)

                shutil.move(fullpath, os.path.join(dest_dir, filename))
                # delete season directory if empty
                if not os.listdir(parent_dir):
                    shutil.rmtree(parent_dir)

        # delete series directory if empty
        print(os.listdir(UPLOADS))
        for dir in os.listdir(UPLOADS):
            print(dir)
            if not os.listdir(os.path.join(UPLOADS, dir)):
                shutil.rmtree(dir)
        
        return json.dumps(episodes_response)


    else:
        return 'Unsupported media type'

    