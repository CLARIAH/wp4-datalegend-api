import unittest
from pprint import pprint as pprint
from datetime import datetime

# How to use?
#


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

    def test_list_gitlab_projects(self):
        import app.util.gitlab_client as gc

        pprint(gc.list_projects())

        assert True

    def test_get_gitlab_project(self):
        import app.util.gitlab_client as gc

        pprint(gc.get_project_info())

        assert True

    def test_gitlab_add_file(self):
        import app.util.gitlab_client as gc

        print gc.add_file('test/test2.csv', "This is just a test... {}".format(datetime.utcnow().isoformat()))

        assert True

    def test_gitlab_browse(self):
        import app.util.gitlab_client as gc

        print gc.browse(None, '')

        print gc.browse('', 'test')

        assert True

if __name__ == '__main__':
    unittest.main()
