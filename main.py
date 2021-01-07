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
def process_uploads(media_type=None):
    # connect google drive / plex library folder
    if media_type == None:
        media_type = request.args['media_type']
    
    dry_run = bool(request.args['dry_run'])
    #media_type = 'movie' #request.data['media_type']
    UPLOADS = os.path.join(app.config['UPLOAD_FOLDER'], media_type)

    if media_type == 'movie':
        # move uploaded file to plex/movies
        dirs = os.listdir(UPLOADS)
        errs = []
        for dir in dirs:
            try:
                shutil.move(os.path.join(UPLOADS, dir), app.config['PLEX_MOVIE_FOLDER'])
            except shutil.Error as e:
                dirs.remove(dir) 
                errs.append(str(e))

        
        return {
            "files": dirs,
            "errors": errs,
            "plex_url": "https://app.plex.tv/desktop#!/media/d391e47fb3d0e2f458f498e7a5dbf6b20f3ec2b4/com.plexapp.plugins.library?key=%2Flibrary%2Fsections%2F1%2Fall%3Fsort%3DaddedAt%3Adesc&title=Recently%20Added%20in%20Films&context=source%3Ahub.movie.recentlyadded&pageType=list&source=1"
            }

    elif media_type == 'tv':
        # Detect tv show using tvnamer
        try:
            episodes = detect_shows(UPLOADS, dry_run)
            episodes_response = [episode.generateFilename() for episode in episodes]
        except NoValidFilesFoundError:
            return("No valid files were supplied")
        except UserAbort as errormsg:
            return(errormsg)
        except SkipBehaviourAbort as errormsg:
            return(errormsg)

        # move uploaded file to plex folder
        if not dry_run:
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
        for dir in os.listdir(UPLOADS):
            if os.path.isdir(dir) and not os.listdir(os.path.join(UPLOADS, dir)):
                shutil.rmtree(dir)
        
        return {
            "files": episodes_response,
            "errors": [],
            "plex_url": "https://app.plex.tv/desktop#!/media/d391e47fb3d0e2f458f498e7a5dbf6b20f3ec2b4/com.plexapp.plugins.library?key=%2Fhubs%2Fhome%2FrecentlyAdded%3Ftype%3D2%26sectionID%3D2&title=Recently%20Added%20in%20TV%20programmes&context=source%3Ahub.tv.recentlyadded&pageType=list&source=2"
            }


    else:
        return 'Unsupported media type'

    