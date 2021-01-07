
import logging
import os

import tvdb_api
from tvdb_api import Tvdb
from tvnamer.compat import PY2, raw_input
from tvnamer.config import Config
from tvnamer.config_defaults import defaults
from tvnamer.main import FileParser, findFiles
from tvnamer.tvnamer_exceptions import (DataRetrievalError,
                                        EpisodeNameNotFound, EpisodeNotFound,
                                        InvalidFilename, InvalidPath,
                                        NoValidFilesFoundError, SeasonNotFound,
                                        ShowNotFound, SkipBehaviourAbort,
                                        UserAbort)
from tvnamer.unicode_helper import p

import tvnamer.utils
from tvnamer.utils import Renamer

LOG = logging.getLogger(__name__)
TVNAMER_API_KEY = "fb51f9b848ffac9750bada89ecba0225"

errors = []

def warn(text):
    if text not in errors:
        errors.append(text)


tvnamer.utils.warn = warn

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

def processFile(tvdb_instance, episode):
    """Gets episode name, prompts user for input
    """
    p("#" * 20)
    p("# Processing file: %s" % episode.fullfilename)

    if len(Config['input_filename_replacements']) > 0:
        replaced = applyCustomInputReplacements(episode.fullfilename)
        p("# With custom replacements: %s" % (replaced))

    # Use force_name option. Done after input_filename_replacements so
    # it can be used to skip the replacements easily
    if Config['force_name'] is not None:
        episode.seriesname = Config['force_name']

    p("# Detected series: %s (%s)" % (episode.seriesname, episode.number_string()))

    try:
        episode.populateFromTvdb(tvdb_instance, force_name=Config['force_name'], series_id=Config['series_id'])
    except (DataRetrievalError, ShowNotFound) as errormsg:
        if Config['always_rename'] and Config['skip_file_on_error'] is True:
            if Config['skip_behaviour'] == 'exit':
                warn("Exiting due to error: %s" % errormsg)
                raise SkipBehaviourAbort()
            warn("Skipping file due to error: %s" % errormsg)
            return
        else:
            warn(errormsg)
    except (SeasonNotFound, EpisodeNotFound, EpisodeNameNotFound) as errormsg:
        # Show was found, so use corrected series name
        if Config['always_rename'] and Config['skip_file_on_error']:
            if Config['skip_behaviour'] == 'exit':
                warn("Exiting due to error: %s" % errormsg)
                raise SkipBehaviourAbort()
            warn("Skipping file due to error: %s" % errormsg)
            return

        warn(errormsg)

    cnamer = Renamer(episode.fullpath)


    shouldRename = False

    if Config["move_files_only"]:

        newName = episode.fullfilename
        shouldRename = True

    else:
        newName = episode.generateFilename()
        episode.generatedfilename = newName
        if newName == episode.fullfilename:
            p("#" * 20)
            p("Existing filename is correct: %s" % episode.fullfilename)
            p("#" * 20)

            shouldRename = True

        else:
            p("#" * 20)
            p("Old filename: %s" % episode.fullfilename)

            if len(Config['output_filename_replacements']) > 0:
                # Show filename without replacements
                p("Before custom output replacements: %s" % (episode.generateFilename(preview_orig_filename = False)))

            p("New filename: %s" % newName)

            if Config['dry_run']:
                p("%s will be renamed to %s" % (episode.fullfilename, newName))
                if Config['move_files_enable']:
                    p("%s will be moved to %s" % (newName, getMoveDestination(episode)))
                return
            elif Config['always_rename']:
                doRenameFile(cnamer, newName)
                if Config['move_files_enable']:
                    if Config['move_files_destination_is_filepath']:
                        doMoveFile(cnamer = cnamer, destFilepath = getMoveDestination(episode))
                    else:
                        doMoveFile(cnamer = cnamer, destDir = getMoveDestination(episode))
                return

            ans = confirm("Rename?", options = ['y', 'n', 'a', 'q'], default = 'y')

            if ans == "a":
                p("Always renaming")
                Config['always_rename'] = True
                shouldRename = True
            elif ans == "q":
                p("Quitting")
                raise UserAbort("User exited with q")
            elif ans == "y":
                p("Renaming")
                shouldRename = True
            elif ans == "n":
                p("Skipping")
            else:
                p("Invalid input, skipping")

            if shouldRename:
                doRenameFile(cnamer, newName)

    if shouldRename and Config['move_files_enable']:
        newPath = getMoveDestination(episode)
        if Config['dry_run']:
            p("%s will be moved to %s" % (newName, getMoveDestination(episode)))
            return

        if Config['move_files_destination_is_filepath']:
            doMoveFile(cnamer = cnamer, destFilepath = newPath, getPathPreview = True)
        else:
            doMoveFile(cnamer = cnamer, destDir = newPath, getPathPreview = True)

        if not Config['batch'] and Config['move_files_confirmation']:
            ans = confirm("Move file?", options = ['y', 'n', 'q'], default = 'y')
        else:
            ans = 'y'

        if ans == 'y':
            p("Moving file")
            doMoveFile(cnamer, newPath)
        elif ans == 'q':
            p("Quitting")
            raise UserAbort("user exited with q")


def detect_shows(path, dry_run):
    errors = []
    Config.update(defaults)
    #Config['verbose'] = True
    Config['force_name'] = None
    Config['series_id'] = None
    Config['select_first'] = True
    Config['always_rename'] = True
    Config['recursive'] = True
    Config['filename_with_episode'] = '%(seriesname)s - s%(seasonnumber)02de%(episode)s - %(episodename)s%(ext)s'
    Config['dry_run'] = dry_run
    Config['filename_blacklist'] = ['.DS_Store']

    extras = find_extras(path)
    if extras is not None:
        Config['filename_blacklist'] += os.listdir(extras)

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