import logging
import sys

from db_backup.errors import FailedBackup

log = logging.getLogger("db_backup")

class Backup(object):
    def __init__(self, database_handler):
        self.database_handler = database_handler

    def run(self):
        try:
            for chunk in self.database_handler.dump():
                pass
        except FailedBackup as error:
            log.error(error)
            sys.exit(1)

