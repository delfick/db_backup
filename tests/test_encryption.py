# coding: spec

from db_backup.processes import wait_for, check_and_start_process, stdout_chunks
from db_backup.errors import GPGFailedToStart, FailedToRun
from db_backup.encryption import Encryptor

from tests.utils import a_temp_file, path_to, copied_directory, gpg_fingerprint, setup_gpg_home
from tests.case import TestCase

from noseOfYeti.tokeniser.support import noy_sup_setUp
import os

describe TestCase, "Encryptor":
    before_each:
        self.encryptor = Encryptor()

    it "raises GPGFailedToStart if it doesn't know the specified recipients":
        with a_temp_file() as dest:
            with self.assertRaisesRegexp(GPGFailedToStart, "GPG didn't even start"):
                self.encryptor.encrypt(["1", "2", "3"], ["lkasdf", "oiuweor"], dest)

    it "can encrypt and decrypt a message":
        message = "1\n2\n3\n4"
        gpg_home = path_to("gpg")

        with copied_directory(gpg_home) as new_gpg_home:
            setup_gpg_home(new_gpg_home)
            with a_temp_file() as dest:
                os.remove(dest)
                self.encryptor.encrypt([message], ["bob@bob.com", "jade@stone.com"], dest, new_gpg_home)

                with open(dest) as f:
                    encrypted = f.read()

                self.assertGreater(len(encrypted), 0)
                self.assertNotEqual(encrypted, message)

                decrypted = ' '.join(self.encryptor.decrypt(dest, new_gpg_home, password="super_secret"))
                self.assertEqual(decrypted, message)

    it "Can't decrypt a message if the key is gone":
        message = "1\n2\n3\n4"
        gpg_home = path_to("gpg")

        with copied_directory(gpg_home) as new_gpg_home:
            setup_gpg_home(new_gpg_home)
            with a_temp_file() as dest:
                os.remove(dest)
                self.encryptor.encrypt([message], ["bob@bob.com"], dest, new_gpg_home)

                with open(dest) as f:
                    encrypted = f.read()

                self.assertGreater(len(encrypted), 0)
                self.assertNotEqual(encrypted, message)

                # Now remove the key
                fingerprint = gpg_fingerprint("bob@bob.com", new_gpg_home)
                process = check_and_start_process("gpg", "--homedir {0} --no-tty --batch --delete-secret-and-public-key \"{1}\"".format(new_gpg_home, fingerprint), "Remove key")
                wait_for(process, "Remove key", timeout=5)

                # Print remaining keys for debugging purposes and see that we can't decrypt
                print '\n'.join(stdout_chunks("gpg", "--list-keys --homedir {0}".format(new_gpg_home), "List key"))
                with self.assertRaisesRegexp(FailedToRun, "Decrypting something failed"):
                    list(self.encryptor.decrypt(dest, new_gpg_home, password="super_secret"))

