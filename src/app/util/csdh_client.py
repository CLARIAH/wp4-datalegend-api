import os
import json
import requests
import logging
from SPARQLWrapper import SPARQLWrapper, JSON
import sparql_client as sc
from rdflib import Graph
from threading import Thread


from app import app

log = app.logger
log.setLevel(logging.DEBUG)


def get_definition(uri):
    exists = sc.ask(uri, template="""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        ASK {{<{}> rdfs:label ?l .}}""")

    if not exists:
        success, visited = sc.resolve(uri, depth=2)
        print "Resolved ", visited
    else:
        success = True

    if success:
        query = """
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX qb: <http://purl.org/linked-data/cube#>

            SELECT (<{URI}> as ?uri) ?type ?label ?description ?concept_uri WHERE {{
                OPTIONAL
                {{
                    <{URI}>   rdfs:label ?label .
                }}
                OPTIONAL
                {{
                    <{URI}>   rdfs:comment ?description .
                }}
                OPTIONAL
                {{
                    <{URI}>   a  qb:DimensionProperty .
                    BIND(qb:DimensionProperty AS ?type )
                }}
                OPTIONAL
                {{
                    <{URI}>   qb:concept  ?measured_concept .
                }}
                OPTIONAL
                {{
                    <{URI}>   a  qb:MeasureProperty .
                    BIND(qb:MeasureProperty AS ?type )
                }}
                OPTIONAL
                {{
                    <{URI}>   a  qb:AttributeProperty .
                    BIND(qb:AttributeProperty AS ?type )
                }}
            }}

        """.format(URI=uri)

        results = sc.sparql(query)

        log.debug(results)

        # Turn into something more manageable, and take only the first element.
        variable_definition = sc.dictize(results)[0]

        query = """
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX qb: <http://purl.org/linked-data/cube#>

            SELECT DISTINCT ?uri ?label WHERE {{
                  <{URI}>   a               qb:CodedProperty .
                  BIND(qb:DimensionProperty AS ?type )
                  <{URI}>   qb:codeList     ?uri .
                  ?uri       rdfs:label      ?label .
            }}""".format(URI=uri)

        codelist_results = sc.sparql(query)

        log.debug(codelist_results)

        if len(codelist_results) > 0:
            codelist = sc.dictize(codelist_results)
            log.debug(codelist)
            # Only take the first result (won't allow multiple code lists)
            # TODO: Check how this potentially interacts with user-added codes and lists
            variable_definition['codelist'] = codelist[0]
        else:
            log.debug("No codelist for this variable")

        log.debug("Definition for: {}".format(uri))
        log.debug(variable_definition)

        return variable_definition
    else:
        raise(Exception("Could not find the definition for <{}> online, nor in the CSDH".format(uri)))


def get_dimensions():
    # Get the LSD dimensions from the LSD service (or a locally cached copy)
    # And concatenate it with the dimensions in the CSDH
    # Return an ordered dict of dimensions (ordered by number of references)

    dimensions = get_lsd_dimensions() + get_csdh_dimensions()

    # dimensions_as_dict = {dim['uri']: dim for dim in dimensions}
    sorted_dimensions = sorted(dimensions, key=lambda t: t['refs'])

    # sorted_dimensions = OrderedDict(sorted(dimensions_as_dict.items(), key=lambda t: t[1]['refs']))
    return sorted_dimensions


def get_lsd_dimensions():
    """Loads the list of Linked Statistical Data dimensions (variables) from the LSD portal"""
    # TODO: Create a local copy that gets updated periodically

    try:
        if os.path.exists('metadata/dimensions.json'):
            log.debug("Loading dimensions from file...")
            with open('metadata/dimensions.json', 'r') as f:
                dimensions_json = f.read()
            log.debug("Dimensions loaded...")
            dimensions = json.loads(dimensions_json)
        else:
            raise Exception("Could not load dimensions from file...")
    except Exception as e:
        log.warning(e)
        dimensions_response = requests.get("http://amp.ops.few.vu.nl/data.json")
        log.debug("Loading dimensions from LSD service...")
        try:
            dimensions = json.loads(dimensions_response.content)

            if len(dimensions_response) > 1:
                with open('metadata/dimensions.json', 'w') as f:
                    f.write(dimensions_response)
            else:
                raise Exception("Could not load dimensions from service")

        except Exception as e:
            log.error(e)

            dimensions = []

    dimensions = [dim for dim in dimensions if dim['refs'] > 1]
    return dimensions


