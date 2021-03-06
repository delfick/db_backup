# coding: spec

from db_backup.databases import DatabaseInfo, DatabaseDriver, PsqlDriver, MysqlDriver, DatabaseHandler, SqliteDriver
from db_backup.errors import FailedToRun, NoDatabase

from tests.utils import print_exception_and_assertfail, run_command
from tests.case import TestCase

from noseOfYeti.tokeniser.support import noy_sup_setUp, noy_sup_tearDown
import mock

from textwrap import dedent
import tempfile
import random
import os

describe TestCase, "DatabaseDriver":
    before_each:
        self.database_info = mock.Mock(name="Database_info")
        self.database_driver = DatabaseDriver(self.database_info)

    it "takes in database_info":
        driver = DatabaseDriver(self.database_info)
        self.assertIs(driver.database_info, self.database_info)

    describe "Getting a temporary file":
        it "Writes the content to the file and returns it's location":
            content = """
            blah
            and
            stuff
            """

            with self.database_driver.a_temp_file(content) as filename:
                assert os.path.exists(filename)
                self.assertEqual(open(filename).read(), content)

        it "deletes the file when done with it":
            with self.database_driver.a_temp_file("blah") as filename:
                assert os.path.exists(filename)
            assert not os.path.exists(filename)

        it "deletes the file even when there is an exception":
            AnException = type("AnException", (Exception, ), {})
            with self.assertRaisesRegexp(AnException, "hmmm"):
                with self.database_driver.a_temp_file("meh") as filename:
                    raise AnException("hmmm")

            assert not os.path.exists(filename)

    describe "Filling out a template":
        it "copes when argv portion is a string":
            self.database_info.as_dict.side_effect = lambda: {"stuff": 3}
            with self.database_driver.fill_out(("blah", "stuff>{stuff}")) as result:
                self.assertEqual(result, ("blah", " stuff>3", {}, None))

        it "ignores portion of the argv if it doesn't format to a nonempty":
            self.database_info.as_dict.return_value = {"blah": "", "other": 5, "things": None}
            with self.database_driver.fill_out(
                ( "command"
                , [ ("--flag", "{blah}"), ("--flag2", "{other}"), ("--flag3", "{things}"), ("--flag4", "{blah}_6")
                  ]
                )
            ) as result:
                self.assertEqual(result, ("command", "--flag2 5 --flag3 None --flag4 _6", {}, None))

        it "raises an error if we try to format something not in the options":
            self.database_info.as_dict.return_value =  {"stuff": 3}
            with self.assertRaisesRegexp(KeyError, "non_existant"):
                with self.database_driver.fill_out(("blah", "stuff>{non_existant}")):
                    pass

        describe "When we need a password":
            it "uses password_option option":
                self.database_driver.password_option = (None, ("-p", "{password}"), None, None)
                self.database_info.as_dict.return_value = {"password": "blah", "meh": 3}
                with self.database_driver.fill_out(("command", [("--flag", "{meh}")])) as result:
                    self.assertEqual(result, ("command", "-p blah --flag 3", {}, None))

            it "uses password_option env":
                self.database_driver.password_option = ({"SOME_ENV_VAR": "things_{password}"}, ("-p", "{password}"), None, None)
                self.database_info.as_dict.return_value = {"password": "blahs", "meh": 3}
                with self.database_driver.fill_out(("command", [("--flag", "{meh}")])) as result:
                    self.assertEqual(result, ("command", "-p blahs --flag 3", {"SOME_ENV_VAR": "things_blahs"}, None))

            it "formats and passes back the stdin":
                self.database_driver.password_option = ({"SOME_ENV_VAR": "things_{password}"}, ("-p", "{password}"), None, "tree_{password}")
                self.database_info.as_dict.return_value = {"password": "blahd", "meh": 3}
                with self.database_driver.fill_out(("command", [("--flag", "{meh}")])) as result:
                    self.assertEqual(result, ("command", "-p blahd --flag 3", {"SOME_ENV_VAR": "things_blahd"}, "tree_blahd"))

            it "puts file_contents from password_option into a file exposed as PASSWORD_FILE":
                file_contents = "blahdeblahablahya"
                self.database_driver.password_option = ({"SOME_ENV_VAR": "{PASSWORD_FILE}"}, ("-p", "{password}"), file_contents, None)
                self.database_info.as_dict.return_value = {"password": "blahs", "meh": 3}
                with self.database_driver.fill_out(("command", [("--flag", "{meh}"), ("--flag2", "{PASSWORD_FILE}")])) as result:
                    command, args, env, stdin = result
                    self.assertEqual(env.keys(), ["SOME_ENV_VAR"])
                    password_file = env["SOME_ENV_VAR"]
                    assert os.path.exists(password_file)
                    self.assertEqual(open(password_file).read(), file_contents)
                    self.assertEqual(result, ("command", "-p blahs --flag 3 --flag2 {0}".format(password_file), {"SOME_ENV_VAR": password_file}, None))
                assert not os.path.exists(password_file)

    describe "Dump command":
        it "fills out the dump_template":
            result = mock.Mock(name="result")
            dump_template = mock.Mock(name="dump_template")
            self.database_driver.dump_template = dump_template

            fill_out_cm = mock.MagicMock(name="fill_out_cm")
            fill_out_cm.__enter__.return_value = result
            with mock.patch.object(self.database_driver, "fill_out") as fill_out:
                fill_out.return_value = fill_out_cm
                with self.database_driver.dump_command() as dump_command:
                    self.assertIs(dump_command, result)
                fill_out.assert_called_once_with(dump_template)

    describe "Restore command":
        it "fills out the restore_template":
            result = mock.Mock(name="result")
            restore_template = mock.Mock(name="restore_template")
            self.database_driver.restore_template = restore_template

            fill_out_cm = mock.MagicMock(name="fill_out_cm")
            fill_out_cm.__enter__.return_value = result
            with mock.patch.object(self.database_driver, "fill_out") as fill_out:
                fill_out.return_value = fill_out_cm
                with self.database_driver.restore_command() as rslt:
                    self.assertIs(rslt, result)
                fill_out.assert_called_once_with(restore_template)

    describe "Is_empty command":
        it "runs the is_empty template and says whether the output is 0":
            is_empty_template = mock.Mock(name="is_empty_template")
            self.database_driver.is_empty_template = is_empty_template

            with mock.patch.object(self.database_driver, "run_template") as run_template:
                run_template.side_effect = lambda template, desc: "0"
                self.assertIs(self.database_driver.is_empty(), True)
                run_template.assert_called_once_with(is_empty_template, "Find number of tables")

            with mock.patch.object(self.database_driver, "run_template") as run_template:
                run_template.side_effect = lambda template, desc: "1"
                self.assertIs(self.database_driver.is_empty(), False)
                run_template.assert_called_once_with(is_empty_template, "Find number of tables")

    describe "run_template":
        @mock.patch("db_backup.databases.stdout_chunks")
        it "fills out the template and returns the stripped stdout from running the command", fake_stdout_chunks:
            env = mock.Mock(name="env")
            desc = mock.Mock(name="desc")
            command = mock.Mock(name="command")
            options = mock.Mock(name="options")
            template = mock.Mock(name="template")

            fake_stdout_chunks.side_effect = lambda *args, **kwargs: "\n1\n"
            fill_out_cm = mock.MagicMock(name="fill_out_cm")
            fill_out_cm.__enter__.return_value = (command, options, env, None)
            with mock.patch.object(self.database_driver, "fill_out") as fill_out:
                fill_out.return_value = fill_out_cm
                self.assertEqual(self.database_driver.run_template(template, desc), "1")
                fill_out.assert_called_once_with(template)
                fake_stdout_chunks.assert_called_once_with(command, options, desc, env=env, stdin=None)

        it "actually works":
            self.database_info.as_dict.side_effect = lambda: {}
            result = self.database_driver.run_template(("echo", "blah and stuff"), "Run echo")
            self.assertEqual(result, "blah and stuff")

