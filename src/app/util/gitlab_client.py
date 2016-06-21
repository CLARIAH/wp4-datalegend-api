import logging
import gitlab

import os
import json
import base64
import traceback

from datetime import datetime
from tempfile import NamedTemporaryFile

import file_adapter as fa

from app import app

log = app.logger
log.setLevel(logging.DEBUG)


PRIVATE_TOKEN = "ZDMRh1o7xCmigmxK8hqK"
PROJECT = 15

git = gitlab.Gitlab('http://gitlab.clariah-sdh.eculture.labs.vu.nl', token=PRIVATE_TOKEN)


def list_projects():
    projects = list(git.getall(git.getprojects))

    return projects


def get_project_info():
    try:
        info = git.getproject(PROJECT)
        log.debug("Retrieved project info from Gitlab for project {}".format(PROJECT))
        return info
    except:
        log.error("Could not retrieve project info for project {}".format(PROJECT))


def browse(base_path, relative_path):
    # @base_path is necessary for legacy purposes (file browser)
    # TODO: This currently does not work as it should, as the way we have to compute
    # the parent path of the current path is unclear (we don't have that information)

    log.debug('Browsing {}'.format(relative_path))

    # make sure that Gitlab understands what we mean by '.'
    if relative_path == '.':
        relative_path = ''

    # remove any preceding slashes, as GitLab doesn't understand this.
    relative_path = relative_path.lstrip('/')

    files = git.getrepositorytree(PROJECT, path=relative_path, ref_name='master')
    log.debug("Found files: {}".format(files))

    filelist = []
    for p in files:
        log.debug("Found {}".format(p['name']))
        path = "{}/{}".format(relative_path, p['name'])
        if p['name'][-3:] == 'csv':
            filelist.append({'label': p['name'], 'uri': path, 'version': p['id'], 'mimetype': 'text/csv', 'type': 'file'})
        elif p['type'] == 'tree':
            filelist.append({'label': p['name'], 'uri': path, 'version': p['id'], 'mimetype': 'inode/directory', 'type': 'dir'})

    [parent_path, _] = os.path.split(relative_path)

    log.debug("Parent: {}".format(parent_path))
    # TODO: This is where things break.
    if relative_path is '':
        parent = None
    else:
        parent = {'label': '..', 'uri': parent_path, 'mimetype': 'inode/directory', 'type': 'dir'}

    return filelist, parent


def get_file(file_path, format="CSV"):
    file_info = _get_file_info(file_path)

    file_info['content'] = base64.b64decode(file_info['content'])

    # TODO: completely untested
    if format != "JSON":
        return file_info
    else:
        file_info['content'] = json.loads(file_info['content'])
        return file_info

def _get_file_info(file_path):
    project_info = git.getproject(PROJECT)
    file_info = git.getfile(PROJECT, file_path, "master")
    log.debug(file_info)
    if file_info is not False:
        # Add 'url' to file_info
        file_info['url'] = project_info["web_url"] + "/raw/" + file_info["ref"] + "/" + file_info["file_path"]

        return file_info
    else:
        raise Exception("Could not find file on GitLab: {}".format(file_path))


def add_file(gitlab_file_path, content):
    success = git.updatefile(PROJECT,
                             gitlab_file_path,
                             "master",
                             content,
                             "File uploaded by datalegend API {}".format(datetime.utcnow().isoformat()))

    if success:
        log.debug("Successfully added file to GitLab server")
        # This is really over the top for large files!!
        file_info = get_file(gitlab_file_path)

        return file_info
    else:
        log.error("Could not upload file to GitLab server")
        raise Exception("Could not upload file to GitLab server")


def read_cache(dataset_path):
    dataset_cache_filename = "{}.cache.json".format(dataset_path)

    try:
        dataset_definition = get_file(dataset_cache_filename, format='JSON')['content']

        # TODO: this is for backwards compatibility. Newer caches will contain the 'dataset' key
        if 'dataset' in dataset_definition:
            return dataset_definition
        else:
            return {'dataset': dataset_definition}
    except:
        log.debug(traceback.format_exc())
        log.info("Could not find cache file {}".format(dataset_path))

        return {}

def write_cache(dataset_path, dataset_definition):
    dataset_cache_path = "{}.cache.json".format(dataset_path)

    add_file(dataset_cache_path, json.dumps(dataset_definition))

    log.debug("Written dataset definition to cache")


# TODO: Copied from File Client
def load(dataset_name, relative_dataset_path):

    # First try to load from cache
    cached_dataset = read_cache(relative_dataset_path)
    if cached_dataset != {}:
        log.info("Returning from cache")
        return cached_dataset

    # Otherwise, we'll read the actual file
    log.info("Building new dataset dictionary")

    dataset_info = get_file(relative_dataset_path)
    dataset_content = dataset_info['content']

    log.debug(dataset_content)

    [_, dataset_filename] = os.path.split(relative_dataset_path)

    f = NamedTemporaryFile(suffix=dataset_filename, delete=False)
    f.write(dataset_content)
    f.close()

    # Specify the dataset's details
    # TODO: this is hardcoded, and needs to be gleaned from the dataset file metadata
    dataset = {
        'filename': f.name,
        'name': dataset_name,
        'version': dataset_info['commit_id'],
        'header': True
    }

    log.debug("Initializing adapter for dataset")
    # Intialize a file a dapter for the dataset
    adapter = fa.get_adapter(dataset)

    log.debug("Preparing dataset definition")
    # Prepare the data dictionary
    dataset_definition = {'dataset': {
        'name': adapter.get_dataset_name(),
        'uri': adapter.get_dataset_uri(),
        'file': relative_dataset_path,
        'variables': adapter.get_values(),
    }}

    # We write what we've read to cache
    write_cache(relative_dataset_path, dataset_definition)

    return dataset_definition