def get_csdh_dimensions():
    """Loads the list of Linked Statistical Data dimensions (variables) from the CSDH"""
    log.debug("Loading dimensions from the CSDH")
    query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dct: <http://purl.org/dc/terms/>
        PREFIX qb: <http://purl.org/linked-data/cube#>

        SELECT DISTINCT ?uri ?label ("CSDH" as ?refs) WHERE {
          {
              ?uri a qb:DimensionProperty .
              ?uri rdfs:label ?label .
          }
          UNION
          {
              ?uri a qb:MeasureProperty .
              ?uri rdfs:label ?label .
          }
          UNION
          {
              ?uri a qb:AttributeProperty .
              ?uri rdfs:label ?label .
          }
        }
    """
    sdh_dimensions_results = sc.sparql(query)
    try:
        if len(sdh_dimensions_results) > 0:
            sdh_dimensions = sc.dictize(sdh_dimensions_results)
        else:
            sdh_dimensions = []
    except Exception as e:
        log.error(e)
        sdh_dimensions = []

    return sdh_dimensions


def get_csdh_schemes():
    """Loads SKOS Schemes (code lists) from the CSDH"""
    log.debug("Querying CSDH Cloud")

    query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dct: <http://purl.org/dc/terms/>

        SELECT DISTINCT ?uri ?label WHERE {
          {
              ?c skos:inScheme ?uri .
              ?uri rdfs:label ?label .
          }
          UNION
          {
              ?uri skos:member ?c .
              ?uri rdfs:label ?label .
          }

        }
    """

    schemes_results = sc.sparql(query)
    log.debug(schemes_results)
    schemes = sc.dictize(schemes_results)

    log.debug(schemes)

    return schemes


def get_schemes():
    """Loads SKOS Schemes (code lists) either from the LOD Cache, or from a cached copy"""
    if os.path.exists('metadata/schemes.json'):
        # TODO: Check the age of this file, and update if older than e.g. a week.
        log.debug("Loading schemes from file...")
        with open('metadata/schemes.json', 'r') as f:
            schemes_json = f.read()

        schemes = json.loads(schemes_json)
        return schemes
    else:
        log.debug("Loading schemes from RDF sources...")
        schemes = []

        # ---
        # Querying the LOD Cloud
        # ---
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
        # ---
        # Querying the HISCO RDF Specification (will become a call to a
        # generic CLARIAH Vocabulary Portal thing.)
        # ---
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

        with open('metadata/schemes.json', 'w') as f:
            f.write(schemes_json)

        return schemes


def get_concepts(uri):
    query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dct: <http://purl.org/dc/terms/>

        SELECT DISTINCT ?uri ?label ?notation WHERE {{
          {{ ?uri skos:inScheme <{URI}> . }}
          UNION
          {{ <{URI}> skos:member+ ?uri . }}
          ?uri skos:prefLabel ?label .
          OPTIONAL {{ ?uri skos:notation ?notation . }}
        }}
    """.format(URI=uri)

    lod_codelist = []
    sdh_codelist = []

    try:
        log.debug("Querying the LOD cloud cache")
        # First we go to the LOD cloud
        sparql = SPARQLWrapper('http://lod.openlinksw.com/sparql')
        sparql.setTimeout(1)
        sparql.setReturnFormat(JSON)
        sparql.setQuery(query)

        lod_codelist_results = sparql.query().convert()['results']['bindings']
        if len(lod_codelist_results) > 0:
            lod_codelist = sc.dictize(lod_codelist_results)
        else:
            lod_codelist = []

        log.debug(lod_codelist)
    except Exception as e:
        log.error(e)
        log.error('Could not retrieve anything from the LOD cloud')
        lod_codelist = []

    try:
        log.debug("Querying the SDH")
        # Then we have a look locally
        sdh_codelist_results = sc.sparql(query)
        if len(sdh_codelist_results) > 0:
            sdh_codelist = sc.dictize(sdh_codelist_results)
        else:
            sdh_codelist = []

        log.debug(sdh_codelist)

    except Exception as e:
        log.error(e)
        log.error('Could not retrieve anything from the SDH')
        sdh_codelist = []

    return lod_codelist + sdh_codelist


def get_datasets():
    query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX np: <http://www.nanopub.org/nschema#>
        PREFIX qb: <http://purl.org/linked-data/cube#>
        PREFIX prov: <http://www.w3.org/ns/prov#>

        SELECT DISTINCT ?uri ?label ?owner ?nanopublication WHERE {
          ?nanopublication a         np:Nanopublication ;
               np:hasAssertion       ?assertion_uri ;
               np:hasPublicationInfo ?pubinfo_uri .

          GRAPH ?assertion_uri {
            ?uri         a                    qb:DataSet ;
                         rdfs:label           ?label .
          }
          GRAPH ?pubinfo_uri {
            ?nanopublication         prov:wasAttributedTo ?owner .
          }
        }
    """

    dataset_list = []

    try:
        log.debug("Querying the SDH")
        # Then we have a look locally
        sdh_datasets_results = sc.sparql(query)
        if len(sdh_datasets_results) > 0:
            dataset_list = sc.dictize(sdh_datasets_results)
        else:
            dataset_list = []

        log.debug(dataset_list)

    except Exception as e:
        log.error(e)
        log.error('Could not retrieve anything from the SDH')
        dataset_list = []

    return dataset_list