describe TestCase, "DriverTestBase":

    # Tell noseOfYeti not to run these tests in this class
    # But instead run them in each subclass
    __only_run_tests_in_children__ = True

    SQL_ENGINE = None
    DRIVER_KLS = None
    SQL_TEST_USER = "db_backup_tests"
    SQL_TEST_DB_NAME = "db_backup_test_db"
    SQL_TEST_USER_WITH_PASSWORD = "db_bkp_tests_pwd"

    before_each:
        # Only do this for the subclasses where we have SQL_ENGINE specified
        if self.SQL_ENGINE:
            self.database_info = DatabaseInfo.from_dict({"engine": self.SQL_ENGINE, "name": self.SQL_TEST_DB_NAME, "user": self.SQL_TEST_USER})
            self.database_driver = self.DRIVER_KLS(self.database_info)
            self.database_handler = DatabaseHandler(self.database_info, self.database_driver)

            self.passworded_database_info = DatabaseInfo.from_dict({"engine": self.SQL_ENGINE, "name": self.SQL_TEST_DB_NAME, "user": self.SQL_TEST_USER_WITH_PASSWORD, "password": 'password'})
            self.passworded_database_driver = self.DRIVER_KLS(self.passworded_database_info)
            self.passworded_database_handler = DatabaseHandler(self.passworded_database_info, self.database_driver)

    after_each:
        # Only do this for the subclasses where we have SQL_ENGINE specified
        if self.SQL_ENGINE:
            self.dropdb()

    @classmethod
    def see_if_database_exists(cls):
        """Return whether our test database exists"""
        raise NotImplementedError()

    def createdb(self):
        """Create our test database"""
        self.dropdb()
        with print_exception_and_assertfail("Creating test database"):
            self._createdb()

    def dropdb(self):
        """Drop our test database"""
        with print_exception_and_assertfail("Seeing if we created a test database"):
            needs_deleting = self.see_if_database_exists()

        if needs_deleting:
            with print_exception_and_assertfail("Deleting test database"):
                self._dropdb()

    def _createdb(self):
        """Assume there is no db already and create one"""
        raise NotImplementedError()

    def _dropdb(self):
        """Assume there is a db to delete and drop it"""
        raise NotImplementedError()

    def run_sql_command(self, command, desc, extra=""):
        """Run some command with the cli"""
        raise NotImplementedError()

    def create_table(self, table_name, schema):
        """Create a table"""
        return self.run_sql_command("create table {0} ({1})".format(table_name, schema), "Creating a table")

    def insert_values(self, table_name, values):
        """Insert values into a table"""
        values_string = ", ".join(str(val) for val in values)
        return self.run_sql_command("insert into {0} values {1}".format(table_name, values_string), "Inserting values")

    def select_values(self, table_name):
        """Select values from a table"""
        return self.run_sql_command("select * from {0}".format(table_name), "Selecting values")

    # These tests are no run on this class
    # But we have the __only_run_tests_in_children__ option set so they run in children describes

    it "complains if it tries to backup a database that doesn't exist unless it's sqlite":
        self.dropdb()
        if self.SQL_ENGINE != 'sqlite3':
            with self.assertRaisesRegexp(FailedToRun, "Dump command failed"):
                list(self.database_handler.dump())
        else:
            dump = self.database_handler.dump()
            self.assertEqual(list(dump), ['PRAGMA foreign_keys=OFF;\nBEGIN TRANSACTION;\nCOMMIT;\n'])

    it "complains if tries to determine if a database that doesn't exist is empty":
        self.dropdb()
        if self.SQL_ENGINE == 'sqlite3':
            with self.assertRaisesRegexp(NoDatabase, "There was no sqlite database.+"):
                self.database_driver.is_empty()
        else:
            with self.assertRaisesRegexp(FailedToRun, "Find number of tables failed"):
                self.database_driver.is_empty()

    it "says the database is empty when it has no tables":
        self.createdb()
        assert self.database_driver.is_empty()

    it "says the database is not empty if it has a table":
        self.createdb()
        self.create_table("blah", "id integer")
        assert not self.database_driver.is_empty()

    it "successfully can dump and restore a database":
        self.createdb()
        self.create_table("blah", "id integer, val varchar(10)")

        values = [(str(num), str(int(random.random() * 100))) for num in range(10)]
        self.insert_values("blah", values)

        dump = list(self.database_handler.dump())
        self.dropdb()
        self.createdb()

        assert self.database_driver.is_empty()
        self.database_handler.restore(dump)
        restored_values = []
        for row in self.select_values("blah"):
            if row:
                if "|" in row:
                    restored_values.append(tuple(row.split("|")))
                else:
                    restored_values.append(tuple(row.split("\t")))
        self.assertEqual(restored_values, values)

    it "successfully can dump and restore a database when a password is required":
        self.createdb()
        self.create_table("blah", "id integer, val varchar(10)")

        values = [(str(num), str(int(random.random() * 100))) for num in range(10)]
        self.insert_values("blah", values)

        dump = list(self.passworded_database_handler.dump())

        self.dropdb()
        self.createdb()

        assert self.passworded_database_driver.is_empty()
        self.passworded_database_handler.restore(dump)
        restored_values = []
        for row in self.select_values("blah"):
            if row:
                if "|" in row:
                    restored_values.append(tuple(row.split("|")))
                else:
                    restored_values.append(tuple(row.split("\t")))
        self.assertEqual(restored_values, values)

    describe "Psql Driver":
        # __only_run_tests_in_children__ Means the tests in the parent describe are run here

        SQL_ENGINE = 'psql'
        DRIVER_KLS = PsqlDriver

        @classmethod
        def setupClass(cls):
            try:
                cls.see_if_database_exists()
            except FailedToRun:
                assert False, dedent("""
                    Couldn't ask psql for info. Perhaps you don't have a {0} user in your postgres?

                    Try::

                        $ sudo -u postgres psql -c "create user {0} with CREATEDB"
                        $ sudo -u postgres psql -c "create user {0} with CREATEDB PASSWORD 'password'"
                """.format(cls.SQL_TEST_USER, cls.SQL_TEST_USER_WITH_PASSWORD))

        @classmethod
        def see_if_database_exists(cls):
            """Return whether our test database exists"""
            output = run_command("psql", "-U {0} -l -A -t".format(cls.SQL_TEST_USER), "Find test database")
            for line in output:
                if line.startswith(cls.SQL_TEST_DB_NAME):
                    return True
            return False

        def _createdb(self):
            """Assume there is no db already and create one"""
            run_command("createdb", "-U {0} {1}".format(self.SQL_TEST_USER, self.SQL_TEST_DB_NAME), "Create test database")

        def _dropdb(self):
            """Assume there is a db to delete and drop it"""
            run_command("dropdb", "-U {0} {1}".format(self.SQL_TEST_USER, self.SQL_TEST_DB_NAME), "Delete test database")

        def run_sql_command(self, command, desc, extra=""):
            """Run some command with psql cli"""
            return run_command("psql", "-U {0} {1} -c \"{2}\" {3} -t -A".format(self.SQL_TEST_USER, self.SQL_TEST_DB_NAME, command, extra), desc)

        it "has a plain and django alias":
            assert 'psql' in PsqlDriver.aliases
            assert 'django.db.backends.postgresql_psycopg2' in PsqlDriver.aliases

    describe "Mysql Driver":
        # __only_run_tests_in_children__ Means the tests in the parent describe are run here

        SQL_ENGINE = 'mysql'
        DRIVER_KLS = MysqlDriver

        @classmethod
        def setupClass(cls):
            try:
                if cls.see_if_database_exists():
                    cls._dropdb.im_func(cls)
                else:
                    cls._createdb.im_func(cls)
            except FailedToRun:
                assert False, dedent("""
                    Couldn't ask mysql for info. Perhaps you don't have a {0} user in your mysql?

                    Try::

                        $ sudo mysql

                        > create user {0};
                        > grant all privileges on {2}.* to '{0}'@'localhost' with grant option;

                        > create user {1} identified by 'password';
                        > grant usage on *.* to '{1}'@'localhost' identified by 'password';
                        > grant all privileges on {2}.* to '{1}'@'localhost' with grant option;
                """.format(cls.SQL_TEST_USER, cls.SQL_TEST_USER_WITH_PASSWORD, cls.SQL_TEST_DB_NAME))

        @classmethod
        def see_if_database_exists(cls):
            """Return whether our test database exists"""
            output = run_command("mysql", "--user {0} --batch -s -e \"show databases\"".format(cls.SQL_TEST_USER), "Find test database")
            for line in output:
                if line.startswith(cls.SQL_TEST_DB_NAME):
                    return True
            return False

        def _createdb(self):
            """Assume there is no db already and create one"""
            run_command("mysql", "--user {0} -e \"create database {1}\"".format(self.SQL_TEST_USER, self.SQL_TEST_DB_NAME), "Create test database")

        def _dropdb(self):
            """Assume there is a db to delete and drop it"""
            run_command("mysql", "--user {0} -e \"drop database {1}\"".format(self.SQL_TEST_USER, self.SQL_TEST_DB_NAME), "Delete test database")

        def run_sql_command(self, command, desc, extra=""):
            """Run some command with mysql cli"""
            return run_command("mysql", "--user {0} {1} -e \"{2}\" {3} --batch -s".format(self.SQL_TEST_USER, self.SQL_TEST_DB_NAME, command, extra), desc)

        it "has a plain and django alias":
            assert 'mysql' in MysqlDriver.aliases
            assert 'django.db.backends.mysql' in MysqlDriver.aliases

    describe "Sqlite Driver":
        # __only_run_tests_in_children__ Means the tests in the parent describe are run here

        SQL_ENGINE = 'sqlite3'
        DRIVER_KLS = SqliteDriver

        @classmethod
        def setupClass(cls):
            cls.SQL_TEST_DB_NAME = tempfile.NamedTemporaryFile(delete=False).name

        @classmethod
        def see_if_database_exists(cls):
            """Return whether our test database exists"""
            return os.path.exists(cls.SQL_TEST_DB_NAME)

        def _createdb(self):
            """Sqlite just makes the database if it doesn't exist"""
            return run_command("sqlite3", "{0} .schema".format(self.SQL_TEST_DB_NAME), "Making database")

        def _dropdb(self):
            """Assume there is a db to delete and drop it"""
            os.remove(self.SQL_TEST_DB_NAME)

        def run_sql_command(self, command, desc, extra=""):
            """Run some command with sqlite cli"""
            return run_command("sqlite3", "{1} \"{2}\" {3}".format(self.SQL_TEST_USER, self.SQL_TEST_DB_NAME, command, extra), desc)

        def insert_values(self, table_name, values):
            """Sqlite version on travis ci is too old :("""
            for val in values:
                self.run_sql_command("insert into {0} values {1}".format(table_name, val), "Inserting value {0}".format(val))

        it "has a plain and django alias":
            assert 'sqlite3' in SqliteDriver.aliases
            assert 'django.db.backends.sqlite3' in SqliteDriver.aliases

