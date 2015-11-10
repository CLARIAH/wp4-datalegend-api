# -*- coding: utf-8 -*-
# Copy this file to 'config.py' and make necessary changes for your local setup.
import os

base_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "<RELATIVE PATH TO DATA FOLDER>"))

# Base URI for resources
QBR_BASE = "http://data.socialhistory.org/resource/"

# Base URI for vocabulary
QBRV_BASE = "http://data.socialhistory.org/vocab/"

# SPARQL Endpoint Configuration
ENDPOINT_URL = '<URL OF SPARQL ENDPOINT>'
UPDATE_URL = '<URL OF SPARQL UPDATE ENDPOINT>'

# Virtuoso specific stuff
CRUD_URL = '<CRUD URL>'
from requests.auth import HTTPDigestAuth
CRUD_AUTH = HTTPDigestAuth('<USER>', '<PASS>')

# Is the API running behind a proxy?
BEHIND_PROXY = False

# Should the API log at DEBUG level?
DEBUG = True

# Stardog specific stuff
# (these are the default settings for HTTP Basic authenticating)
REASONING_TYPE = 'NONE'
AUTH = ('admin','admin')

# Respond to GitHub webhooks
FOLLOW_GITHUB = True
FOLLOW_REPO = 'https://github.com/CLARIAH/wp4-csdh-api'
FOLLOW_REF = 'refs/heads/master'
