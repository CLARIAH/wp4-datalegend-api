import sh
import os
import argparse
import traceback

def get_repository(data_path):
    git = sh.git.bake(_cwd=data_path)
    try:
        git.status('.')
    except:
        git.init('.')

    return git


def pull(data_path):
    git = get_repository(data_path)
    response = git.pull()

    return response


def add_file(data_path, path, author, email):
    git = get_repository(data_path)

    path = path.replace(' ', '\\ ')

    # Get the relative path
    absolute_path = os.path.join(data_path, path)
    try:
        git.add(absolute_path)
        git.commit('--author=\"{} <{}>\"'.format(author, email),
                   m="QBer commit by {} (<{}>)".format(author, email))
    except:
        pass

    git_output = git('ls-files', '-s', absolute_path)

    sha_hash = git_output.split(' ')[1]
    return sha_hash


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get Git hash and commit if possible')
    parser.add_argument('data_path', type=str, help='Absolute path to GIT repository')
    parser.add_argument('path', type=str, help='Absolute path to file')
    parser.add_argument('author', type=str)
    parser.add_argument('email', type=str)

    args = parser.parse_args()

    print add_file(args.data_path, args.path, args.author, args.email)
