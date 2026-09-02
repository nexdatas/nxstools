#!/usr/bin/env python
#   This file is part of nexdatas - Tango Server for NeXus data writer
#
#    Copyright (C) 2012-2018 DESY, Jan Kotanski <jkotan@mail.desy.de>
#
#    nexdatas is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    nexdatas is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with nexdatas.  If not, see <http://www.gnu.org/licenses/>.
# \package test nexdatas
# \file runtest.py
# the unittest runner
#

import os
import sys

try:
    __import__("PyTango")
    # if module PyTango available
    PYTANGO_AVAILABLE = True
except ImportError as e:
    PYTANGO_AVAILABLE = False
    print("PyTango is not available: %s" % e)

try:
    __import__("h5py")
    # if module h5py available
    H5PY_AVAILABLE = True
except ImportError as e:
    H5PY_AVAILABLE = False
    print("h5py is not available: %s" % e)

try:
    __import__("pninexus.h5cpp")
    # if module pninexus.h5cpp available
    H5CPP_AVAILABLE = True
except ImportError as e:
    H5CPP_AVAILABLE = False
    print("h5cpp is not available: %s" % e)
except SystemError as e:
    H5CPP_AVAILABLE = False
    print("h5cpp is not available: %s" % e)


import unittest

import NXSTools_test
import RedisWriter_test
import RedisUtils_test


if not H5PY_AVAILABLE and not H5CPP_AVAILABLE:
    raise Exception("Please install h5py or pninexus.h5cpp")


# list of available databases
DB_AVAILABLE = []

try:
    try:
        import MySQLdb
    except ImportError:
        import pymysql as MySQLdb
        MySQLdb.install_as_MySQLdb()

    # connection arguments to MYSQL DB
    args = {}
    args["db"] = 'tango'
    # args["host"] = 'localhost'
    args["read_default_file"] = '/etc/mysql/my.cnf'
    # inscance of MySQLdb
    print(args)
    mydb = MySQLdb.connect(**args)
    mydb.close()
    DB_AVAILABLE.append("MYSQL")
except Exception as e1:
    try:
        try:
            import MySQLdb
        except ImportError:
            import pymysql as MySQLdb
            MySQLdb.install_as_MySQLdb()
        from os.path import expanduser
        home = expanduser("~")
        # connection arguments to MYSQL DB
        cnffile = '%s/.my.cnf' % home
        args2 = {
            # 'host': u'localhost',
            'db': u'tango',
            'read_default_file': '%s/.my.cnf' % home,
            'use_unicode': True}
        # inscance of MySQLdb
        print(args2)
        mydb = MySQLdb.connect(**args2)
        mydb.close()
        DB_AVAILABLE.append("MYSQL")
    except ImportError as e2:
        print("MYSQL not available: %s %s" % (e1, e2))
    except Exception as e2:
        print("MYSQL not available: %s %s" % (e1, e2))
    except Exception:
        print("MYSQL not available")


try:
    import psycopg2
    # connection arguments to PGSQL DB
    args = {}
    args["database"] = 'mydb'
    # inscance of psycog2
    pgdb = psycopg2.connect(**args)
    pgdb.close()
    DB_AVAILABLE.append("PGSQL")
except ImportError as e:
    print("PGSQL not available: %s" % e)
except Exception as e:
    print("PGSQL not available: %s" % e)
except Exception:
    print("PGSQL not available")


try:
    import cx_Oracle
    # pwd
    with open('%s/pwd' % os.path.dirname(NXSTools_test.__file__)) as fl:
        passwd = fl.read()[:-1]

    # connection arguments to ORACLE DB
    args = {}
    args["dsn"] = (
        "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=dbsrv01.desy.de)"
        "(PORT=1521))(LOAD_BALANCE=yes)(CONNECT_DATA=(SERVER=DEDICATED)"
        "(SERVICE_NAME=desy_db.desy.de)(FAILOVER_MODE=(TYPE=NONE)"
        "(METHOD=BASIC)(RETRIES=180)(DELAY=5))))")
    args["user"] = "read"
    args["password"] = passwd
    # inscance of cx_Oracle
    ordb = cx_Oracle.connect(**args)
    ordb.close()
    DB_AVAILABLE.append("ORACLE")
