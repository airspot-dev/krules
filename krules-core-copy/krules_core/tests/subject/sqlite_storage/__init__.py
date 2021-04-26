# Copyright 2019 The KRules Authors
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# IMPORTANT!! ######################################################################################
# please note that this implementation must not be understood as valid for a production environment.
# It is provided for testing purposes only and to provide a basic reference interface
####################################################################################################
import json
import sqlite3

import logging
logger = logging.getLogger(__name__)

from krules_core.subject import PropertyType, SubjectExtProperty, SubjectProperty


class SQLLiteSubjectStorage(object):

    def __init__(self, subject, dbfile):
        self._dbfile = dbfile
        self._subject = subject
        self._conn = sqlite3.connect(dbfile)

        create_subjects_table_sql = """
            CREATE TABLE IF NOT EXISTS subjects (
                subject TEXT NOT NULL,
                property TEXT NOT NULL,
                proptype TEXT NOT NULL,
                propvalue TEXT,
                PRIMARY KEY (subject, property, proptype)
                ) WITHOUT ROWID
        """
        c = self._conn.cursor()
        c.execute(create_subjects_table_sql)
        c = self._conn.cursor()
        c.execute("CREATE INDEX IF NOT EXISTS idx_subjects ON subjects(subject)")
        self._close_connection()

    def __str__(self):

        dbtype = "onfile"
        if self._dbfile == ":memory:":
            dbtype = "inmemory"

        return "sqlite_{}_{}".format(dbtype, self._subject)

    def is_concurrency_safe(self):
        return self._dbfile != ":memory:"

    def is_persistent(self):
        return self._dbfile != ":memory:"

    def _get_connection(self):

        if self._dbfile == ":memory:":
            return self._conn
        self._conn.close()
        self._conn = sqlite3.connect(self._dbfile)
        return self._conn

    def _close_connection(self):
        # does not close connection if database is not persistent
        if self._dbfile != ":memory:":
            self._conn.close()

    def load(self):

        select_props_sql = """
            SELECT property, proptype, propvalue
            FROM subjects
            WHERE subject = ?
        """
        conn = self._get_connection()
        c = conn.cursor()
        c.execute(select_props_sql, (self._subject,))

        res = {
            PropertyType.DEFAULT: {},
            PropertyType.EXTENDED: {}
        }
        rows = c.fetchall()
        for row in rows:
            res[row[1]][row[0]] = json.loads(row[2])

        self._close_connection()

        return res[PropertyType.DEFAULT], res[PropertyType.EXTENDED]

    def store(self, inserts=[], updates=[], deletes=[]):

        conn = self._get_connection()

        sql_script = ""

        # inserts
        for prop in inserts:
            sql_script += "INSERT INTO subjects (subject, property, proptype, propvalue) "\
                          "VALUES ('{}', '{}', '{}', '{}');\n".format(
                self._subject, prop.name, prop.type, prop.json_value().replace("'", "''")
            )

        # updates
        for prop in updates:
            sql_script += "UPDATE subjects SET propvalue='{}' WHERE "\
                          "subject = '{}' "\
                          "AND property = '{}' "\
                          "AND proptype = '{}';".format(
                prop.json_value().replace("'", "''"), self._subject, prop.name, prop.type
            )

        # deletes
        for prop in deletes:
            sql_script += "DELETE FROM subjects WHERE " \
                          "subject = '{}' " \
                          "AND property = '{}' " \
                          "AND proptype = '{}';".format(
                self._subject, prop.name, prop.type
            )

        # TODO: when fails shoud a failback function should be called
        #   checking at least each insert property if needs update instead
        conn.executescript(sql_script)

        self._close_connection()

    def set(self, prop, old_value_default=None):
        """
        Set value for property, works both in update and insert
        Returns old value
        Note that for this implementation a write lock is required on the entire database,
        a row-level lock would be preferable
        """
        conn = self._get_connection()
        #c = conn.cursor()
        conn.execute("BEGIN IMMEDIATE")

        res = conn.execute("SELECT propvalue FROM subjects WHERE subject=? and property=? and proptype=?",
                        (self._subject, prop.name, prop.type)).fetchall()

        old_value = old_value_default

        try:
            if len(res):
                old_value = json.loads(res[0][0])

                conn.execute("UPDATE subjects SET propvalue=? WHERE subject=? and property=? and proptype=?",
                          (prop.json_value(old_value), self._subject, prop.name, prop.type))
            else:
                conn.execute("INSERT INTO subjects (subject, property, proptype, propvalue) "\
                              "VALUES ('{}', '{}', '{}', '{}');\n".format(
                    self._subject, prop.name, prop.type, prop.json_value(old_value_default))
                )
        except Exception as ex:
            conn.execute("ROLLBACK")
            self._close_connection()
            raise ex

        conn.execute("COMMIT")
        self._close_connection()

        new_value = prop.get_value(old_value)
        return new_value, old_value

    def get(self, prop):
        """
        Get a single property
        Raises AttributeError if not found
        """
        conn = self._get_connection()
        res = conn.execute("SELECT propvalue FROM subjects WHERE subject=? and property=? and proptype=?",
                        (self._subject, prop.name, prop.type)).fetchall()
        if not len(res):
            self._close_connection()
            raise AttributeError(prop.name)
        self._close_connection()
        return json.loads(res[0][0])

    # def incr(self, prop, amount=1):
    #     """
    #     some backends may have specialized functions for this operation (eg: redis)
    #     """
    #     prop.value = lambda x: x is None and 0 + amount or x + amount
    #     return self.set(prop)
    #
    # def decr(self, prop, amount=1):
    #     """
    #     some backends may have specialized functions for this operation (eg: redis)
    #     """
    #     prop.value = lambda x: x is None and 0 - amount or x - amount
    #     return self.set(prop)

    def delete(self, prop):
        """
        Delete a single property
        """
        conn = self._get_connection()

        conn.execute("DELETE FROM subjects WHERE subject = ? AND property = ? AND proptype = ?",
                     (self._subject, prop.name, prop.type))

        conn.commit()

        self._close_connection()

    def get_ext_props(self):

        conn = self._get_connection()

        props = conn.execute("SELECT property, propvalue from subjects WHERE proptype = ? and subject = ?",
                             (PropertyType.EXTENDED, self._subject)).fetchall()
        #res = [SubjectExtProperty(pname, json.loads(pvalue)) for pname, pvalue in props]
        self._close_connection()

        return dict((k, json.loads(v)) for k, v in props)


    ## WE DON?T NEED IT
    # def get_all_properties(self):
    #     """
    #     Get all properties
    #     """
    #     conn = self._get_connection()
    #     rows = conn.execute("SELECT property, proptype, propvalue FROM subjects WHERE subject = ?", (self._subject,))\
    #         .fetchall()
    #
    #
    #     res = []
    #     for pname, ptype, pvalue in rows:
    #         klass = ptype == PropertyType.DEFAULT and SubjectProperty or SubjectExtProperty
    #         res.append(klass(pname, json.loads(pvalue)))
    #
    #     self._close_connection()
    #
    #     return res

    def flush(self):

        conn = self._get_connection()

        conn.execute("DELETE FROM subjects WHERE subject = '{}';".format(self._subject))

        conn.commit()

        self._close_connection()

