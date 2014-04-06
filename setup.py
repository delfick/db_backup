from setuptools import setup, find_packages

setup(
      name = "db_backup"
    , version = "0.1.3"
    , packages = ['db_backup'] + ['db_backup.%s' % pkg for pkg in find_packages('db_backup')]
    , include_package_data = True

    , extras_require =
      { "tests":
        [ "noseOfYeti>=1.4.9"
        , "nose"
        , "mock"
        ]
      }

    # metadata for upload to PyPI
    , url = "http://db-backup.readthedocs.org"
    , author = "Stephen Moore"
    , author_email = "stephen@delfick.com"
    , description = "Code for creating encrypted backups of databases"
    , license = "WTFPL"
    , keywords = "database encrypted backup restore"
    )
