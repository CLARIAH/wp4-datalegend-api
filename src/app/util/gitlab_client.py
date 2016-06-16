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


def get_file(file_path, content):
    file_info = get_file_info(file_path)
    # TODO: This should actually be the file object. Let's first see how that ties into the code in views.py
    return file_info['url']

def get_file_info(file_path):
    project_info = git.getproject(PROJECT)
    file_info = git.getfile(PROJECT, file_path, "master")

    # Add 'url' to file_info
    file_info['url'] = project_info["web_url"] + "/raw/" + file_info["ref"] + "/" + file_info["file_path"]


def add_file(file_path, content):
    success = git.updatefile(PROJECT,
                             file_path,
                             "master",
                             content,
                             "File uploaded by datalegend API {}".format(datetime.utcnow().isoformat()))

    if success:
        log.debug("Successfully added file to GitLab server")
        file_info = get_file_info(file_path)

        return file_info
    else:
        log.error("Could not upload file to GitLab server")
        raise Exception("Could not upload file to GitLab server")
