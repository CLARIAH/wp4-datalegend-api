import logging
import gitlab
from datetime import datetime
from pprint import pprint as pprint
import os
from app import app

log = app.logger
log.setLevel(logging.DEBUG)


PRIVATE_TOKEN = "YOURPRIVATETOKENHERE"
PROJECT = 15

git = gitlab.Gitlab('http://gitlab.clariah-sdh.eculture.labs.vu.nl', token=PRIVATE_TOKEN)


def list_projects():
    projects = list(git.getall(git.getprojects))

    return projects


def get_project_info():
    try:
        info = git.getproject(PROJECT)
        log.debug("Retrieved project info from Gitlab for project {}".format(PROJECT))
        return info
    except:
        log.error("Could not retrieve project info for project {}".format(PROJECT))


def add_file(file_path, content):
    success = git.updatefile(PROJECT,
                             file_path,
                             "master",
                             content,
                             "File uploaded by datalegend API {}".format(datetime.utcnow().isoformat()))

    if success:
        print "success"
        (parent_path, filename) = os.path.split(file_path)

        tree = git.getrepositorytree(PROJECT, path=parent_path)

        file_info = (item for item in tree if item["name"] == filename).next()

        log.debug("Successfully added file to GitLab server")

        return file_info

    else:
        raise Exception("Could not upload file to GitLab server")
