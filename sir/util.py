# Copyright (c) 2014 Wieland Hoffmann
# License: MIT, see LICENSE for details
import logging
import solr
import urllib2

from . import config
from .schema import SCHEMA
from json import loads
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


logger = logging.getLogger("sir")


class VersionMismatchException(Exception):
    def __init__(self, core, expected, actual):
        self.core = core
        self.expected = expected
        self.actual = actual

    def __str__(self):
        return "%s: Expected %1.1f, got %1.1f" % (self.core,
                                                  self.expected,
                                                  self.actual)


def db_session(db_uri):
    """
    Creates a new :class:`sqla:sqlalchemy.orm.session.sessionmaker`.

    :param str db_uri: A :ref:`database URL <sqla:database_urls>` for
                       SQLAlchemy.

    :rtype: :class:`sqla:sqlalchemy.orm.session.sessionmaker`
    """
    e = create_engine(db_uri, server_side_cursors=False)
    S = sessionmaker(bind=e)
    return S


def solr_connection(solr_uri, core):
    """
    Creates a :class:`solr:solr.Solr` connection for the core ``core`` at the
    Solr server listening on ``solr_uri``.

    :param str solr_uri:
    :param str core:
    :raises urllib2.URLError: if a ping to the cores ping handler doesn't
                              succeed
    :rtype: :class:`solr:solr.Solr`
    """
    core_uri = solr_uri + "/" + core
    ping_uri = core_uri + "/admin/ping"

    logger.debug("Pinging %s", ping_uri)
    urllib2.urlopen(ping_uri)

    logger.debug("Connection to the Solr core at %s", core_uri)
    return solr.Solr(core_uri)


def solr_version_check(core):
    """
    Checks that the version of the Solr core ``core`` at ``solr_uri`` matches
    ``version``.
    :param str solr_uri:
    :param str core:
    :raises urllib2.URLError: If the Solr core can't be reached
    :raises VersionMismatchException: If the version in Solr is different than
                                      the supported one
    """
    expected_version = SCHEMA[core].version
    solr_uri = config.CFG.get("solr", "uri")
    u = urllib2.urlopen("%s/%s/schema/version" % (solr_uri, core))
    content = loads(u.read())
    seen_version = content["version"]
    if not seen_version == expected_version:
        raise VersionMismatchException(core, expected_version, seen_version)
    logger.debug("%s: version %1.1f matches %1.1f", core, expected_version, seen_version)


def check_solr_cores_version(cores):
    """
    Checks multiple Solr cores for version compatibility

    :param [str] cores: The names of the cores
    :raises VersionMismatchException: If the version of any core in Solr is
                                      different than the supported one
    """
    map(solr_version_check, cores)