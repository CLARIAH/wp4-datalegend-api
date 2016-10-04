# -*- coding: utf-8 -*-
# Copy this file to 'config.py' and make necessary changes for your local setup.

# Path to a directory where temporary files can be written
# (must be read/writable by the user that owns of the server process)
TEMP_PATH = "/tmp"

# Base URI for resources
QBR_BASE = "http://data.socialhistory.org/ns/resource/"

# Base URI for vocabulary
QBRV_BASE = "http://data.socialhistory.org/ns/vocab/"

# SPARQL Endpoint Configuration
ENDPOINT_URL = '<URL OF SPARQL ENDPOINT>'
UPDATE_URL = '<URL OF SPARQL UPDATE ENDPOINT>'

# Virtuoso specific stuff
CRUD_URL = '<CRUD URL>'
from requests.auth import HTTPDigestAuth
CRUD_AUTH = HTTPDigestAuth('<USER>', '<PASS>')

# Dataverse configuration
DATAVERSE_HOST = '<DATAVERSE_HOST>'  # e.g. dataverse.harvard.edu (without the http:// bit)
DATAVERSE_TOKEN = '<API TOKEN>'  # The API token key for connecting to dataverse

# Is the API running behind a proxy?
BEHIND_PROXY = False

# Should the API log at DEBUG level?
DEBUG = True

# Stardog specific stuff
# (these are the default settings for HTTP Basic authenticating)
REASONING_TYPE = 'NONE'
AUTH = ('admin', 'admin')

# Respond to GitHub webhooks
FOLLOW_GITHUB = True
FOLLOW_REPO = 'https://github.com/CLARIAH/wp4-datalegend-api'
FOLLOW_REF = 'refs/heads/master'
