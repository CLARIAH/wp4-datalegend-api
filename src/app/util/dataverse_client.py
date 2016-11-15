import requests
from copy import copy
import app.config as config
import os


class Connection(object):

    def __init__(self, host=config.DATAVERSE_HOST, token=config.DATAVERSE_TOKEN):
        self.host = host
        self.token = token

        self.params = {
            'key': token
        }

        # Setup connection urls
        self.search_url = "http://{}/api/search".format(host)
        self.dataset_url = "http://{}/api/datasets/{{}}".format(host)
        self.access_url = "http://{}/api/access/datafile/{{}}".format(host)

    def search(self, query, dv_type=None):
        """
        Calls the search API of the Dataverse installation with the provided query string
        Returns a dictionary
        """
        params = copy(self.params)
        params['q'] = query

        if dv_type:
            params['type'] = dv_type
        params['show_entity_ids'] = True

        params_str = "&".join("%s=%s" % (k, v) for k, v in params.items())
        url = self.search_url + "?" + params_str
        r = requests.get(url)

        return r.json()

    def dataset(self, identifier):
        """
        Calls the search API with the permanent identifier provided, and uses the returned entity_id
        to call the native API for dataset details.
        """

        # Check whether the identifier has the expected format
        identifier = identifier.strip().replace('http://dx.doi.org/', 'doi:')
        identifier = identifier.strip().replace('http://hdl.handle.net/', 'hdl:')

        # Default to doi: prefix is no prefix is provided
        if not (identifier.startswith('doi:') or identifier.startswith('hdl:')):
            identifier = 'doi:{}'.format(identifier)

        try:
            entity_id = self.search('identifier:{}'.format(identifier))['data']['items'][0]['entity_id']

            params = copy(self.params)

            url = self.dataset_url.format(entity_id)

            r = requests.get(url, params)
            return r.json()['data']['latestVersion']
        except:
            raise(Exception('No results found for {}'.format(identifier)))

    def access(self, name, identifier, destination):
        params = copy(self.params)

        url = self.access_url.format(identifier)
        r = requests.get(url, params)

        if r.status_code == requests.codes.ok:
            filename = os.path.join(destination, name)
            print "Downloading to {}".format(filename)
            with open(filename, 'w') as datafile:
                datafile.write(r.content)
        else:
            raise(Exception('Cannot download file {}'.format(name)))

        return filename

    def get_access_url(self, identifier):
        url = self.access_url.format(identifier)

        return url

    def retrieve_files(self, dataset_metadata):
        files = []
        for f in dataset_metadata['files']:
            print f['dataFile']

            if f['dataFile']['contentType'] in ['text/tab-separated-values', 'text/csv']:
                print "This is a tab or csv file"

                files.append(
                    {'label': f['dataFile']['filename'],
                     'uri': str(f['dataFile']['id']),
                     'mimetype': f['dataFile']['contentType'],
                     'type': 'dataverse'}
                )

        # And return the list of files...
        return files
