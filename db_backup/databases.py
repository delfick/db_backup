from db_backup.processes import stdout_chunks
from db_backup.errors import BadValue

class DatabaseInfo(object):
    ATTRS = ("engine", "name", "user", "password", "port", "host")

    def __init__(self, engine, name, user=None, password=None, port=None, host=None):
        self.name = name
        self.user = user
        self.port = port
        self.host = host
        self.engine = engine
        self.password = password

    def as_dict(self):
        """Return database info attributes as a dictionary"""
        return {key:getattr(self, key, None) for key in DatabaseInfo.ATTRS}

    @classmethod
    def from_dict(self, options):
        """Return us an instance of DatabaseInfo from a dictionary"""
        lowered = {key.lower():val for key, val in options.items()}
        have = {key:lowered[key] for key in DatabaseInfo.ATTRS if key in lowered}
        return DatabaseInfo(**have)

class DatabaseHandler(object):
    PSQL_DB = 'psql'
    MYSQL_DB = 'mysql'
    SQLITE_DB = 'sqlite'

    def __init__(self, database_info):
        self.database_info = database_info
        if isinstance(self.database_info, dict):
            self.database_info = DatabaseInfo.from_dict(self.database_info)

        self.database_type = {
              'django.db.backends.mysql': DatabaseHandler.MYSQL_DB
            , 'django.db.backends.sqlite3': DatabaseHandler.SQLITE_DB
            , 'django.db.backends.postgresql_psycopg2': DatabaseHandler.PSQL_DB
            }.get(self.database_info.engine)

        if self.database_type is None:
            raise BadValue("Provided database_engine ({0}) is not one we support".format(self.database_info.engine))

    def dump(self):
        """Dump the contents of the database and yield a chunk at a time without hitting the disk"""
        command, options = self.dump_command()
        return stdout_chunks(command, options, "Dump command")

    def dump_command(self):
        """Get the necessary command for dumping contents from our database"""
        if self.database_type == DatabaseHandler.SQLITE_DB:
            # Sqlite3 doesn't have a special command for dumping
            command = "sqlite3"
            options = "{name} .dump"
        else:
            if self.database_type == DatabaseHandler.PSQL_DB:
                command = "pg_dump"
                options = "-U {user}"
            elif self.database_type == DatabaseHandler.MYSQL_DB:
                command = "mysqldump"
                options = "--user {user}"
            else:
                raise BadValue("The database_type on this instance is weird ({0}).".format(self.database_type))

            # Inject host and port if required
            if self.database_info.port:
                options = "{0} --port {{port}}".format(options)
            if self.database_info.host:
                options = "{0} --host {{host}}".format(options)

            # Add the database name after the options
            options = "{0} {{name}}".format(options)

        return command, options.format(**self.database_info.as_dict())

