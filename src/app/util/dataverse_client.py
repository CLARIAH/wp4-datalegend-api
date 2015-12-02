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

        params_str = "&".join("%s=%s" % (k,v) for k,v in params.items())
        url = self.search_url + "?" + params_str
        r = requests.get(url)

        return r.json()


    def dataset(self, identifier):
        """
        Calls the search API with the permanent identifier provided, and uses the returned entity_id
        to call the native API for dataset details.
        """
        entity_id = self.search('identifier:{}'.format(identifier))['data']['items'][0]['entity_id']

        params = copy(self.params)

        url = self.dataset_url.format(entity_id)

        r = requests.get(url,params)
        return r.json()['data']['latestVersion']


    def access(self, identifier):
        params = copy(self.params)

        url = self.access_url.format(identifier)
        r = requests.get(url,params)

        return r


    def retrieve_files(self, dataset_metadata, destination):
        tabcsvfile = ""
        for f in dataset_metadata['files']:
            print f['datafile']['id']
            if f['datafile']['contentType'] in ['text/tab-separated-values', 'text/csv']:
                print "This is a tab or csv file"
                r = self.access(f['datafile']['id'])

                if r.status_code == requests.codes.ok:
                    filename = os.path.join(destination, f['datafile']['name'])
                    tabcsvfile = f['datafile']['name']
                    print "Downloading to {}".format(filename)
                    with open(filename,'w') as datafile:
                        datafile.write(r.content)
                else:
                    raise(Exception('Cannot download file {}'.format(f['datafile']['name'])))

        # Temporarily return the last retrieved suitable file.
        return tabcsvfile
