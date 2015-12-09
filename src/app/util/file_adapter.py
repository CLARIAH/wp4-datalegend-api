# -*- coding: utf-8 -*-

# TODO: Temporarily Disabled
# import os
# os.environ["DYLD_LIBRARY_PATH"] = "../lib/python2.7/site-packages/savReaderWriter/spssio/macos"

from collections import OrderedDict
# TODO: Temporarily Disabled
# from savReaderWriter import SavReader, SavHeaderReader
import csv
import pandas as pd
import iribaker
import magic
import os
from app import config


class Adapter(object):
    def __init__(self, dataset):
        self.dataset = dataset

        (head, dataset_local_name) = os.path.split(dataset['filename'])
        (dataset_name, extension) = os.path.splitext(dataset_local_name)

        self.dataset_name = dataset_name
        self.dataset_uri = iribaker.to_iri(config.QBR_BASE + dataset_name)

        print "Initialized adapter"
        return

    def get_reader(self):
        return self.reader

    def get_header(self):
        return self.header

    def get_dataset_uri(self):
        return self.dataset_uri

    def get_dataset_name(self):
        return self.dataset_name

    def get_metadata(self):
        if self.metadata:
            return self.metadata
        else:
            return None

    def load_metadata(self):
        metadata = OrderedDict()

        if 'metadata' in self.dataset:
            print "Loading metadata..."
            metadata_filename = self.dataset['metadata']

            with open(metadata_filename, "r") as metadata_file:
                metadata_reader = csv.reader(metadata_file, delimiter=";", quotechar="\"")

                for l in metadata_reader:
                    metadata[l[0].strip()] = l[1].strip()

        elif self.header:
            print "No metadata... reconstructing from header"
            for h in self.header:
                metadata[h] = h
        else:
            print "No metadata or header"

        return metadata

    def validate_header(self):
        """Checks whether the header in the file and the metadata provided are exactly the same"""
        if self.header and self.metadata:
            # Find the difference between header and metadata keys
            diff = set(self.header).difference(set(self.metadata.keys()))
            if len(diff) > 0:
                print "Header and metadata do *not* correspond"
                # print zip(self.header,self.metadata.keys())
                return False
            else:
                print "Header and metadata are aligned"
                return True
        else:
            print "No header or no metadata present"
            return False

    def get_values(self):
        """
        Return all unique values, and converts it to samples for each column.
        """

        # Get all unique values for each column
        stats = {}
        for col in self.data.columns:
            istats = []

            counts = self.data[col].value_counts()

            # print self.data[col][0]

            for i in counts.index:
                # The URI for the variable value
                i_uri = iribaker.to_iri("{}/value/{}/{}"
                                        .format(self.dataset_uri, col, i))

                # Capture the counts and label in a dictionary for the value
                stat = {
                    'original': {
                        'uri': i_uri,
                        'label': i
                    },
                    'label': i,
                    'uri': i_uri,
                    'count': counts[i]
                }

                # And append it to the list of variable values
                istats.append(stat)

            # The URI for the variable
            variable_uri = iribaker.to_iri("{}/variable/{}"
                                           .format(self.dataset_uri, col))
            # The URI for a (potential) codelist for the variable
            codelist_uri = iribaker.to_iri("{}/codelist/{}"
                                           .format(self.dataset_uri, col))

            codelist_label = "Codelist generated from the values for '{}'".format(col)

            codelist = {
                'original': {
                    'uri': codelist_uri,
                    'label': codelist_label
                },
                'uri': codelist_uri,
                'label': codelist_label
            }

            stats[col] = {
                'original': {
                    'uri': variable_uri,
                    'label': col
                },
                'uri': variable_uri,
                'label': col,
                'description': "The variable '{}' as taken "
                               "from the '{}' dataset."
                               .format(col, self.dataset_name),
                'category': 'coded',
                'type': 'http://purl.org/linked-data/cube#DimensionProperty',  # This is the default
                'values': istats,
                'codelist': codelist
            }

        return stats


