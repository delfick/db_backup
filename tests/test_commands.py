# coding: spec

from db_backup.errors import BadBackupFile, NonEmptyDatabase
from db_backup.commands import backup, restore

from tests.utils import a_temp_directory, path_to, assert_is_binary, a_temp_file

from unittest import TestCase
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
                expected = os.path.join(backup_dir, filename)
                recipients = ["bob@bob.com"]
                database_settings = {"name": database, "engine": "sqlite3"}

                backup(database_settings, recipients, backup_dir, gpg_home)
                assert os.path.exists(expected)
                assert_is_binary(expected)

describe TestCase, "Restore command":
    it "complains if the restore_from backup file doesn't exist":
        with a_temp_file() as restore_from:
            os.remove(restore_from)
            with self.assertRaisesRegexp(BadBackupFile, "The backup file at '{0}' doesn't exist".format(restore_from)):
                database_settings = mock.Mock(name="database_settings")
                restore(database_settings, restore_from)

    @mock.patch("db_backup.commands.DatabaseHandler")
    it "complains if the database isn't empty", FakeDatabaseHandler:
        handler = mock.Mock(name="handler")
        database_settings = mock.Mock(name="database_settings")

        FakeDatabaseHandler.side_effect = lambda settings: handler
        handler.is_empty.side_effect = lambda: False

        with a_temp_file() as restore_from:
            with self.assertRaisesRegexp(NonEmptyDatabase, "Sorry, won't restore to a database that isn't empty"):
                restore(database_settings, restore_from)
                FakeDatabaseHandler.assert_called_once_with(database_settings)
                handler.is_empty.assert_called_once()

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

