# -*- coding: utf-8 -*-
from flask import render_template, request, jsonify
from flask_swagger import swagger
from werkzeug.exceptions import HTTPException
from rdflib import ConjunctiveGraph, Namespace, Literal, URIRef, RDF, RDFS, XSD

import shutil

import traceback
import logging
import json
import os
import gevent.subprocess as sp

import iribaker

import config
import util.sparql_client as sc
import util.file_client as fc
import util.git_client as git_client
import util.gitlab_client as gitlab_client
import util.dataverse_client as dc
import util.csdh_client as cc

from app import app, socketio

import importlib
converter = importlib.import_module("app.wp4-converters.src.converter")

# import datacube.converter

log = app.logger
log.setLevel(logging.DEBUG)


@app.route('/')
def index():
    return render_template('base.html')


@app.route('/api-docs')
def apidocs():
    return render_template('api-docs.html')


@app.route('/specs')
def specs():
    """
    Provides Swagger specification for the CSDH API
    ---
    tags:
        - Base
    responses:
        '200':
          description: Swagger specification
          type: object
        default:
          description: Unexpected error
          schema:
            $ref: "#/definitions/Message"
    """
    swag = swagger(app)
    swag['info']['version'] = "0.0.1"
    swag['info']['title'] = "CSDH API"
    swag['info']['description'] = """API Specification for
                                     the CLARIAH Structured Data Hub"""
    # swag['host'] = "api.clariah-sdh.eculture.labs.vu.nl"
    swag['host'] = app.config['SERVER_NAME']
    swag['schemes'] = ['http']
    swag['basePath'] = '/'
    swag['swagger'] = '2.0'

    return jsonify(swag)


@app.route('/trigger', methods=['POST'])
def follow_github():
    """
    Responds to triggers initiated by GitHub webhooks (if activated in the configuration)
    Make sure to set the appropriate parameters in `config.py`
    ---
      tags:
        - Base
      consumes:
        - text/json
      parameters:
        - name: data
          in: body
          description: The GitHub webhook payload
          required: true
          type: object
      responses:
        '200':
          description: Git repository updated
          type: object
          schema:
            $ref: "#/definitions/Message"
        default:
          description: Unexpected error
          schema:
            id: Message
            type: object
            properties:
              code:
                type: integer
                format: int32
              message:
                type: string
    """
    if not config.FOLLOW_GITHUB:
        raise(Exception("This application is not setup to respond to GitHub webhook data"))

    # Retrieve the data from POST
    data = json.loads(request.data)

    # Check whether the data is about the repository & branch we're
    # trying to track
    if (str(data['ref']) != config.FOLLOW_REF or
            str(data['repository']['url']) != config.FOLLOW_REPO):
        raise(Exception("""This application is not setup to respond to pushes to
                         this particular repository or branch"""))

    log.info("New commit by: {}".format(data['commits'][0]['author']['name']))
    log.info("Updating code repo")

    # Run the git pull command from the `src` directory (one up)
    message = sp.check_output(['git', 'pull'], cwd='..')

    # Format a response
    response = {'message': message, 'code': 200}
    return jsonify(response)


# Socket IO handlers
@socketio.on('message', namespace='/inspector')
def message(json):
    log.debug('SocketIO message:\n' + str(json))


@app.errorhandler(Exception)
def error_response(ex):
    """
    Handles any errors raised in the execution of the backend
    Builds a JSON representation of the error messages, to be handled by the client
    Complies with the Swagger definnition of an error response
    """
    if 'code' in ex:
        code = ex.code
    elif 'errno' in ex:
        code = ex.errno
    else:
        code = 42

    response = jsonify(message=str(ex), code=code)
    response.status_code = (code
                            if isinstance(ex, HTTPException)
                            else 500)

    log.error(traceback.format_exc())
    return response