except ImportError as e:
    print("ORACLE not available: %s" % e)
except Exception as e:
    print("ORACLE not available: %s" % e)
except Exception:
    print("ORACLE not available")


if H5PY_AVAILABLE:
    import H5PYWriter_test
    import FileWriterH5PY_test
    import NXSCollectH5PY_test
    import NXSFileInfoH5PY_test
    import NXSCreatePyEvalH5PY_test
if H5CPP_AVAILABLE:
    import H5CppWriter_test
    import NXSCreatePyEvalH5Cpp_test
    import FileWriterH5Cpp_test
    import NXSCollectH5Cpp_test
    import NXSFileInfoH5Cpp_test
    import H5CppRedisWriter_test

if H5PY_AVAILABLE and H5CPP_AVAILABLE:
    import FileWriterH5CppH5PY_test

if H5CPP_AVAILABLE or H5PY_AVAILABLE:
    import NXSCollect_test
    import NXSFileInfo_test


if PYTANGO_AVAILABLE:
    import NXSCreateClientDSFS_test
    import NXSCreateClientDSFS2_test
    import NXSCreateClientDSFS3_test
    import NXSCreate_test
    import NXSCreateCompare_test

    import NXSCreateTangoDSFS_test
    import NXSCreateTangoDSFS2_test
    import NXSCreateTangoDSFS3_test

    import NXSCreateDeviceDSFS_test
    import NXSCreateDeviceDSFS2_test
    import NXSCreateDeviceDSFS3_test

    import NXSCreateCompFS_test
    import NXSCreateCompFS2_test
    import NXSCreateCompFS3_test

    import NXSCreateOnlineDSFS_test
    import NXSCreateOnlineDSFS2_test
    import NXSCreateOnlineDSFS3_test

    import NXSCreateOnlineCPFS_test
    import NXSCreateOnlineCPFS2_test
    import NXSCreateOnlineCPFS3_test

    import NXSCreatePoolDSFS_test
    import NXSCreatePoolDSFS2_test
    import NXSCreatePoolDSFS3_test

    import NXSCreateSECoPCPFS_test

    import NXSData_test

    if "MYSQL" in DB_AVAILABLE:
        import NXSetUp_test

        import NXSCreateStdCompFS_test
        import NXSCreateStdCompFS2_test
        import NXSCreateStdCompFS3_test

        import NXSConfig_test
        import NXSCreateClientDSDB_test
        import NXSCreateClientDSDB2_test
        import NXSCreateClientDSDBR_test
        import NXSCreateClientDSDBR2_test

        import NXSCreateTangoDSDB_test
        import NXSCreateTangoDSDB2_test
        import NXSCreateTangoDSDBR_test
        import NXSCreateTangoDSDBR2_test

        import NXSCreateCompDB_test
        import NXSCreateCompDB2_test
        import NXSCreateCompDBR_test
        import NXSCreateCompDBR2_test

        import NXSCreateDeviceDSDB_test
        import NXSCreateDeviceDSDB2_test
        import NXSCreateDeviceDSDBR_test
        import NXSCreateDeviceDSDBR2_test
        import NXSCreateDeviceDSFS4_test

        import NXSCreateOnlineDSDB_test
        import NXSCreateOnlineDSDB2_test
        import NXSCreateOnlineDSDBR_test
        import NXSCreateOnlineDSDBR2_test
        import NXSCreateOnlineDSDBE_test
        import NXSCreateOnlineDSDBE2_test

        import NXSCreateOnlineCPDB_test
        import NXSCreateOnlineCPDB2_test
        import NXSCreateOnlineCPDBR_test
        import NXSCreateOnlineCPDBR2_test

        import NXSCreateStdCompDB_test
        import NXSCreateStdCompDB2_test
        import NXSCreateStdCompDBR_test
        import NXSCreateStdCompDBR2_test
        import NXSCreateStdCompDBE_test
        import NXSCreateStdCompDBE2_test

        import NXSCreatePoolDSDB_test
        import NXSCreatePoolDSDB2_test
        import NXSCreatePoolDSDBR_test
        import NXSCreatePoolDSDBR2_test

        import NXSCreateSECoPCPDB_test


