"""
Settings File
"""
import os
from get_docker_secret import get_docker_secret

UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.abspath('/uploads'))
PLEX_MOVIE_FOLDER = os.getenv('PLEX_MOVIE_FOLDER', os.path.abspath('/plex/movies'))
PLEX_TV_FOLDER = os.getenv('PLEX_TV_FOLDER', os.path.abspath('/plex/tv'))
PLEX_TV_URL = os.getenv('PLEX_TV_URL')
PLEX_MOVIE_URL = os.getenv('PLEX_MOVIE_URL')
SECRET_KEY = get_docker_secret('flask_secret_key', default='very_secret')