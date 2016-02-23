# from savReaderWriter import SavReader
import logging
import os
import json

from glob import glob
import magic

import file_adapter as fa

from app import app

log = app.logger
log.setLevel(logging.DEBUG)


def read_cache(dataset_path):
    dataset_cache_filename = "{}.cache.json".format(dataset_path)

    if os.path.exists(dataset_cache_filename):
        with open(dataset_cache_filename, 'r') as dataset_cache_file:
            dataset_definition = json.load(dataset_cache_file)

        ## TODO: this is for backwards compatibility. Newer caches will contain the 'dataset' key
        if 'dataset' in dataset_definition:
            return dataset_definition
        else:
            return {'dataset': dataset_definition}
    else:
        return {}


def write_cache(dataset_path, dataset_definition):
    dataset_cache_filename = "{}.cache.json".format(dataset_path)

    with open(dataset_cache_filename, 'w') as dataset_cache_file:
        json.dump(dataset_definition, dataset_cache_file)

    log.debug("Written dataset definition to cache")


def load(dataset_name, relative_dataset_path, absolute_dataset_path):
    # First try to load from cache
    cached_dataset = read_cache(absolute_dataset_path)
    if cached_dataset != {}:
        log.info("Returning from cache")
        return cached_dataset

    # Otherwise, we'll read the actual file
    log.info("Building new dataset dictionary")

    # Specify the dataset's details
    # TODO: this is hardcoded, and needs to be gleaned from the dataset file metadata
    dataset = {
        'filename': absolute_dataset_path,
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
    write_cache(absolute_dataset_path, dataset_definition)

    return dataset_definition


def browse(parent_path, relative_path):

    absolute_path = os.path.join(parent_path, relative_path)
    log.debug('Browsing {}'.format(absolute_path))
    files = glob("{}/*".format(absolute_path))

    filelist = []
    for p in files:
        (pth, fn) = os.path.split(p)

        if fn[-3:] == 'csv':

            try:
                mymagic = magic.Magic(mimetype=True)
            except:
                mymagic = magic.Magic()
            mimetype = mymagic.from_file(p)

            if mimetype == "text/plain" and (fn[-3:] == "ttl" or fn[-2:] == 'n3'):
                mimetype = "text/turtle"
            if mimetype == "text/plain" and (fn[-3:] == "owl" or fn[-3:] == 'rdf'):
                mimetype = "application/rdf+xml"

            if os.path.isdir(p):
                filetype = 'dir'
            else:
                filetype = 'file'

            relative_p = os.path.relpath(p, parent_path)

            filelist.append({'label': fn, 'uri': relative_p, 'mimetype': mimetype, 'type': filetype})

    # Absolute parent is the absolute path of the parent of the current absolute path
    absolute_parent = os.path.abspath(os.path.join(absolute_path, os.pardir))
    # The relative parent is the relative path of the parent
    relative_parent = os.path.relpath(absolute_parent, parent_path)

    log.debug("base path " + parent_path)
    log.debug("absolute parent " + absolute_parent)
    log.debug("relative parent " + relative_parent)
    log.debug("constructed parent " + os.path.abspath(os.path.join(parent_path, '..')))

    if absolute_parent == os.path.abspath(os.path.join(parent_path, '..')) or '..' in relative_parent:
        print absolute_parent, relative_parent
        parent = None
    else:
        parent = {'label': '..', 'uri': relative_parent, 'mimetype': 'inode/directory', 'type': 'dir'}

    return filelist, parent
