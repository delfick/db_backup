from db_backup.processes import start_process, feed_process, check_for_command, until
from db_backup.errors import FailedEncryption, BadValue, GPGFailedToStart

import logging
import os

log = logging.getLogger("db_backup")

class Encryptor(object):
    """Used to run gpg over some input with a particular recipient list"""
    DEFAULT_KEYLIST = "/etc/gpg-backup/keylist"

    def __init__(self, keylist=None):
        self.keylist = keylist
        self.recipients = []
        if not self.keylist:
            self.keylist = Encryptor.DEFAULT_KEYLIST

    def prepare(self):
        """Raise exceptions and get recipients"""
        if not os.path.exists(self.keylist):
            raise BadValue("The specified keylist doesn't exist ({0})".format(self.keylist))

        with open(self.keylist) as fle:
            for key in fle:
                self.recipients.append(key.strip())

    def encrypt(self, input_iterator, destination):
        """Encrypt chunks from the provided iterator"""
        if not self.recipients:
            raise FailedEncryption("No recipients, did you run Encryptor().prepare() first?")

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

