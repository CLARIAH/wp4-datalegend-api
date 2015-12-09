from rdflib import Dataset, Namespace, Literal, URIRef, RDF, RDFS, XSD
import datetime
import iribaker

QBRV = Namespace('http://data.socialhistory.org/vocab/')
QBR = Namespace('http://data.socialhistory.org/resource/')

QB = Namespace('http://purl.org/linked-data/cube#')
SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
PROV = Namespace('http://www.w3.org/ns/prov#')
NP = Namespace('http://www.nanopub.org/nschema#')
FOAF = Namespace('http://xmlns.com/foaf/0.1/')


def safe_url(NS, local):
    """Generates a URIRef from the namespace + local part that is safe for
    use in RDF graphs

    Arguments:
    NS      -- a @Namespace object
    local   -- the local name of the resource
    """
    return URIRef(iribaker.to_iri(NS[local]))


def get_base_uri(dataset):
    return Namespace('http://data.socialhistory.org/resource/{}/'.format(dataset))


def get_value_uri(dataset, variable, value):
    """Generates a variable value IRI for a given combination of dataset, variable and value"""
    BASE = get_base_uri(dataset)

    return iribaker.to_iri(BASE['code/' + variable + '/' + value])


def get_variable_uri(dataset, variable):
    """Generates a variable IRI for a given combination of dataset and variable"""
    BASE = get_base_uri(dataset)

    return iribaker.to_iri(BASE[variable])