# TODO: Temporarily Disabled
# class SavAdapter(Adapter):
#
#     def __init__(self, dataset):
#         super(SavAdapter, self).__init__(dataset)
#
#         if not dataset['format'] == 'SPSS':
#             raise Exception('This is an SPSS adapter, not {}'.format(dataset['format']))
#
#         self.filename = dataset['filename']
#
#         self.has_header = dataset['header']
#
#         self.reader = SavReader(self.filename, ioLocale='en_US.UTF-8')
#
#         if self.has_header:
#             with SavHeaderReader(self.filename, ioLocale='en_US.UTF-8') as hr:
#                 self.header = hr.varNames
#
#         else :
#             self.header = None
#
#         self.metadata = self.load_metadata()
#
#         print self.validate_header()
#         return
#
#     def get_examples(self):
#         """Returns first 10000 rows, and converts it to samples for each column."""
#
#         # Get first 10000 rows
#         rows = self.reader.head(10000)
#
#         # Assume metadata keys are best (since if no metadata exists, the header
#         # will be used to generate it)
#         header = self.metadata.keys()
#
#         # Convert the rows to a list of dictionaries with keys from the header
#         data_dictionaries = [dict(zip(header, [v.strip() if type(v) == str
#                              else v for v in values ])) for values in rows]
#
#         # Convert the list of dictionaries to a dictionary of sets
#         data = defaultdict(set)
#         for d in data_dictionaries:
#             for k, v in d.items():
#                 data[k].add(v)
#
#         json_ready_data = {}
#         for k,v in data.items():
#             json_ready_data[k] = list(v)[:250]
#
#         return json_ready_data


class CsvAdapter(Adapter):

    def __init__(self, dataset):
        """Initializes an adapter for reading a CSV dataset"""
        super(CsvAdapter, self).__init__(dataset)

        if not dataset['format'] == 'text/csv':
            raise Exception('This is a CSV adapter, not {}'.format(dataset['format']))

        self.filename = dataset['filename']

        self.has_header = dataset['header']

        with open(self.filename, 'r') as fn:
            self.data = pd.DataFrame.from_csv(fn)

        if self.has_header:
            self.header = list(self.data.columns)
        elif self.metadata:
            self.header = self.metadata.keys()
        else:
            self.header = None

        self.metadata = self.load_metadata()

        print self.validate_header()
        return


class TabAdapter(Adapter):

    def __init__(self, dataset):
        """Initializes an adapter for reading a Tab-delimited dataset"""
        super(TabAdapter, self).__init__(dataset)

        if dataset['format'] not in ['text/tab-separated-values', 'text/plain']:
            raise Exception('This is a Tab adapter, not {}'.format(dataset['format']))

        self.filename = dataset['filename']

        self.has_header = dataset['header']

        with open(self.filename, 'r') as fn:
            self.data = pd.DataFrame.from_csv(fn, sep='\t')
        if self.has_header:
            self.header = list(self.data.columns)
        elif self.metadata:
            self.header = self.metadata.keys()
        else:
            self.header = None

        self.metadata = self.load_metadata()

        print self.validate_header()
        return


mappings = {
    # "SPSS": SavAdapter,
    "text/csv": CsvAdapter,
    "text/tab-separated-values": TabAdapter,
    "text/plain": TabAdapter
}


def get_adapter(dataset):

    if 'format' in dataset:
        mimetype = dataset['format']
    else:
        csv_fileh = open(dataset['filename'], 'rb')
        try:
            dialect = csv.Sniffer().sniff(csv_fileh.read(1024))
            # Perform various checks on the dialect (e.g., lineseparator,
            # delimiter) to make sure it's sane

            # Don't forget to reset the read position back to the start of
            # the file before reading any entries.
            csv_fileh.seek(0)

            if dialect.delimiter == ',' or dialect.delimiter == ';':
                mimetype = 'text/csv'
            elif dialect.delimiter == '\t':
                mimetype = 'text/tab-separated-values'
            else:
                # Probably not very wise, but we'll default to the CSV mimetype
                # and rely on Panda's ability to guess the separator
                mimetype = 'text/csv'

        except csv.Error:
            # File appears not to be in CSV format; try libmagic (not very useful)
            mimetype = magic.from_buffer(open(dataset['filename']).read(1024), mime=True)

        # Make sure we set the guessed mimetype as format for the dataset
        dataset['format'] = mimetype

    try:
        adapterClass = mappings[mimetype]
        adapter = adapterClass(dataset)

        return adapter
    except Exception as e:
        raise(e)
        # raise(Exception("No adapter for this file type: '{}'".format(mimetype)))