@app.route('/dataset/definition')
def get_dataset_definition():
    """
    Get dataset metadata
    Loads the metadata for a dataset specified by the 'path' relative path argument.
    ---
      parameters:
        - name: path
          in: query
          description: The relative path of the dataset file that is to be loaded
          required: false
          type: string
          defaultValue: derived/utrecht_1829_clean_01.csv
      tags:
        - Dataset
      responses:
        '200':
          description: Dataset metadata retrieved
          schema:
            id: DatasetSchema
            type: object
            properties:
              name:
                type: string
                description: The name of the dataset
              path:
                type: string
                description: The location of the dataset on disk (server side)
              variables:
                description: A dictionary of variable names and values occurring in the dataset
                type: object
                properties:
                    default:
                        description: The default uri for this variable name
                        type: string
                    uri:
                        description: The assigned uri for this variable name
                        type: string
                    label:
                        description: The label for this variable name (i.e. the name itself)
                        type: string
                    description:
                        description: The description of the variable
                        type: string
                    category:
                        description: The category of the variable (coded, identifier, other, community)
                        type: string
                    type:
                        description: The DataCube type of the variable (sdmx:DimensionProperty, ... etc.)
                        type: string
                    codelist:
                        description: If appliccable, the codelist for this variable
                        type: object
                        properties:
                            default:
                                description: The default URI for the codelist
                                type: string
                            uri:
                                description: The assigned URI for the codelist
                                type: string
                            label:
                                description: The label for the codelist
                                type: string
                    values:
                        description: An array with values and frequencies for this variable name
                        additionalProperties:
                            description: The values and frequencies for this variable
                            schema:
                                type: object
                                items:
                                    type: object
                                    default:
                                        description: The default URI representation for this value
                                        type: string
                                    uri:
                                        description: The assigned URI representation for this value
                                        type: string
                                    label:
                                        description: The value as a label
                                        type: string
                                    literal:
                                        description: The assigned Literal representation for this value
                                    count:
                                        type: integer
                                        format: int32
            required:
                - name
                - path
                - mappings
                - values
        default:
          description: Unexpected error
          schema:
            $ref: "#/definitions/Message"
    """
    dataset_path = request.args.get('path', False)

    # Check whether a file path has been provided
    if not dataset_path:
        raise(Exception("""You should provide a relative path to
                        the file you want to load, and specify its name"""))

    dataset_name = os.path.basename(dataset_path)
    # Create an absolute path
    absolute_dataset_path = os.path.join(config.base_path, dataset_path)

    log.debug('Dataset path: ' + dataset_path)
    dataset_definition = fc.load(dataset_name, dataset_path, absolute_dataset_path)

    return jsonify(dataset_definition)


@app.route('/community/dimensions')
def get_community_dimensions():
    """
    Get a list of known community-defined dimensions
    Retrieves the dimensions gathered through the LSD dimensions website
    ---
    tags:
        - Community
    responses:
        '200':
            description: Community dimensions retrieved
            schema:
                id: CommunityDimensions
                type: object
                properties:
                    dimensions:
                        description: An array of specifications as provided by LSD
                        type: array
                        items:
                            type: object
                            properties:
                                id:
                                    description: The internal ID provided by LSD
                                    type: integer
                                    format: int32
                                label:
                                    description: The name of the dimension variable
                                    type: string
                                refs:
                                    description: The number of uses of the dimension in the LOD cloud
                                    type: integer
                                    format: int32
                                uri:
                                    description: The URI of the variable
                                    type: string
                                view:
                                    description:
                                        Some HTML for rendering the variable
                                        (ugly leftover, ignored)
                                    type: string
                            required:
                                - label
                                - refs
                                - uri
                required:
                    - dimensions
    default:
        description: Unexpected error
        schema:
          $ref: "#/definitions/Message"
    """
    dimensions_response = {'dimensions': cc.get_dimensions()}
    return jsonify(dimensions_response)


@app.route('/community/schemes')
def get_community_schemes():
    """
    Get a list of known community-defined concept schemes
    Retrieves concept schemes from the LOD Cloud and the CSDH
    ---
    tags:
        - Community
    responses:
        '200':
            description: Community concept schemes retrieved
            schema:
                type: object
                properties:
                    schemes:
                        description: An array of concept scheme labels and URIs
                        schema:
                            type: array
                            items:
                                description: An object specifying the label and URI of a concept scheme
                                type: object
                                properties:
                                    label:
                                        description: The name of the concept scheme
                                        type: string
                                    uri:
                                        description: The URI of the concept scheme
                                        type: string
                                required:
                                    - label
                                    - uri
                required:
                    - schemes
        default:
            description: Unexpected error
            schema:
              $ref: "#/definitions/Message"
    """
    schemes_response = {'schemes': cc.get_schemes() + cc.get_csdh_schemes()}
    return jsonify(schemes_response)