def delete_dataset(uri):
    log.warning("TODO: Untested! Unsafe!")
    uri = uri.strip()

    query = """
        PREFIX np: <http://www.nanopub.org/nschema#>

        SELECT DISTINCT ?assertion_uri ?pubinfo_uri ?provenance_uri WHERE {{
            <{URI}> a         np:Nanopublication ;
               np:hasAssertion       ?assertion_uri ;
               np:hasPublicationInfo ?pubinfo_uri ;
               np:hasProvenance      ?provenance_uri .
        }}
    """.format(URI=uri)

    def clear_graph(uri):
        clear_query_template = """
            DEFINE sql:log-enable 2
            CLEAR GRAPH <{}>
        """
        clear_query = clear_query_template.format(uri)
        log.debug("Clearing graph {}".format(uri))
        return sc.sparql_update(clear_query)

    def delete_publication(uri):
        delete_query = """
            PREFIX np: <http://www.nanopub.org/nschema#>

            DELETE {{ GRAPH ?g {{
              <{URI}> a         np:Nanopublication ;
                   np:hasAssertion       ?assertion_uri ;
                   np:hasPublicationInfo ?pubinfo_uri ;
                   np:hasProvenance      ?provenance_uri .
                ?assertion_uri a    np:Assertion .
                ?pubinfo_uri a      np:PublicationInfo .
                ?provenance_uri a   np:Provenance .
            }}}}
            WHERE {{ GRAPH ?g {{
              <{URI}> a         np:Nanopublication ;
                   np:hasAssertion       ?assertion_uri ;
                   np:hasPublicationInfo ?pubinfo_uri ;
                   np:hasProvenance      ?provenance_uri .
                ?assertion_uri a    np:Assertion .
                ?pubinfo_uri a      np:PublicationInfo .
                ?provenance_uri a   np:Provenance .
            }}}}
        """.format(URI=uri)

        log.debug("Removing the nanopublication {}...".format(uri))
        return sc.sparql_update(delete_query)


    nanopub = {}

    try:
        log.debug("Querying the SDH")
        # Then we have a look locally
        nanopub_results = sc.sparql(query)
        if len(nanopub_results) > 0:
            nanopub = sc.dictize(nanopub_results)[0]
            log.debug(nanopub)

            t_assertion = Thread(target=clear_graph, args=(nanopub['assertion_uri'],))
            t_assertion.start()
            t_provenance = Thread(target=clear_graph, args=(nanopub['provenance_uri'],))
            t_provenance.start()
            t_pubinfo = Thread(target=clear_graph, args=(nanopub['pubinfo_uri'],))
            t_pubinfo.start()
            t_publication = Thread(target=delete_publication, args=(uri,))
            t_publication.start()

            return "Called delete functions for {}".format(uri)
        else:
            return "No matching nanopublication found"

        log.debug(nanopub)
    except Exception as e:
        log.error(e)
        log.error("Could not retrieve anything from the SDH")
        log.debug(nanopub_results)
        return "Could not retrieve anything from the SDH"

    return "Not implemented"