# main function
def main():

    # test suit
    suite = unittest.TestSuite()

    if H5PY_AVAILABLE:
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                FileWriterH5PY_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                H5PYWriter_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCollectH5PY_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSFileInfoH5PY_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreatePyEvalH5PY_test))
    if H5CPP_AVAILABLE:
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                FileWriterH5Cpp_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                H5CppWriter_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCollectH5Cpp_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSFileInfoH5Cpp_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreatePyEvalH5Cpp_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                H5CppRedisWriter_test))
    if H5CPP_AVAILABLE and H5PY_AVAILABLE:
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                FileWriterH5CppH5PY_test))

    if H5CPP_AVAILABLE or H5PY_AVAILABLE or H5CPP_AVAILABLE:
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCollect_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSFileInfo_test))

    suite.addTests(
        unittest.defaultTestLoader.loadTestsFromModule(
            RedisWriter_test))
    suite.addTests(
        unittest.defaultTestLoader.loadTestsFromModule(
            RedisUtils_test))

    if PYTANGO_AVAILABLE:
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateClientDSFS_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateClientDSFS2_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateClientDSFS3_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreate_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateCompare_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSData_test))

        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateTangoDSFS_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateTangoDSFS2_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateTangoDSFS3_test))

        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateOnlineDSFS_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateOnlineDSFS2_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateOnlineDSFS3_test))

        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateOnlineCPFS_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateOnlineCPFS2_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateOnlineCPFS3_test))

        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreatePoolDSFS_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreatePoolDSFS2_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreatePoolDSFS3_test))

        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateSECoPCPFS_test))

        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateDeviceDSFS_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateDeviceDSFS2_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateDeviceDSFS3_test))

        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateCompFS_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateCompFS2_test))
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromModule(
                NXSCreateCompFS3_test))
        if "MYSQL" in DB_AVAILABLE:
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSetUp_test))

            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSConfig_test))

            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateStdCompFS_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateStdCompFS2_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateStdCompFS3_test))

            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateClientDSDB_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateClientDSDB2_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateClientDSDBR_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateClientDSDBR2_test))

            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateTangoDSDB_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateTangoDSDB2_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateTangoDSDBR_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateTangoDSDBR2_test))

            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateOnlineCPDB_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateOnlineCPDB2_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateOnlineCPDBR_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateOnlineCPDBR2_test))

            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateOnlineDSDB_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateOnlineDSDB2_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateOnlineDSDBR_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateOnlineDSDBR2_test))

            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateSECoPCPDB_test))

            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateOnlineDSDBE_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateOnlineDSDBE2_test))

            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateStdCompDB_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateStdCompDB2_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateStdCompDBR_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateStdCompDBR2_test))

            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateStdCompDBE_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateStdCompDBE2_test))

            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreatePoolDSDB_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreatePoolDSDB2_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreatePoolDSDBR_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreatePoolDSDBR2_test))

            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateDeviceDSDB_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateDeviceDSDB2_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateDeviceDSDBR_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateDeviceDSDBR2_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateDeviceDSFS4_test))

            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateCompDB_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateCompDB2_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateCompDBR_test))
            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(
                    NXSCreateCompDBR2_test))

    # test runner
    runner = unittest.TextTestRunner()
    # test result
    result = runner.run(suite).wasSuccessful()
    sys.exit(not result)

    #   if ts:
    #       ts.tearDown()


if __name__ == "__main__":
    main()
