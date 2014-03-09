# coding: spec

from db_backup.databases import DatabaseInfo, DatabaseHandler, PsqlDriver, MysqlDriver, SqliteDriver
from db_backup.errors import NoDBDriver

from noseOfYeti.tokeniser.support import noy_sup_setUp
from unittest import TestCase
import mock

describe TestCase, "DatabaseInfo":
    it "takes in the attrs as specified by ATTRS":
        self.assertGreater(len(DatabaseInfo.ATTRS), 0)
        vals = {key:mock.Mock(name=key) for key in DatabaseInfo.ATTRS}
        database_info = DatabaseInfo(**vals)
        for key in DatabaseInfo.ATTRS:
            self.assertIs(getattr(database_info, key), vals[key])

    it "converts None values into empty strings":
        self.assertGreater(len(DatabaseInfo.ATTRS), 0)
        vals = {key:mock.Mock(name=key) for key in DatabaseInfo.ATTRS}
        vals["port"] = None
        database_info = DatabaseInfo(**vals)
        for key in DatabaseInfo.ATTRS:
            if key != "port":
                self.assertIs(getattr(database_info, key), vals[key])
        self.assertIs(database_info.port, "")

    it "can turn back into a dictionary":
        vals = {key:mock.Mock(name=key) for key in DatabaseInfo.ATTRS}
        self.assertEqual(DatabaseInfo(**vals).as_dict(), vals)

    it "can become a DatabaseInfo from a dict with extra or missing args":
        vals = {key:mock.Mock(name=key) for key in DatabaseInfo.ATTRS}
        del vals["port"]
        vals["other"] = mock.Mock(name="other")
        database_info = DatabaseInfo.from_dict(vals)
        for key in vals:
            if key != "other":
                self.assertIs(getattr(database_info, key), vals[key])
        self.assertEqual(database_info.port, "")
        assert not hasattr(database_info, "other")

describe TestCase, "DatabaseHandler":
    before_each:
        self.name = mock.Mock(name="name")
        self.engine = mock.Mock(name="engine")
        self.database_info = DatabaseInfo.from_dict({"engine": self.engine, "name": self.name})

    it "selects appropriate db driver":
        paired = [
              ("sqlite3", SqliteDriver), ("django.db.backends.sqlite3", SqliteDriver)
            , ("mysql", MysqlDriver), ("django.db.backends.mysql", MysqlDriver)
            , ("psql", PsqlDriver), ("django.db.backends.postgresql_psycopg2", PsqlDriver)
            ]

        for alias, expected in paired:
            self.database_info.engine = alias
            handler = DatabaseHandler(self.database_info)
            self.assertIs(type(handler.db_driver), expected)
            self.assertIs(handler.db_driver.database_info, self.database_info)

    it "uses db driver it is given":
        self.database_info.engine = "alkjdf"
        driver = mock.Mock(name="driver")
        handler = DatabaseHandler(self.database_info, driver)
        self.assertIs(handler.db_driver, driver)

    it "complains if it can't find the correct db driver":
        self.database_info.engine = "adksf"
        with self.assertRaisesRegexp(NoDBDriver, "Couldn't find driver for engine adksf"):
            DatabaseHandler(self.database_info).db_driver

    it "can be given other drivers":
        driver = mock.Mock(name="driver")
        driver.aliases = ("adksf", )
        instance = mock.Mock(name="driver instance")
        driver.side_effect = lambda info: instance

        self.database_info.engine = "adksf"
        handler = DatabaseHandler(self.database_info)
        handler.add_db_driver(driver)
        self.assertIs(handler.db_driver, instance)

    it "converts database info to DatabaseInfo object if it's a dictionary":
        handler = DatabaseHandler({"name": "blah", "engine": "sqlite3"})
        self.assertIs(type(handler.database_info), DatabaseInfo)
        self.assertEqual(handler.database_info.name, "blah")
        self.assertEqual(handler.database_info.engine, "sqlite3")

    describe "Commands":
        before_each:
            self.db_driver = mock.Mock(name="db driver")
            self.database_info = mock.Mock(name="database_info")
            self.handler = DatabaseHandler(self.database_info, self.db_driver)

        describe "Dump":
            it "returns stdout from running the dump command":
                self.db_driver.dump_command.side_effect = lambda: ("echo", "-e \"stuff\nand\nthings\"")
                self.assertEqual(list(self.handler.dump()), ["stuff\nand\nthings\n"])

        describe "is_empty":
            it "Asks the driver what it thinks":
                result = mock.Mock(name="result")
                self.db_driver.is_empty.side_effect = lambda: result
                self.assertIs(self.handler.is_empty(), result)

        describe "restore":
            @mock.patch("db_backup.databases.feed_process")
            @mock.patch("db_backup.databases.check_and_start_process")
            it "Uses the restore_command to make a restorer that it feeds with the provided data", fake_check_and_start_process, fake_feed_process:
                food = mock.Mock(name="food")
                command = mock.Mock(name="command")
                options = mock.Mock(name="options")
                restorer = mock.Mock(name="restorer")

                self.db_driver.restore_command.side_effect = lambda: (command, options)
                fake_check_and_start_process.side_effect = lambda *args, **kwargs: restorer

                self.handler.restore(food)
                fake_check_and_start_process.assert_called_once_with(command, options, "Restore command", capture_stdin=True)
                fake_feed_process.assert_called_once_with(restorer, "Restoring database", food)

