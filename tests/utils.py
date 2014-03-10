from db_backup.processes import stdout_chunks

from contextlib import contextmanager

import traceback
import tempfile
import logging
import shutil
import sys
import os

log = logging.getLogger("db_backup_tests")

test_folder = os.path.abspath(os.path.dirname(__file__))

def path_to(*path_parts):
    """Get us a path relative to the test folder"""
    return os.path.abspath(os.path.join(test_folder, *path_parts))

@contextmanager
def a_temp_file():
    """Yield a temporary file and ensure it is deleted"""
    fle = None
    try:
        fle = tempfile.NamedTemporaryFile(delete=False).name
        yield fle
    finally:
        if fle and os.path.exists(fle):
            os.remove(fle)

@contextmanager
def a_temp_directory():
    """Yield a temporary directory and ensure it is deleted"""
    directory = None
    try:
        directory = tempfile.mkdtemp()
        yield directory
    finally:
        if directory and os.path.exists(directory):
            shutil.rmtree(directory)

@contextmanager
def copied_directory(original):
    """Copy a directory and yield that directory, make sure it disappears on exit"""
    with a_temp_directory() as new_dir:
        shutil.rmtree(new_dir)
        shutil.copytree(original, new_dir)
        yield new_dir

def gpg_fingerprint(uid, gpg_home):
    """Get us a fingerprint from a uid"""
    next_fingerprint = None
    for chunk in stdout_chunks("gpg", "--list-keys --fingerprint --homedir {0}".format(gpg_home), "Find fingerprints"):
        for line in chunk.split("\n"):
            if line.strip().startswith("Key fingerprint"):
                next_fingerprint = line.split("=")[1].strip()
                print "fingerprint", next_fingerprint
            elif line.strip().startswith("uid") and uid in line:
                return next_fingerprint

    raise Exception("Couldn't find fingerprint for uid {0}".format(uid))

@contextmanager
def print_exception_and_assertfail(desc):
    """Ignore any exceptions and print out the traceback to sys.stderr"""
    try:
        yield
    except KeyboardInterrupt:
        raise
    except Exception:
        print >> sys.stderr, traceback.format_exc()
        assert False, desc

def run_command(command, options, desc):
    """Run some command and log the stdout"""
    lines = []
    for chunk in stdout_chunks(command, options, desc):
        for line in chunk.split("\n"):
            log.info("STDOUT: %s", line)
            lines.append(line)
    return lines

def assert_is_binary(location):
    """Run file against the location and see that it returns 'data'"""
    return ''.join(stdout_chunks("file", "{0} -b".format(location), "See if a file is binary")).strip() == "data"

def setup_gpg_home(gpg_home):
    """Make sure the directory has 700 permissions and everything inside has 600 permissions"""
    os.chmod(gpg_home, 0700)
    for fle in os.listdir(gpg_home):
        os.chmod(os.path.join(gpg_home, fle), 0600)

