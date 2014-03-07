from db_backup.processes import start_process, feed_process, check_for_command, until
from db_backup.errors import FailedEncryption, BadValue, GPGFailedToStart

import logging
import os

log = logging.getLogger("db_backup")

class Encryptor(object):
    """Used to run gpg over some input with a particular recipient list"""
    def __init__(self, recipients):
        self.recipients = recipients

    def encrypt(self, input_iterator, destination):
        """Encrypt chunks from the provided iterator"""
        command = "gpg --trust-model always -e -r {0} --output {1}".format(" -r ".join(self.recipients), destination)

        desc = "Encrypting something"
        check_for_command("gpg", desc)

        # We know we have gpg, let's do this!
        log.info("Running \"%s\"", command)
        process = start_process(command, capture_stdin=True)

        # See if it fails to start (i.e. bad recipients)
        for _ in until(timeout=0.5):
            if process.poll() not in (None, 0):
                raise GPGFailedToStart("GPG didn't even start")

        feed_process(process, desc, input_iterator)

