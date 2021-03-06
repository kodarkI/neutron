#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import functools
import unittest.case

from oslo_db.sqlalchemy import provision
from oslo_db.sqlalchemy import test_base
import testtools.testcase

from neutron.common import constants as n_const
from neutron.tests import base
from neutron.tests import tools


def create_resource(prefix, creation_func, *args, **kwargs):
    """Create a new resource that does not already exist.

    If prefix isn't 'max_length' in size, a random suffix is concatenated to
    ensure it is random. Otherwise, 'prefix' is used as is.

    :param prefix: The prefix for a randomly generated name
    :param creation_func: A function taking the name of the resource
           to be created as it's first argument.  An error is assumed
           to indicate a name collision.
    :param *args *kwargs: These will be passed to the create function.
    """

    # Don't generate a random name if prefix is already full-length.
    if len(prefix) == n_const.DEVICE_NAME_MAX_LEN:
        return creation_func(prefix, *args, **kwargs)

    while True:
        name = base.get_rand_name(
            max_length=n_const.DEVICE_NAME_MAX_LEN,
            prefix=prefix)
        try:
            return creation_func(name, *args, **kwargs)
        except RuntimeError:
            pass


def no_skip_on_missing_deps(wrapped):
    """Do not allow a method/test to skip on missing dependencies.

    This decorator raises an error if a skip is raised by wrapped method when
    OS_FAIL_ON_MISSING_DEPS is evaluated to True. This decorator should be used
    only for missing dependencies (including missing system requirements).
    """

    @functools.wraps(wrapped)
    def wrapper(*args, **kwargs):
        try:
            return wrapped(*args, **kwargs)
        except (testtools.TestCase.skipException, unittest.case.SkipTest) as e:
            if base.bool_from_env('OS_FAIL_ON_MISSING_DEPS'):
                tools.fail(
                    '%s cannot be skipped because OS_FAIL_ON_MISSING_DEPS '
                    'is enabled, skip reason: %s' % (wrapped.__name__, e))
            raise
    return wrapper


# NOTE(cbrandily): Define mysql+pymysql backend implementation
@provision.BackendImpl.impl.dispatch_for("mysql+pymysql")
class PyMySQLBackendImpl(provision.BackendImpl):

    default_engine_kwargs = {'mysql_sql_mode': 'TRADITIONAL'}

    def create_opportunistic_driver_url(self):
        return "mysql+pymysql://openstack_citest:openstack_citest@localhost/"

    def create_named_database(self, engine, ident, conditional=False):
        with engine.connect() as conn:
            if not conditional or not self.database_exists(conn, ident):
                conn.execute("CREATE DATABASE %s" % ident)

    def drop_named_database(self, engine, ident, conditional=False):
        with engine.connect() as conn:
            if not conditional or self.database_exists(conn, ident):
                conn.execute("DROP DATABASE %s" % ident)

    def database_exists(self, engine, ident):
        return bool(engine.scalar("SHOW DATABASES LIKE '%s'" % ident))


impl = provision.BackendImpl.impl("mysql+pymysql")
url = impl.create_opportunistic_driver_url()
# NOTE(cbrandily): Declare mysql+pymysql backend implementation
provision.Backend("mysql+pymysql", url)


# NOTE(cbrandily): Define mysql+pymysql db fixture
class PyMySQLFixture(test_base.DbFixture):
    DRIVER = 'mysql+pymysql'


# NOTE(cbrandily): Define mysql+pymysql base testcase
class MySQLTestCase(test_base.DbTestCase):
    """Base test class for MySQL tests.

    Enforce the supported driver, which is PyMySQL.
    If the MySQL db is unavailable then this test is skipped, unless
    OS_FAIL_ON_MISSING_DEPS is enabled.
    """
    FIXTURE = PyMySQLFixture
    SKIP_ON_UNAVAILABLE_DB = not base.bool_from_env('OS_FAIL_ON_MISSING_DEPS')


class PostgreSQLTestCase(test_base.PostgreSQLOpportunisticTestCase):
    """Base test class for PostgreSQL tests.

    If the PostgreSQL db is unavailable then this test is skipped, unless
    OS_FAIL_ON_MISSING_DEPS is enabled.
    """
    SKIP_ON_UNAVAILABLE_DB = not base.bool_from_env('OS_FAIL_ON_MISSING_DEPS')
