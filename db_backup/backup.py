from db_backup.databases import DatabaseHandler
from db_backup.encryption import Encryptor

import logging
import time
import os

log = logging.getLogger("db_backup")

class Backup(object):
    def __init__(self, database_settings, keylist):
        self.keylist = keylist
        self.database_settings = database_settings

    def run(self, backup_dir):
        database_handler = DatabaseHandler(self.database_settings)
        encryption_handler = Encryptor(self.keylist)

        filename = "db_backup_{0}.gpg".format(time.time())
        destination = os.path.join(backup_dir, filename)

        encryption_handler.prepare()
        encryption_handler.encrypt(database_handler.dump(), destination)

