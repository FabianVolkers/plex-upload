import json
import os
import re
import shutil
import logging
from flask import (Blueprint, Flask, current_app, flash, make_response, redirect,
                   render_template, request, url_for)
from tvnamer.tvnamer_exceptions import (NoValidFilesFoundError,
                                        SkipBehaviourAbort, UserAbort)
from werkzeug.utils import secure_filename

from .tv import detect_shows, errors

bp = Blueprint('files', __name__, url_prefix='/files')
log = logging.getLogger()

@bp.route('/upload', methods=['POST'])
def upload():
    media_type = request.form['media-type']

    UPLOAD_FOLDER = current_app.config['UPLOAD_FOLDER']
    name, ext = os.path.splitext(request.form[f'path'])
    filename = f"{media_type}/{name.title()}{ext}"
    file = request.files['file']

    current_chunk = int(request.form['dzchunkindex'])

    if 'movie/undefined' == filename.lower():
        name, ext = os.path.splitext(file.filename)
        filename = f"{media_type}/{name.title()}/{name.title()}{ext}"
    elif 'tv/undefined' == filename.lower():
        name, ext = os.path.splitext(file.filename)
        filename = f"{media_type}/{name.title()}{ext}"
    elif 'undefined' == filename.lower():
        print(filename)

    dirs = filename.split('/')

    save_dir = os.path.join(UPLOAD_FOLDER, "/".join(dirs[:-1]))
    save_path = os.path.join(UPLOAD_FOLDER, filename)

    if len(dirs) > 1:
        os.makedirs(save_dir, exist_ok=True)

    # If the file already exists it's ok if we are appending to it,
    # but not if it's new file that would overwrite the existing one
    if os.path.exists(save_path) and current_chunk == 0:
        # 400 and 500s will tell dropzone that an error occurred and show an error
        return make_response(('File already exists', 400))

    try:
        with open(save_path, 'ab') as f:
            f.seek(int(request.form['dzchunkbyteoffset']))
            f.write(file.stream.read())
    except OSError:
        # log.exception will include the traceback so we can see what's wrong 
        log.exception('Could not write to file')
        return make_response(("Not sure why,"
                              " but we couldn't write the file to disk", 500))
    
    total_chunks = int(request.form['dztotalchunkcount'])

    if current_chunk + 1 == total_chunks:
        # This was the last chunk, the file should be complete and the size we expect
        if os.path.getsize(save_path) != int(request.form['dztotalfilesize']):
            log.error(f"File {file.filename} was completed, "
                      f"but has a size mismatch."
                      f"Was {os.path.getsize(save_path)} but we"
                      f" expected {request.form['dztotalfilesize']} ")
            return make_response(('Size mismatch', 500))
        else:
            log.info(f'File {file.filename} has been uploaded successfully')
    else:
        log.debug(f'Chunk {current_chunk + 1} of {total_chunks} '
                  f'for file {file.filename} complete')

    return make_response(("Chunk upload successful", 200))

    # if file and filename:
    #     file.save(os.path.join(UPLOAD_FOLDER, filename))
    # for i in range(len(request.files)):


    #return("Uploaded Files")

@bp.route('/process', methods=['GET'])
def process_uploads(media_type=None):
    
    # connect google drive / plex library folder
    if media_type == None:
        media_type = request.args['media_type']
    
    dry_run = bool(int(request.args['dry_run']))

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
        episodes_response = []
        try:
            episodes = detect_shows(UPLOADS, dry_run)
            
            for episode in episodes:
                if hasattr(episode, 'generatedfilename'):
                    episodes_response.append(episode.generatedfilename)

        except NoValidFilesFoundError:
            print("No valid files were supplied")
        except UserAbort as errormsg:
            return(errormsg)
        except SkipBehaviourAbort as errormsg:
            return(errormsg)

        # move uploaded file to plex folder
        if not dry_run:

            for episode in episodes:
                if hasattr(episode, 'generatedfilename'):
                    
                    dest_dir = os.path.join(
                        TV_SHOWS,
                        episode.seriesname.lower(),
                        "season_{:02d}".format(episode.seasonnumber)
                        )

                    os.makedirs(dest_dir, exist_ok=True)

                    parent_dir = "/".join(episode.fullpath.split("/")[:-1])
                    filename = episode.generatedfilename
                    fullpath = os.path.join(parent_dir, filename)

                    shutil.move(fullpath, os.path.join(dest_dir, filename))
                    # delete season directory if empty
                    if not os.listdir(parent_dir) :
                        shutil.rmtree(parent_dir)

        # delete series directory if empty
        for dir in os.listdir(UPLOADS):
            if os.path.isdir(dir) and not os.listdir(os.path.join(UPLOADS, dir)):
                shutil.rmtree(dir)

        return {
            "files": episodes_response,
            "errors": errors,
            "plex_url": current_app.config['PLEX_TV_URL']
            }


    else:
        return 'Unsupported media type'

