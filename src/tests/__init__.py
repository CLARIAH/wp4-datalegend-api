import unittest
import json


class TestLoad(unittest.TestCase):

    def test_excel_clio(self):
        """
        Tests basic loading CLIO Infra data into a DataFrame
        """

        import app.util.file_adapter as fa

        dataset = {
            "format": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "filename": "tests/GDP_Capita-historical.xlsx",
            "header": True
        }

        adapter = fa.get_adapter(dataset)

        values = adapter.get_values()

        import pprint

        pprint.pprint(values)
