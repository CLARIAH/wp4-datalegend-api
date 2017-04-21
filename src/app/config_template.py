# -*- coding: utf-8 -*-
# Copy this file to 'config.py' and make necessary changes for your local setup.
import os


# Add the converters module to the python path
import sys
sys.path.append("wp4-converters/src")

# Path to a directory where temporary files can be written
# (must be read/writable by the user that owns of the server process)
TEMP_PATH = os.environ('TEMP_PATH') or "/tmp"

# Base URI for resources
QBR_BASE = os.environ('QBR_BASE') or "http://data.socialhistory.org/resource/"

# Base URI for vocabulary
QBRV_BASE = os.environ('QBRV_BASE') or "http://data.socialhistory.org/vocab/"

# SPARQL Endpoint Configuration
ENDPOINT_URL = os.environ('ENDPOINT_URL') or '<URL OF SPARQL ENDPOINT>'
UPDATE_URL = os.environ('UPDATE_URL') or '<URL OF SPARQL UPDATE ENDPOINT>'

# Virtuoso specific stuff
CRUD_URL = os.environ('CRUD_URL') or '<CRUD URL>'
from requests.auth import HTTPDigestAuth
CRUD_USER = os.environ('CRUD_USER') or '<USER>'
CRUD_PASS = os.environ('CRUD_PASS') or '<PASS>'
CRUD_AUTH = HTTPDigestAuth(CRUD_USER, CRUD_PASS)

# Dataverse configuration
DATAVERSE_HOST = os.environ('DATAVERSE_HOST') or '<DATAVERSE_HOST>'  # e.g. dataverse.harvard.edu (without the http:// bit)
DATAVERSE_TOKEN = os.environ('DATAVERSE_TOKEN') or '<API TOKEN>'  # The API token key for connecting to dataverse

# Is the API running behind a proxy?
BEHIND_PROXY = os.environ('BEHIND_PROXY') or False

# Should the API log at DEBUG level?
DEBUG = os.environ('DEBUG') or True

# Stardog specific stuff
# (these are the default settings for HTTP Basic authenticating)
REASONING_TYPE = 'NONE'
AUTH = ('admin', 'admin')

# Respond to GitHub webhooks
FOLLOW_GITHUB = os.environ('FOLLOW_GITHUB') or True
FOLLOW_REPO = os.environ('FOLLOW_REPO') or 'https://github.com/CLARIAH/wp4-datalegend-api'
FOLLOW_REF = os.environ('FOLLOW_REF') or 'refs/heads/master'
