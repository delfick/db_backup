from db_backup.processes import feed_process, check_and_start_process, until, stdout_chunks
from db_backup.errors import GPGFailedToStart

class Encryptor(object):
    """Used to encrypt and decrypt with gpg"""

    def encrypt(self, input_iterator, recipients, destination):
        """Encrypt chunks from the provided iterator"""
        desc = "Encrypting something"
        options = "--trust-model always -e -r {0} --output {1}".format(" -r ".join(recipients), destination)
        process = check_and_start_process("gpg", options, desc, capture_stdin=True)

        # See if it fails to start (i.e. bad recipients)
        for _ in until(timeout=0.5):
            if process.poll() not in (None, 0):
                raise GPGFailedToStart("GPG didn't even start")

        feed_process(process, desc, input_iterator)

    def decrypt(self, location):
        """Decrypt provided location and yield chunks of decrypted data"""
        return stdout_chunks("gpg", "--trust-model always -d {0}".format(location), "Decrypting something")

