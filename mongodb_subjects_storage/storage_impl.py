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

from datetime import datetime

from bson import ObjectId

import logging

from pymongo import errors, WriteConcern, ReadPreference, MongoClient
from pymongo.read_concern import ReadConcern

logger = logging.getLogger(__name__)

from krules_core.subject import PropertyType


class SubjectsMongoStorage(object):
    atomic_ops_coll = "_atomic_ops"

    def __init__(self, subject, db, collection,
                 client_args=(),
                 client_kwargs={},
                 use_atomic_ops_collection=True,
                 atomic_ops_collection_size=5242880,
                 atomic_ops_collection_max=1000):

        # use_atomic_ops_collection is a capped collection in which a record is written
        # with an incremental value for each read and subsequent write operation on subject.
        # The violation of a unique index will allow to intercept a greater number of transactions in conflict
        # with a cost in terms of performances that can tend to be acceptable.
        # Note that if the amount of potentially conflicting atomic operations is high
        # and the resulting consistency of the data is critical, MongoDB may not be the appropriate backend solution.
        # In this case it is suggested to use the Redis backend implementation

        self._subject = str(subject)
        self._use_atomic_ops = use_atomic_ops_collection
        client = MongoClient(*client_args, **client_kwargs)

        if collection not in client[db].list_collection_names():
            try:
                _ = client[db].create_collection(collection)
                _.create_index([("name", 1)], unique=True)
            except errors.OperationFailure:
                pass
            except errors.CollectionInvalid:
                pass

        if self._use_atomic_ops and self.atomic_ops_coll not in client[db].list_collection_names():
            try:
                _ = client[db].create_collection(self.atomic_ops_coll,
                                                 capped=True, size=atomic_ops_collection_size,
                                                 max=atomic_ops_collection_max)
                _.create_index([("subject", 1), ("property", 1), ("counter", 1)],
                               unique=True)
            except errors.OperationFailure:
                pass
            except errors.CollectionInvalid:
                pass

        self._collection = collection
        self._db = db
        self._client = client

    def _get_collection(self):
        return self._client[self._db][self._collection]

    def __str__(self):
        return "{} instance for {}".format(self.__class__.__name__, self._subject)

    def is_concurrency_safe(self):
        return True

    def is_persistent(self):
        return True

    def load(self):
        res = {
            PropertyType.DEFAULT: {},
            PropertyType.EXTENDED: {}
        }

        doc = self._get_collection().find_one(
            {"name": self._subject},
            projection={"_id": False, "_lock": False, "name": False, "_event_info": False}
        )
        if doc is None:
            doc = {}

        for k, v in doc.items():
            res[k[0]][k[1:]] = v
        return res[PropertyType.DEFAULT], res[PropertyType.EXTENDED]

    def store(self, inserts=[], updates=[], deletes=[]):

        if len(inserts) + len(updates) + len(deletes) == 0:
            return

        hset = {}
        for prop in tuple(inserts) + tuple(updates):
            hset[f"{prop.type}{prop.name}"] = prop.get_value()
        hunset = {}
        for prop in deletes:
            hunset[f"{prop.type}{prop.name}"] = 1

        hupdate = {}
        if len(hset):
            hupdate.update({"$set": hset})
        if len(hunset):
            hupdate.update({"$unset": hunset})

        self._get_collection().update_one(
            {"name": self._subject},
            hupdate,
            upsert=True
        )

    def set(self, prop, old_value_default=None):

        pname = f"{prop.type}{prop.name}"
        values = [None, old_value_default]

        def _commit_with_retry(session):
            while True:
                try:
                    # Commit uses write concern set at transaction start.
                    session.commit_transaction()
                    break
                except (errors.ConnectionFailure, errors.OperationFailure) as exc:
                    # Can retry commit
                    if exc.has_error_label("UnknownTransactionCommitResult"):
                        logger.warning("UnknownTransactionCommitResult, retrying "
                                       "commit operation ...")
                        continue
                    else:
                        logger.error("Error during commit ...")
                        raise

        def _callback(session):

            value_args = []

            last_op = {
                "subject": self._subject,
                "property": pname,
                "counter": 0
            }

            if self._use_atomic_ops:
                with session.client[self._db][self.atomic_ops_coll] \
                        .find({"subject": self._subject, "property": pname}) \
                        .sort([("counter", -1)]).limit(1) as cursor:
                    try:
                        last_op = cursor[0].copy()
                    except IndexError:
                        pass

            # https://www.mongodb.com/blog/post/how-to-select--for-update-inside-mongodb-transactions
            current = session.client[self._db][self._collection].find_one_and_update(
                {"name": self._subject},
                {"$set": {"_lock": ObjectId()}}
            )

            if current is None:
                current = {}
            values[1] = current.get(pname, old_value_default)
            if callable(prop.value):
                value_args.append(values[1])
            values[0] = prop.get_value(*value_args)

            if self._use_atomic_ops:
                last_op["counter"] += 1
                try:
                    session.client[self._db][self.atomic_ops_coll].insert_one(
                        {"subject": self._subject, "property": pname,
                         "counter": last_op["counter"],
                         "createdAt": datetime.now()},
                    )
                except errors.DuplicateKeyError:
                    logger.warning("conflict during atomic operation")
                    raise

            session.client[self._db][self._collection].update_one(
                {"name": self._subject},
                {"$set": {pname: values[0]}},
                upsert=True,

            )
            _commit_with_retry(session)

        with self._client.start_session() as session:
            while True:
                try:
                    session.with_transaction(
                        _callback, read_concern=ReadConcern("majority"),
                        write_concern=WriteConcern("majority", j=True, wtimeout=5000),
                        read_preference=ReadPreference.PRIMARY
                    )
                    break
                except (errors.DuplicateKeyError):
                    continue

        return values[0], values[1]

    def get(self, prop):
        """
        Get a single property
        Raises AttributeError if not found
        """
        pname = f"{prop.type}{prop.name}"
        res = self._get_collection().find_one(
            {"name": self._subject},
        )
        if res is None or pname not in res:
            raise AttributeError(prop.name)

        return res[pname]

    def delete(self, prop):
        """
        Delete a single property
        """
        pname = f"{prop.type}{prop.name}"
        self._get_collection().update_one(
            {"name": self._subject},
            {"$unset": {
                pname: ""
            }}
        )

    def get_ext_props(self):

        props = {}
        res = self._get_collection().find_one(
            {"name": self._subject},
            projection={"_id": False, "_lock": False, "name": False, "_event_info": False}
        )
        if res is not None:
            for pname, pvalue in res.items():
                if pname.startswith(PropertyType.EXTENDED):
                    props[pname[len(PropertyType.EXTENDED):]] = pvalue

        return props

    def flush(self):
        self._get_collection().delete_one({
            "name": self._subject
        })
        return self