@app.route('/community/definition', methods=['GET'])
def get_community_definition():
    """
    Get the SDMX variable definition from the Web, LOD Cloud or CSDH if available
    First checks whether we already know the variable, otherwise resolves the URI
    of the variable as a URL, and retrieves its definition.
    ---
    tags:
        - Community
    parameters:
        - name: uri
          in: query
          description: The URI of the variable for which the definition is to be retrieved
          required: true
          type: string
          defaultValue: http://purl.org/linked-data/sdmx/2009/dimension#sex
    responses:
        '200':
            description: The variable definition was returned succesfully
            schema:
                type: object
                properties:
                    definition:
                        description: A variable definition
                        schema:
                            type: object
                            properties:
                                label:
                                    description: The name of the variable
                                    type: string
                                uri:
                                    description: The URI of the variable
                                    type: string
                                type:
                                    description: The DataCube type for the variable
                                    type: string
                                description:
                                    description: A description of the variable, if available
                                    type: string
                                codelist:
                                    description: An optional reference to a codelist URI for the variable
                                    schema:
                                        type: object
                                        properties:
                                            label:
                                                description: The name of the codelist
                                                type: string
                                            uri:
                                                description: The URI of the codelist
                                                type: string
                            required:
                                - uri
                required:
                    - definition
        default:
            description: Unexpected error
            schema:
              $ref: "#/definitions/Message"
    """
    uri = request.args.get('uri', False)

    if uri:
        variable_definition = cc.get_definition(uri)
        return jsonify({'definition': variable_definition})
    else:
        raise(Exception("No `uri` parameter given"))


@app.route('/community/concepts', methods=['GET'])
def codelist():
    """
    Get the list of concepts belonging to the code list
    Gets the SKOS Concepts belonging to the SKOS Scheme or Collection identified by the URI parameter
    ---
    tags:
        - Community
    parameters:
        - name: uri
          in: query
          description: The URI of the codelist for which the concepts are to be retrieved
          required: true
          type: string
          defaultValue: http://purl.org/linked-data/sdmx/2009/code#sex
    responses:
        '200':
            description: The codes were retrieved succesfully
            schema:
                type: object
                properties:
                    concepts:
                        description: A list of concepts belonging to the codelist
                        schema:
                            type: array
                            items:
                                description: A concept definition
                                schema:
                                    type: object
                                    properties:
                                        label:
                                            description: The preferred label of the concept
                                            type: string
                                        uri:
                                            description: The URI of the concept
                                            type: string
                                        notation:
                                            description: An optional (shorthand) notation of the concept
                                            type: string
                                    required:
                                        - label
                                        - uri
                required:
                    - concepts
        default:
            description: Unexpected error
            schema:
              $ref: "#/definitions/Message"
    """
    uri = request.args.get('uri', False)
    log.debug('Retrieving concepts for ' + uri)

    if uri:
        log.debug("Querying for SKOS concepts in Scheme or Collection <{}>".format(uri))

        codelist = cc.get_concepts(uri)

        if codelist == []:
            raise(Exception("Could not retrieve anything from LOD or CSDH"))
        else:
            return jsonify({'concepts': codelist})
    else:
        raise(Exception("Missing required parameter: `uri`"))


@app.route('/dataset/save', methods=['POST'])
def dataset_save():
    """
    Save the dataset to the CSDH file cache
    Note that this does not convert the dataset to RDF, nor does it upload it to the CSDH repository
    ---
    tags:
        - Dataset
    parameters:
        - name: dataset
          in: body
          description: The dataset definition that is to be saved to cache.
          required: true
          type: object
          schema:
            $ref: "#/definitions/DatasetSchema"
    responses:
        '200':
            description: The dataset was succesfully saved to the file cache
            schema:
                $ref: "#/definitions/Message"
        default:
            description: Unexpected error
            schema:
              $ref: "#/definitions/Message"
    """
    req_json = request.get_json(force=True)

    dataset = req_json['dataset']
    dataset_path = os.path.join(config.base_path, dataset['file'])

    fc.write_cache(dataset_path, {'dataset': dataset})
    return jsonify({'code': 200, 'message': 'Success'})

@app.route('/dataset/delete', methods=['GET'])
def dataset_delete():
    """
    Remove a dataset from the CSDH
    Note that this requires one to specify the Nanopublication URI, not the dataset URI
    **WARNING**: There is no authentication/authorization in place!
    ---
    tags:
        - Dataset
    parameters:
        - name: uri
          in: query
          description: The nanpublication URI of the dataset that is to be removed
          required: true
          type: string
    responses:
        '200':
            description: The dataset was succesfully removed from the SDH
            schema:
                $ref: "#/definitions/Message"
        default:
            description: Unexpected error
            schema:
              $ref: "#/definitions/Message"
    """
    uri = request.args.get('uri', None)

    if not uri:
        raise Exception('Must specify a Nanopublication URI!')

    message = cc.delete_dataset(uri)

    return jsonify({'code': 200, 'message': message})


