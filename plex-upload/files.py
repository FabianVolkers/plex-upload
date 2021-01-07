import json
import os
import re
import shutil

from flask import (Blueprint, Flask, current_app, flash, redirect,
                   render_template, request, url_for)
from tvnamer.tvnamer_exceptions import (NoValidFilesFoundError,
                                        SkipBehaviourAbort, UserAbort)
from werkzeug.utils import secure_filename

from .tv import detect_shows

bp = Blueprint('files', __name__, url_prefix='/files')

@bp.route('/upload', methods=['POST'])
def upload():
    media_type = request.form['media-type']

    UPLOAD_FOLDER = current_app.config['UPLOAD_FOLDER']
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
            os.makedirs(os.path.join(UPLOAD_FOLDER, "/".join(dirs[:-1])), exist_ok=True)


        if file and filename:
            file.save(os.path.join(UPLOAD_FOLDER, filename))

    #process_uploads(media_type=media_type)

    return("Uploaded Files")

@bp.route('/process', methods=['GET'])
def process_uploads(media_type=None):
    # connect google drive / plex library folder
    if media_type == None:
        media_type = request.args['media_type']
    
    dry_run = bool(request.args['dry_run'])
    #media_type = 'movie' #request.data['media_type']
    UPLOADS = os.path.join(current_app.config['UPLOAD_FOLDER'], media_type)
    MOVIES = current_app.config['PLEX_MOVIE_FOLDER']
    TV_SHOWS = current_app.config['PLEX_TV_FOLDER']

    if media_type == 'movie':
        # move uploaded file to plex/movies
        dirs = os.listdir(UPLOADS)
        errs = []
        for dir in dirs:
            try:
                
                shutil.move(os.path.join(UPLOADS, dir), MOVIES)
            except shutil.Error as e:
                dirs.remove(dir) 
                errs.append(str(e))

        
        return {
            "files": dirs,
            "errors": errs,
            "plex_url": current_app.config['PLEX_MOVIE_URL']
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
                        TV_SHOWS,
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
            "plex_url": current_app.config['PLEX_TV_URL']
            }


    else:
        return 'Unsupported media type'

