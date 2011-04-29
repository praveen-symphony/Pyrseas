# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject
    ~~~~~~~~~~~~~~~~

    This defines two low level classes and an intermediate class.
    Most Pyrseas classes are derived from either DbObject or
    DbObjectDict.
"""


class DbObject(object):
    "A single object in a database catalog, e.g., a schema, a table, a column"

    def __init__(self, **attrs):
        """Initialize the catalog object from a dictionary of attributes

        :param attrs: the dictionary of attributes

        Non-key attributes without a value are discarded.
        """
        for key, val in attrs.items():
            if val or key in self.keylist:
                setattr(self, key, val)

    def key(self):
        """Return a tuple that identifies the database object

        :return: a single value or a tuple
        """
        lst = [getattr(self, k) for k in self.keylist]
        return len(lst) == 1 and lst[0] or tuple(lst)


class DbSchemaObject(DbObject):
    "A database object that is owned by a certain schema"

    def extern_key(self):
        """Return the key to be used in external maps for this object

        :return: string
        """
        return '%s %s' % (self.objtype.lower(), self.name)

    def qualname(self):
        """Return the schema-qualified name of the object

        :return: string

        No qualification is used if the schema is 'public'.
        """
        return self.schema == 'public' and self.name \
            or "%s.%s" % (self.schema, self.name)

    def unqualify(self):
        """Adjust the schema and table name if the latter is qualified"""
        if hasattr(self, 'table') and '.' in self.table:
            tbl = self.table
            dot = tbl.index('.')
            if self.schema == tbl[:dot]:
                self.table = tbl[dot + 1:]

    def comment(self):
        """Return a SQL COMMENT statement for the object

        :return: SQL statement
        """
        if hasattr(self, 'description'):
            descr = "'%s'" % self.description
        else:
            descr = 'NULL'
        return "COMMENT ON %s %s IS %s" % (self.objtype, self.qualname(),
                                           descr)

    def drop(self):
        """Return a SQL DROP statement for the object

        :return: SQL statement
        """
        if not hasattr(self, 'dropped') or not self.dropped:
            self.dropped = True
            return "DROP %s %s" % (self.objtype, self.qualname())
        return []

    def rename(self, newname):
        """Return a SQL ALTER statement to RENAME the object

        :param newname: the new name of the object
        :return: SQL statement
        """
        return "ALTER %s %s RENAME TO %s" % (self.objtype, self.qualname(),
                                             newname)

    def set_search_path(self):
        """Return a SQL SET search_path if not in the 'public' schema"""
        stmt = ''
        if self.schema != 'public':
            stmt = "SET search_path TO %s, pg_catalog" % self.schema
        return stmt


class DbObjectDict(dict):
    """A dictionary of database objects, all of the same type"""

    cls = DbObject
    query = ''

    def __init__(self, dbconn=None):
        """Initialize the dictionary

        :param dbconn: a DbConnection object

        If dbconn is not None, the _from_catalog method is called to
        initialize the dictionary from the catalogs.
        """
        dict.__init__(self)
        self.dbconn = dbconn
        if dbconn:
            self._from_catalog()

    def _from_catalog(self):
        """Initialize the dictionary by querying the catalogs

        This is may be overriden by derived classes as needed.
        """
        for obj in self.fetch():
            self[obj.key()] = obj

    def fetch(self):
        """Fetch all objects from the catalogs using the class query

        :return: list of self.cls objects
        """
        if not self.dbconn.conn:
            self.dbconn.connect()
        data = self.dbconn.fetchall(self.query)
        return [self.cls(**dict(row)) for row in data]