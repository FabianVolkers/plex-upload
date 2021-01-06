
import logging
import os

import tvdb_api
from tvdb_api import Tvdb
from tvnamer.compat import PY2, raw_input
from tvnamer.config import Config
from tvnamer.config_defaults import defaults
from tvnamer.main import FileParser, findFiles, processFile
from tvnamer.tvnamer_exceptions import (DataRetrievalError,
                                        EpisodeNameNotFound, EpisodeNotFound,
                                        InvalidFilename, InvalidPath,
                                        NoValidFilesFoundError, SeasonNotFound,
                                        ShowNotFound, SkipBehaviourAbort,
                                        UserAbort)
from tvnamer.unicode_helper import p
from tvnamer.utils import warn

LOG = logging.getLogger(__name__)
TVNAMER_API_KEY = "fb51f9b848ffac9750bada89ecba0225"

def tvnamer(paths):
    """Main tvnamer function, takes an array of paths, does stuff.
    """

    p("#" * 20)
    p("# Starting tvnamer")

    episodes_found = []

    for cfile in findFiles(paths):
        parser = FileParser(cfile)
        try:
            episode = parser.parse()
        except InvalidFilename as e:
            warn("Invalid filename: %s" % e)
        else:
            if episode.seriesname is None and Config['force_name'] is None and Config['series_id'] is None:
                warn("Parsed filename did not contain series name (and --name or --series-id not specified), skipping: %s" % cfile)

            else:
                episodes_found.append(episode)

    if len(episodes_found) == 0:
        raise NoValidFilesFoundError()

    p("# Found %d episode" % len(episodes_found) + ("s" * (len(episodes_found) > 1)))

    # Sort episodes by series name, season and episode number
    episodes_found.sort(key = lambda x: x.sortable_info())

    # episode sort order
    if Config['order'] == 'dvd':
        dvdorder = True
    else:
        dvdorder = False

    if not PY2 and os.getenv("TRAVIS", "false") == "true":
        # Disable caching on Travis-CI because in Python 3 it errors with:
        #
        # Can't pickle <class 'http.cookiejar.DefaultCookiePolicy'>: it's not the same object as http.cookiejar.DefaultCookiePolicy
        cache = False
    else:
        cache = True

    if Config['tvdb_api_key'] is not None:
        LOG.debug("Using custom API key from config")
        api_key = Config['tvdb_api_key']
    else:
        LOG.debug("Using tvnamer default API key")
        api_key = TVNAMER_API_KEY

    tvdb_instance = Tvdb(
        interactive = not Config['select_first'],
        search_all_languages = Config['search_all_languages'],
        language = Config['language'],
        dvdorder = dvdorder,
        cache=cache,
        apikey=api_key,
    )

    for episode in episodes_found:
        processFile(tvdb_instance, episode)
        p('')

    p("#" * 20)
    p("# Done")
    return episodes_found


def detect_shows(path):
    Config.update(defaults)
    #Config['verbose'] = True
    Config['force_name'] = None
    Config['series_id'] = None
    Config['select_first'] = True
    Config['always_rename'] = True
    Config['recursive'] = True
    Config['filename_with_episode'] = '%(seriesname)s - s%(seasonnumber)02de%(episode)s - %(episodename)s%(ext)s'

    extras = find_extras(path)
    print(extras)
    if extras is not None:
        Config['filename_blacklist'] = os.listdir(extras)

    episodes = tvnamer(paths=[path])
    return episodes

def find_extras(dir):
    for n_dir in os.scandir(dir):
        if n_dir.name.lower() == 'extras':
            return n_dir.path
        elif os.path.isdir(n_dir.path):
            return find_extras(n_dir.path)
        else:
            return None