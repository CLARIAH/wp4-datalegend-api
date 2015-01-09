# -*- coding: utf-8 -*-
from flask import render_template, g, request, jsonify, make_response, redirect, url_for, abort
from werkzeug.http import parse_accept_header
import logging
import requests
import json
import os
from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import Graph

import config

from app import app

from util.file_client import get_header
import loader.reader

log = app.logger
log.setLevel(logging.DEBUG)

@app.route('/')
def index():
    adapter = loader.reader.go('loader/canada.json',0)
    
    variables = adapter.get_header()
    metadata = adapter.get_metadata()
    examples = adapter.get_examples()
    short_metadata = {metadata.keys()[0]: metadata[metadata.keys()[0]]}
    
    dimensions = get_dimensions()
    schemes = get_schemes()
    
    
    
    return render_template('variables.html', variables=variables, metadata=metadata, examples=examples, dimensions=json.dumps(dimensions), schemes=json.dumps(schemes))

def get_dimensions():
    
    dimensions_response = requests.get("http://amp.ops.few.vu.nl/data.json")
    dimensions = json.loads(dimensions_response.content)
    
    return dimensions

def get_schemes():
    if os.path.exists('metadata/schemes.json'):
        log.debug("Loading schemes from file...")
        with open('metadata/schemes.json','r') as f:
            schemes_json = f.read()
        
        schemes = json.loads(schemes_json)
        return schemes
    else :
        log.debug("Loading schemes from RDF sources")
        schemes = []
    
        ### ---
        ### Querying the LOD Cloud
        ### ---
        log.debug("Querying LOD Cloud")

        query = """
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dct: <http://purl.org/dc/terms/>

            SELECT DISTINCT ?scheme ?label WHERE {
              ?c skos:inScheme ?scheme .
              ?scheme rdfs:label ?label . 
            } 
        """
    
        sparql = SPARQLWrapper('http://lod.openlinksw.com/sparql')
        sparql.setReturnFormat(JSON)
        sparql.setQuery(query)
    
        results = sparql.query().convert()
    
        for r in results['results']['bindings']:
            scheme = {}
        
            scheme['label'] = r['label']['value']
            scheme['uri'] = r['scheme']['value']
            schemes.append(scheme)
        
        log.debug("Found {} schemes".format(len(schemes)))
        ### ---
        ### Querying the HISCO RDF Specification (will become a call to a generic CLARIAH Vocabulary Portal thing.)
        ### ---
        log.debug("Querying HISCO RDF Specification")
    
        query = """
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dct: <http://purl.org/dc/terms/>

            SELECT DISTINCT ?scheme ?label WHERE {
              ?scheme a skos:ConceptScheme.
              ?scheme dct:title ?label . 
            } 
        """
    
        g = Graph()
        g.parse('metadata/hisco.ttl', format='turtle')
    
        results = g.query(query)
        
        for r in results:
            scheme = {}
            scheme['label'] = r.label
            scheme['uri'] = r.scheme
            schemes.append(scheme)
        
        log.debug("Found a total of {} schemes".format(len(schemes)))
    
        schemes_json = json.dumps(schemes)
    
        with open('metadata/schemes.json','w') as f:
            f.write(schemes_json)
    
        return schemes
        
    
