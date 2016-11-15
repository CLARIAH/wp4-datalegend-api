# -*- coding: utf-8 -*-

# TODO: Temporarily Disabled
# import os
# os.environ["DYLD_LIBRARY_PATH"] = "../lib/python2.7/site-packages/savReaderWriter/spssio/macos"

from collections import OrderedDict
# TODO: Temporarily Disabled
# from savReaderWriter import SavReader, SavHeaderReader
import csv
import pandas as pd
import numpy as np
import iribaker
import magic
import os
import traceback
import logging
from app import config, app

log = app.logger
log.setLevel(logging.DEBUG)


class Adapter(object):

    def __init__(self, dataset, file_object=None):
        self.dataset = dataset

        if 'name' not in dataset:
            (head, dataset_local_name) = os.path.split(dataset['filename'])
            (dataset_name, extension) = os.path.splitext(dataset_local_name)
            self.dataset_name = dataset_name
        else:
            self.dataset_name = dataset['name']

        if 'version' in dataset:
            self.dataset_uri = iribaker.to_iri(
                config.QBR_BASE + dataset['version'] + '/' + self.dataset_name)
        else:
            self.dataset_uri = iribaker.to_iri(
                config.QBR_BASE + self.dataset_name)

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
                metadata_reader = csv.reader(
                    metadata_file, delimiter=";", quotechar="\"")

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

    def get_data(self):
        """
        Return the CSV file as a dictionary ('column': [list of values])
        """
        return self.data.fillna(value='').to_dict(orient='list')

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
                print col, i
                # The URI for the variable value
                i_uri = iribaker.to_iri(u"{}/value/{}/{}"
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

            codelist_label = "Codelist generated from the values for '{}'".format(
                col)

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
                'category': 'identifier',
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

    def __init__(self, dataset, file_object=None):
        """Initializes an adapter for reading a CSV dataset"""
        super(CsvAdapter, self).__init__(dataset)

        if not dataset['format'] == 'text/csv':
            raise Exception(
                'This is a CSV adapter, not {}'.format(dataset['format']))

        self.filename = dataset['filename']

        self.has_header = dataset['header']

        if file_object is None:
            with open(self.filename, 'r') as fn:
                self.data = pd.read_csv(
                    fn, index_col=False, parse_dates=True, encoding='utf-8')
        else:
            self.data = pd.read_csv(
                file_object, index_col=False, parse_dates=True, encoding='utf-8')

        if self.has_header:
            self.header = list(self.data.columns)
        elif self.metadata:
            self.header = self.metadata.keys()
        else:
            self.header = None

        self.metadata = self.load_metadata()

        print self.validate_header()
        return


class ExcelAdapter(Adapter):

    def __init__(self, dataset, file_object=None, clio=False):
        """Initializes an adapter for reading an Excel dataset"""
        super(ExcelAdapter, self).__init__(dataset)

        if not (dataset['format'] ==
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                or dataset['format'] == 'application/vnd.ms-excel'):
            raise Exception(
                'This is an Excel adapter, not {}'.format(dataset['format']))

        self.filename = dataset['filename']

        self.has_header = dataset['header']

        # If this is ClioInfra data, we skip the first two rows of the
        # Worksheet
        if clio:
            skiprows = [0, 1]
            header = 0
        else:
            skiprows = None
            header = 0

        if file_object is None:
            with open(self.filename, 'r') as fn:
                self.data = pd.read_excel(fn, skiprows=skiprows, header=header)
        else:
            self.data = pd.read_excel(
                file_object, skiprows=skiprows, header=header)

        if clio:
            # Unpivot the table, excluding the first 6 columns (webmapper ids,
            # country, period)
            id_vars = [
                'Webmapper code',
                'Webmapper numeric code',
                'ccode',
                'country name',
                'start year',
                'end year'
            ]
            self.data = pd.melt(self.data, id_vars=id_vars,
                                var_name='year', value_name='GDPPC')

            self.data = self.data[np.isfinite(self.data['GDPPC'])]

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

    def __init__(self, dataset, file_object=None):
        """Initializes an adapter for reading a Tab-delimited dataset"""
        super(TabAdapter, self).__init__(dataset)

        if dataset['format'] not in ['text/tab-separated-values', 'text/plain']:
            raise Exception(
                'This is a Tab adapter, not {}'.format(dataset['format']))

        self.filename = dataset['filename']

        self.has_header = dataset['header']

        if file_object is None:
            with open(self.filename, 'r') as fn:
                self.data = pd.DataFrame.from_csv(
                    fn, index_col=False, sep='\t')
        else:
            self.data = pd.DataFrame.from_csv(
                file_object, index_col=False, sep='\t')

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
    "text/plain": TabAdapter,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ExcelAdapter,
    "application/vnd.ms-excel": ExcelAdapter
}


def get_adapter(dataset, file_object=None):
    log.debug("Filename: {}".format(dataset['filename']))
    if 'format' in dataset:
        mimetype = dataset['format']
    elif dataset['filename'].endswith('.tsv') or dataset['filename'].endswith('.tab'):
        mimetype = 'text/tab-separated-values'
        # Make sure we set the guessed mimetype as format for the dataset
        dataset['format'] = mimetype
    elif dataset['filename'].endswith('.csv'):
        mimetype = 'text/csv'
        # Make sure we set the guessed mimetype as format for the dataset
        dataset['format'] = mimetype
    elif dataset['filename'].endswith('.xls'):
        mimetype = 'application/vnd.ms-excel'
        dataset['format'] = mimetype
    elif dataset['filename'].endswith('.xlsx'):
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        dataset['format'] = mimetype
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
                print "Detected CSV"
                mimetype = 'text/csv'
            elif dialect.delimiter == '\t':
                print "Detected TAB"
                mimetype = 'text/tab-separated-values'
            else:
                # Probably not very wise, but we'll default to the CSV mimetype
                # and rely on Panda's ability to guess the separator
                print "Fallback to CSV"
                mimetype = 'text/csv'

        except csv.Error:
            # File appears not to be in CSV format; try libmagic (not very
            # useful)
            mymagic = magic.Magic(mime=True)
            mimetype = mymagic.from_buffer(
                open(dataset['filename']).read(1024))

        # Make sure we set the guessed mimetype as format for the dataset
        dataset['format'] = mimetype

    try:
        adapterClass = mappings[mimetype]
        adapter = adapterClass(dataset, file_object=file_object)

        return adapter
    except Exception as e:
        traceback.print_exc()
        raise(e)
        # raise(Exception("No adapter for this file type: '{}'".format(mimetype)))