@app.route('/dataset/list', methods=['GET'])
def dataset_list():
    """
    List the datasets currently available on the CSDH
    ---
    tags:
        - Dataset
    responses:
        '200':
            description: Dataset list retrieved
            schema:
              description: A list of datasets (the IRI of the nanopublication, the owner and the name)
              type: object
              properties:
                  datasets:
                      description: The list of datasets
                      type: array
                      items:
                        description: A dataset's name, IRI and owner
                        schema:
                          id: Dataset
                          type: object
                          properties:
                            label:
                              description: The name of the datasets
                              type: string
                            uri:
                              description: The IRI of the datasets
                              type: string
                            nanopublication:
                              description: The IRI of the Nanopublication
                              type: string
                            owner:
                              description: The IRI of the owner of the dataset
                              type: string
                          required:
                            - label
                            - uri
                            - owner
        default:
            description: Unexpected error
            schema:
              $ref: "#/definitions/Message"
    """

    dataset_list = cc.get_datasets()

    return jsonify({'datasets': dataset_list})


@app.route('/dataset/submit', methods=['POST'])
def dataset_submit():
    """
    Submit the dataset definition to the CSDH
    Uses the DataCube converter to convert the JSON representation of variables to RDF DataCube and commits
    the resulting RDF to the CSDH repository
    ---
    tags:
        - Dataset
    parameters:
        - name: dataset
          in: body
          description: The dataset definition that is to be converted and committed to the CSDH repository
          required: true
          schema:
            type: object
            properties:
                dataset:
                    description: The dataset definition
                    $ref: "#/definitions/DatasetSchema"
                user:
                    description: The Google user profile of the person uploading the dataset
                    type: object
    responses:
        '200':
            description: The dataset was converted succesfully
            schema:
                $ref: "#/definitions/Message"
        default:
            description: Unexpected error
            schema:
              $ref: "#/definitions/Message"
    """

    req_json = request.get_json(force=True)
    dataset = req_json['dataset']
    user = req_json['user']    
    filename = dataset['file'].split(".")[0]
    outfile = filename + ".nq"
    
    log.debug("Starting conversion ...")
    c = converter.Converter(dataset, config.base_path, user, target=outfile)
    c.setProcesses(1)
    c.convert()
    log.debug("Conversion successful")

    data = open(outfile, "rb")
    
    log.debug("Adding data to gitlab... ")
    url = gitlab_client.add_file(outfile, data.read())
    log.debug("Added to gitlab: " + url)

    log.debug("Parsing dataset... ")
    g = ConjunctiveGraph()
    
    data = open(outfile, "rb")
    g.parse(data, format="nquads")
    log.debug("DataSet parsed")
    
    for graph in g.contexts():
        log.debug(g)
        graph_uri = graph.identifier
        log.debug("Posting {} ...".format(graph_uri))
        sc.post_data(graph.serialize(format='turtle'), graph_uri=graph_uri)
        log.debug("... done")

    return jsonify({'code': 200, 'message': 'Succesfully submitted converted data to CSDH', 'url': url})



@app.route('/browse', methods=['GET'])
def browse():
    """
    Browse the dataset file cache
    Takes a relative path, and returns a list of files/directories at that location as JSON
    ---
      tags:
        - Base
      parameters:
        - name: path
          in: query
          description: The relative path to be browsed
          required: true
          type: string
          defaultValue: .
      responses:
        '200':
          description: Path retrieved
          schema:
            description: A path specification
            type: object
            properties:
                path:
                    description: The current path
                    type: string
                parent:
                    description: The parent path
                    type: string
                files:
                    description: The list of files found at this location
                    type: array
                    items:
                        description: A file, its path, name and its mimetype
                        schema:
                            id: FileInfo
                            type: object
                            properties:
                                label:
                                    description: The name of the file
                                    type: string
                                mimetype:
                                    description: The guessed mimetype of the file (libmagic)
                                    type: string
                                type:
                                    description: Whether it is a directory (dir) or normal file (file)
                                    type: string
                                uri:
                                    description: The relative path of the file
                                    type: string
                            required:
                                - label
                                - mimetype
                                - type
                                - uri
            required:
                - path
                - parent
                - files
        default:
          description: Unexpected error
          schema:
            id: Message
            type: object
            properties:
              code:
                type: integer
                format: int32
              message:
                type: string
    """
    path = request.args.get('path', None)

    if not path:
        raise Exception('Must specify a path!')

    log.debug('Will browse absolute path: {}/{}'.format(config.base_path, path))
    filelist, parent = fc.browse(config.base_path, path)

    return jsonify({'path': path, 'parent': parent, 'files': filelist})


