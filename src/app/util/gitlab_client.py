import logging
import gitlab
from datetime import datetime
from pprint import pprint as pprint
import os
from app import app

log = app.logger
log.setLevel(logging.DEBUG)


PRIVATE_TOKEN = "ZDMRh1o7xCmigmxK8hqK"
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
        log.debug("Successfully added file to GitLab server")

#         (parent_path, filename) = os.path.split(file_path)
#         tree = git.getrepositorytree(PROJECT, path=parent_path)
#         file_info_tree = (item for item in tree if item["name"] == filename).next()

        project_info = git.getproject(PROJECT)
        file_info = git.getfile(PROJECT, file_path, "master")

        url = project_info["web_url"] + "/raw/" + file_info["ref"] + "/" + file_info["file_path"]
        return url

    else:
        raise Exception("Could not upload file to GitLab server")