def data_structure_definition(profile, dataset_name, dataset_base_uri, variables, source_path, source_hash):
    """Converts the dataset + variables to a set of rdflib Graphs (a nanopublication with provenance annotations)
    that contains the data structure definition (from the DataCube vocabulary) and
    the mappings to external datasets.

    Arguments:
    dataset     -- the name of the dataset
    variables   -- the list of dictionaries with the variables and their mappings to URIs
    profile     -- the Google signin profile
    source_path -- the path to the dataset file that was annotated
    source_hash -- the Git hash of the dataset file version of the dataset

    :returns: an RDF graph store containing a nanopublication
    """
    BASE = Namespace('{}/'.format(dataset_base_uri))
    dataset_uri = URIRef(dataset_base_uri)

    # Initialize a conjunctive graph for the whole lot
    rdf_dataset = Dataset()
    rdf_dataset.bind('qbrv', QBRV)
    rdf_dataset.bind('qbr', QBR)
    rdf_dataset.bind('qb', QB)
    rdf_dataset.bind('skos', SKOS)
    rdf_dataset.bind('prov', PROV)
    rdf_dataset.bind('np', NP)
    rdf_dataset.bind('foaf', FOAF)

    # Initialize the graphs needed for the nanopublication
    timestamp = datetime.datetime.now().isoformat()

    hash_part = source_hash + '/' + timestamp

    # The Nanopublication consists of three graphs
    assertion_graph_uri = BASE['assertion/' + hash_part]
    assertion_graph = rdf_dataset.graph(assertion_graph_uri)

    provenance_graph_uri = BASE['provenance/' + hash_part]
    provenance_graph = rdf_dataset.graph(provenance_graph_uri)

    pubinfo_graph_uri = BASE['pubinfo/' + hash_part]
    pubinfo_graph = rdf_dataset.graph(pubinfo_graph_uri)

    # A URI that represents the author
    author_uri = QBR['person/' + profile['email']]

    rdf_dataset.add((author_uri, RDF.type, FOAF['Person']))
    rdf_dataset.add((author_uri, FOAF['name'], Literal(profile['name'])))
    rdf_dataset.add((author_uri, FOAF['email'], Literal(profile['email'])))
    rdf_dataset.add((author_uri, QBRV['googleId'], Literal(profile['id'])))
    rdf_dataset.add((author_uri, FOAF['depiction'], URIRef(profile['image'])))

    # A URI that represents the version of the dataset source file
    dataset_version_uri = BASE[source_hash]

    # Some information about the source file used
    rdf_dataset.add((dataset_version_uri, QBRV['path'], Literal(source_path, datatype=XSD.string)))
    rdf_dataset.add((dataset_version_uri, QBRV['sha1_hash'], Literal(source_hash, datatype=XSD.string)))

    # ----
    # The nanopublication itself
    # ----
    nanopublication_uri = BASE['nanopublication/' + hash_part]

    rdf_dataset.add((nanopublication_uri, RDF.type, NP['Nanopublication']))
    rdf_dataset.add((nanopublication_uri, NP['hasAssertion'], assertion_graph_uri))
    rdf_dataset.add((assertion_graph_uri, RDF.type, NP['Assertion']))
    rdf_dataset.add((nanopublication_uri, NP['hasProvenance'], provenance_graph_uri))
    rdf_dataset.add((provenance_graph_uri, RDF.type, NP['Provenance']))
    rdf_dataset.add((nanopublication_uri, NP['hasPublicationInfo'], pubinfo_graph_uri))
    rdf_dataset.add((pubinfo_graph_uri, RDF.type, NP['PublicationInfo']))

    # ----
    # The provenance graph
    # ----

    # Provenance information for the assertion graph (the data structure definition itself)
    provenance_graph.add((assertion_graph_uri, PROV['wasDerivedFrom'], dataset_version_uri))
    provenance_graph.add((dataset_uri, PROV['wasDerivedFrom'], dataset_version_uri))
    provenance_graph.add((assertion_graph_uri, PROV['generatedAtTime'],
                          Literal(timestamp, datatype=XSD.datetime)))
    provenance_graph.add((assertion_graph_uri, PROV['wasAttributedTo'], author_uri))

    # ----
    # The publication info graph
    # ----

    # The URI of the latest version of QBer
    # TODO: should point to the actual latest commit of this QBer source file.
    # TODO: consider linking to this as the plan of some activity, rather than an activity itself.
    qber_uri = URIRef('https://github.com/CLARIAH/qber.git')

    pubinfo_graph.add((nanopublication_uri, PROV['wasGeneratedBy'], qber_uri))
    pubinfo_graph.add((nanopublication_uri, PROV['generatedAtTime'],
                      Literal(timestamp, datatype=XSD.datetime)))
    pubinfo_graph.add((nanopublication_uri, PROV['wasAttributedTo'], author_uri))

    # ----
    # The assertion graph
    # ----

    structure_uri = BASE['structure']

    assertion_graph.add((dataset_uri, RDF.type, QB['DataSet']))
    assertion_graph.add((dataset_uri, RDFS.label, Literal(dataset_name)))
    assertion_graph.add((structure_uri, RDF.type, QB['DataStructureDefinition']))

    assertion_graph.add((dataset_uri, QB['structure'], structure_uri))

    for variable_id, variable in variables.items():
        variable_uri = URIRef(variable['original']['uri'])
        variable_label = Literal(variable['original']['label'])
        variable_type = URIRef(variable['type'])

        codelist_uri = URIRef(variable['codelist']['original']['uri'])
        codelist_label = Literal(variable['codelist']['original']['label'])

        # The variable as component of the definition
        component_uri = safe_url(BASE, 'component/' + variable['original']['label'])

        # Add link between the definition and the component
        assertion_graph.add((structure_uri, QB['component'], component_uri))

        # Add label to variable
        # TODO: We may need to do something with a changed label for the variable
        assertion_graph.add((variable_uri, RDFS.label, variable_label))

        if 'description' in variable and variable['description'] != "":
            assertion_graph.add((variable_uri, RDFS.comment, Literal(variable['description'])))

        # If the variable URI is not the same as the original,
        # it is a specialization of a prior variable property.
        if variable['uri'] != str(variable_uri):
            assertion_graph.add((variable_uri,
                                 RDFS['subPropertyOf'],
                                 URIRef(variable['uri'])))

        if variable_type == QB['DimensionProperty']:
            assertion_graph.add((variable_uri, RDF.type, variable_type))
            assertion_graph.add((component_uri, QB['dimension'], variable_uri))

            # Coded variables are also of type coded property (a subproperty of dimension property)
            if variable['category'] == 'coded':
                assertion_graph.add((variable_uri, RDF.type, QB['CodedProperty']))

        elif variable_type == QB['MeasureProperty']:
            # The category 'other'
            assertion_graph.add((variable_uri, RDF.type, variable_type))
            assertion_graph.add((component_uri, QB['measure'], variable_uri))
        elif variable_type == QB['AttributeProperty']:
            # Actually never produced by QBer at this stage
            assertion_graph.add((variable_uri, RDF.type, variable_type))
            assertion_graph.add((component_uri, QB['attribute'], variable_uri))

        # If this variable is of category 'coded', we add codelist and URIs for
        # each variable (including mappings between value uris and etc....)
        if variable['category'] == 'coded':
            assertion_graph.add((codelist_uri, RDF.type, SKOS['Collection']))
            assertion_graph.add((codelist_uri, RDFS.label, Literal(codelist_label)))

            # The variable should point to the codelist
            assertion_graph.add((variable_uri, QB['codeList'], codelist_uri))

            # The variable is mapped onto an external code list.
            # If the codelist uri is not the same as the original one, we
            # have a derived codelist.
            if variable['codelist']['uri'] != str(codelist_uri):
                assertion_graph.add((codelist_uri,
                                     PROV['wasDerivedFrom'],
                                     URIRef(variable['codelist']['uri'])))

            # Generate a SKOS concept for each of the values and map it to the
            # assigned codelist
            for value in variable['values']:
                value_uri = URIRef(value['original']['uri'])
                value_label = Literal(value['original']['label'])

                assertion_graph.add((value_uri, RDF.type, SKOS['Concept']))
                assertion_graph.add((value_uri, SKOS['prefLabel'], Literal(value_label)))
                assertion_graph.add((codelist_uri, SKOS['member'], value_uri))

                # The value has been changed, and therefore there is a mapping
                if value['original']['uri'] != value['uri']:
                    assertion_graph.add((value_uri, SKOS['exactMatch'], URIRef(value['uri'])))
                    assertion_graph.add((value_uri, RDFS.label, Literal(value['label'])))

        elif variable['category'] == 'identifier':
            # Generate a SKOS concept for each of the values
            for value in variable['values']:
                value_uri = URIRef(value['original']['uri'])
                value_label = Literal(value['original']['label'])

                assertion_graph.add((value_uri, RDF.type, SKOS['Concept']))
                assertion_graph.add((value_uri, SKOS['prefLabel'], value_label))

                # The value has been changed, and therefore there is a mapping
                if value['original']['uri'] != value['uri']:
                    assertion_graph.add((value_uri, SKOS['exactMatch'], URIRef(value['uri'])))
                    assertion_graph.add((value_uri, RDFS.label, Literal(value['label'])))

        elif variable['category'] == 'other':
            # Generate a literal for each of the values when converting the dataset (but not here)
            pass

    return rdf_dataset


def reindent(s, numSpaces):
    s = s.split('\n')
    s = [(numSpaces * ' ') + string.lstrip(line) for line in s]
    s = "\n".join(s)
    return s

# Because Trig serialization in RDFLib is extremely crappy
import string


def serializeTrig(rdf_dataset):
    turtles = []
    for c in rdf_dataset.contexts():
        if c.identifier != URIRef('urn:x-rdflib:default'):
            turtle = "<{id}> {{\n".format(id=c.identifier)
            turtle += reindent(c.serialize(format='turtle'), 4)
            turtle += "}\n\n"
        else:
            turtle = c.serialize(format='turtle')
            turtle += "\n\n"

        turtles.append(turtle)

    return "\n".join(turtles)