@app.route('/dataverse/dataset', methods=['GET'])
def dataverse_dataset():
    """
    Retrieve the files for a study
    Takes a Handle or DOI, goes out to dataverse, and retrieves the files for the study dataset.
    ---
      tags:
        - Dataverse
      parameters:
        - name: handle
          in: query
          description: A handle to a dataset in the preconfigured Dataverse (e.g. a DOI or a Handle)
          type: string
          defaultValue: doi:10.7910/DVN/28993
      responses:
        '200':
          description: Path retrieved
          schema:
            description: A dataverse dataset (study)
            type: object
            properties:
                study:
                    description: The current study dataset
                    type: string
                files:
                    description: The list of TAB or CSV files found in this study
                    type: array
                    items:
                        description: A file, its path, name and its mimetype
                        schema:
                            id: FileInfo
                            type: object
                            properties:
                                label:
                                    description: The name of the file
                                    type: string
                                mimetype:
                                    description: The mimetype of the file
                                    type: string
                                type:
                                    description: The type (always 'dataverse')
                                    type: string
                                uri:
                                    description: The identifier of the file on dataverse
                                    type: string
                            required:
                                - label
                                - mimetype
                                - type
                                - uri
            required:
                - path
                - parent
                - files
        default:
            description: Unexpected error
            schema:
              $ref: "#/definitions/Message"
    """
    study_handle = request.args.get('handle', None)

    if not study_handle:
        raise Exception('Must specify a handle!')

    dataverse_connection = dc.Connection()

    dataverse_dataset = dataverse_connection.dataset(study_handle)
    dataset_files = dataverse_connection.retrieve_files(dataverse_dataset)

    log.debug(dataset_files)
    return jsonify({'study': study_handle, 'files': dataset_files})


@app.route('/dataverse/definition')
def dataverse_definition():
    """
    Get dataset metadata from a dataverse file
    Loads the metadata for a dataverse file specified by the id and name parameters.
    Response is the same as for `/dataset/definition`
    ---
      parameters:
        - name: name
          in: query
          description: The name of the dataset file that is to be loaded
          required: false
          type: string
          defaultValue: "Mortality.monthly_MadrasIndia.1916_1921.tab"
        - name: id
          in: query
          description:
            The id of a dataverse dataset file that is to be loaded
          required: false
          type: string
          defaultValue: 2531997
      tags:
        - Dataverse
      responses:
        '200':
          description: Dataset metadata retrieved
          schema:
            $ref: "#/definitions/DatasetSchema"
        default:
          description: Unexpected error
          schema:
            $ref: "#/definitions/Message"
    """
    dataset_id = request.args.get('id', False)
    dataset_name = request.args.get('name', False)

    # Check whether a file has been provided
    if not (dataset_id and dataset_name):
        raise(Exception("""You should provide a file id and name"""))

    dataverse_connection = dc.Connection()
    dataset_absolute_path = dataverse_connection.access(dataset_name, dataset_id, config.base_path)

    dataset_relative_path = os.path.relpath(dataset_absolute_path, config.base_path)
    dataset_definition = fc.load(dataset_name, dataset_relative_path, dataset_absolute_path)

    return jsonify(dataset_definition)


@app.route('/iri', methods=['GET'])
def iri():
    """
    Bake an IRI using iribaker
    Checks an IRI for compliance with RFC and converts invalid characters to underscores, if possible.
    **NB**: No roundtripping, this procedure may result in identity smushing: two input-IRI's may be
    mapped to the same output-IRI.
    ---
      tags:
        - Base
      consumes:
        - text/json
      parameters:
        - name: iri
          in: query
          description: The IRI to be checked for compliance
          required: true
          type: string
      responses:
        '200':
          description: IRI converted
          schema:
            description: A converted IRI result
            type: object
            properties:
                iri:
                    description: The fully compliant IRI
                    type: string
                source:
                    description: The input IRI
                    type: string
            required:
                - iri
                - source
        default:
          description: Unexpected error
          schema:
            id: Message
            type: object
            properties:
              code:
                type: integer
                format: int32
              message:
                type: string
    """

    unsafe_iri = request.args.get('iri', None)

    if unsafe_iri is not None:
        response = {'iri': iribaker.to_iri(unsafe_iri), 'source': unsafe_iri}
        return jsonify(response)
    else:
        raise(Exception("The IRI {} could not be converted to a compliant IRI".format(unsafe_iri)))


@app.after_request
def after_request(response):
    """
    Needed for Swagger UI
    """
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', "Authorization, Content-Type")
    response.headers.add('Access-Control-Expose-Headers', "Authorization")
    response.headers.add('Access-Control-Allow-Methods', "GET, POST, PUT, DELETE, OPTIONS")
    response.headers.add('Access-Control-Allow-Credentials', "true")
    response.headers.add('Access-Control-Max-Age', 60 * 60 * 24 * 20)
    return response
