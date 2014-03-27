# coding: spec

from db_backup.errors import BadBackupFile, NonEmptyDatabase
from db_backup.commands import backup, restore, sanitise_path

from tests.utils import a_temp_directory, path_to, assert_is_binary, a_temp_file
from tests.case import TestCase

import uuid
import mock
import os

describe TestCase, "Backup command":
    @mock.patch("db_backup.commands.make_backup_filename")
    it "encrypts the dump into the backup_directory", fake_make_backup_filename:
        filename = str(uuid.uuid1())
        fake_make_backup_filename.side_effect = lambda: filename
        with a_temp_file() as database:
            with a_temp_directory() as backup_dir:
                self.assertEqual(len(os.listdir(backup_dir)), 0)

                gpg_home = path_to("gpg")
                recipients = ["bob@bob.com"]
                database_settings = {"name": database, "engine": "sqlite3"}

                destination = backup(database_settings, recipients, backup_dir, gpg_home=gpg_home)

                self.assertEqual(destination, os.path.join(backup_dir, filename))
                assert os.path.exists(destination)
                assert_is_binary(destination)

    it "Can take in a function to make the backup filename":
        filename = str(uuid.uuid1())
        filename_maker = lambda: filename
        with a_temp_file() as database:
            with a_temp_directory() as backup_dir:
                self.assertEqual(len(os.listdir(backup_dir)), 0)

                gpg_home = path_to("gpg")
                recipients = ["bob@bob.com"]
                database_settings = {"name": database, "engine": "sqlite3"}

                destination = backup(database_settings, recipients, backup_dir, filename_maker=filename_maker, gpg_home=gpg_home)

                self.assertEqual(destination, os.path.join(backup_dir, filename))
                assert os.path.exists(destination)
                assert_is_binary(destination)

describe TestCase, "Sanitise path":
    @mock.patch("db_backup.commands.urlparse.urlparse")
    it "passes the url through if it doesn't have a file scheme", fake_urlparse:
        path = mock.Mock(name="path")
        info = mock.Mock(name="info")
        fake_urlparse.return_value = info

        info.scheme = None
        info.netloc = "one"
        info.path = "/two/three"
        self.assertIs(sanitise_path(path), path)

        info.scheme = "file"
        self.assertEqual(sanitise_path(path), "one/two/three")

    it "correctly identifies schemes":
        self.assertEqual(sanitise_path("file://blah/and/things.gpg"), "blah/and/things.gpg")
        self.assertEqual(sanitise_path("file:///stuff/or/trees.blah"), "/stuff/or/trees.blah")
        self.assertEqual(sanitise_path("ftp://qwerty"), "ftp://qwerty")
        self.assertEqual(sanitise_path("s3://dvorak"), "s3://dvorak")

describe TestCase, "Restore command":
    @mock.patch("db_backup.commands.sanitise_path")
    it "complains if the restore_from backup file doesn't exist", fake_sanitise_path:
        with a_temp_file() as restore_from:
            os.remove(restore_from)
            fake_sanitise_path.return_value = restore_from
            with self.assertRaisesRegexp(BadBackupFile, "The backup file at '{0}' doesn't exist".format(restore_from)):
                database_settings = mock.Mock(name="database_settings")
                restore(database_settings, restore_from)
            fake_sanitise_path.assert_called_once_with(restore_from)

    @mock.patch("db_backup.commands.sanitise_path")
    @mock.patch("db_backup.commands.DatabaseHandler")
    it "complains if the database isn't empty", FakeDatabaseHandler, fake_sanitise_path:
        handler = mock.Mock(name="handler")
        database_settings = mock.Mock(name="database_settings")

        FakeDatabaseHandler.side_effect = lambda settings: handler
        handler.is_empty.side_effect = lambda: False

        with a_temp_file() as restore_from:
            fake_sanitise_path.return_value = restore_from
            with self.assertRaisesRegexp(NonEmptyDatabase, "Sorry, won't restore to a database that isn't empty"):
                restore(database_settings, restore_from)
                FakeDatabaseHandler.assert_called_once_with(database_settings)
                handler.is_empty.assert_called_once()
            fake_sanitise_path.assert_called_once_with(restore_from)

    @mock.patch("db_backup.commands.Encryptor")
    @mock.patch("db_backup.commands.DatabaseHandler")
    it "Decrypts from the backup and gives it to the database handler", FakeDatabaseHandler, FakeEncryptor:
        handler = mock.Mock(name="handler")
        gpg_home = mock.Mock(name="gpg_home")
        encryptor = mock.Mock(name="encryptor")
        decrypted = mock.Mock(name="decrypted")
        database_settings = mock.Mock(name="database_settings")

        FakeDatabaseHandler.side_effect = lambda settings: handler
        handler.is_empty.side_effect = lambda: True

        FakeEncryptor.side_effect = lambda: encryptor
        encryptor.decrypt.side_effect = lambda *args, **kwargs: decrypted

        with a_temp_file() as restore_from:
            restore(database_settings, restore_from, gpg_home)
            handler.restore.assert_called_once_with(decrypted)

