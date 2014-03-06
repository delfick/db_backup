from db_backup.processes import stdout_chunks
from db_backup.errors import BadValue

class DatabaseHandler(object):
    PSQL_DB = 'psql'
    MYSQL_DB = 'mysql'
    SQLITE_DB = 'sqlite'

    def __init__(self, database_options):
        self.database_options = database_options
        self.database_type = {
              'django.db.backends.mysql': DatabaseHandler.MYSQL_DB
            , 'django.db.backends.sqlite3': DatabaseHandler.SQLITE_DB
            , 'django.db.backends.postgresql_psycopg2': DatabaseHandler.PSQL_DB
            }.get(database_options['ENGINE'])

        if self.database_type is None:
            raise BadValue("Provided database_engine ({0}) is not one we support".format(self.database_options['ENGINE']))

    def dump(self):
        """Dump the contents of the database and yield a chunk at a time without hitting the disk"""
        command, options = self.dump_command()
        return stdout_chunks(command, options, "Dump command")

    def dump_command(self):
        """Get the necessary command for dumping contents from our database"""
        if self.database_type == DatabaseHandler.SQLITE_DB:
            # Sqlite3 doesn't have a special command for dumping
            command = "sqlite3"
            options = "{NAME} .dump"
        else:
            if self.database_type == DatabaseHandler.PSQL_DB:
                command = "pg_dump"
                options = "-U {USER}"
            elif self.database_type == DatabaseHandler.MYSQL_DB:
                command = "mysqldump"
                options = "--user {USER}"
            else:
                raise BadValue("The database_type on this instance is weird ({0}).".format(self.database_type))

            # Inject host and port if required
            if self.database_options.get('PORT'):
                options = "{0} --port {{PORT}}".format(options)
            if self.database_options.get('HOST'):
                options = "{0} --host {{HOST}}".format(options)

            # Add the database name after the options
            options = "{0} {{NAME}}".format(options)

        return command, options.format(**self.database_options)

