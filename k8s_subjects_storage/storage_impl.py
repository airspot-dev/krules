
class SubjectsK8sStorage(object):

    def __init__(self, subject, resource):
        self._subject = str(subject)
        self._resource = resource

    def __str__(self):
        return "{} instance for {}".format(self.__class__, self._subject)

    def _get_resource(self):
        if self._resource is None:
            pass

    def is_concurrency_safe(self):
        return False

    def is_persistent(self):
        return True

    def load(self):
        pass
        # res = {
        #     PropertyType.DEFAULT: {},
        #     PropertyType.EXTENDED: {}
        # }
        # hset = self._conn.hgetall(f"s:{self._subject}")
        # for k, v in hset.items():
        #     k = k.decode("utf-8")
        #     res[k[0]][k[1:]] = json.loads(v)
        # return res[PropertyType.DEFAULT], res[PropertyType.EXTENDED]

    def store(self, inserts=[], updates=[], deletes=[]):
        pass
        # if len(inserts)+len(updates)+len(deletes) == 0:
        #     return
        #
        # skey = f"s:{self._subject}"
        # hset = {}
        # for prop in tuple(inserts)+tuple(updates):
        #     hset[f"{prop.type}{prop.name}"] = prop.json_value()
        # with self._conn.pipeline() as pipe:
        #     pipe.hmset(skey, hset)
        #     for pkey in [f"{el.type}{el.name}" for el in deletes]:
        #         pipe.hdel(skey, pkey)
        #     pipe.execute()


    def set(self, prop, old_value_default=None):
        """
        Set value for property, works both in update and insert
        Returns old value
        """
        # skey = f"s:{self._subject}"
        # pname = f"{prop.type}{prop.name}"
        # if callable(prop.value):
        #     while True:
        #         try:
        #             with self._conn.pipeline() as pipe:
        #                 pipe.watch(skey)
        #                 old_value = pipe.hget(skey, pname)
        #                 pipe.multi()
        #                 if old_value is None:
        #                     old_value = old_value_default
        #                 else:
        #                     old_value = json.loads(old_value)
        #                 new_value = prop.json_value(old_value)
        #                 pipe.hset(skey, pname, new_value)
        #                 pipe.execute()
        #                 break
        #         except redis.WatchError:
        #             continue
        #     new_value = json.loads(new_value)
        # else:
        #     with self._conn.pipeline() as pipe:
        #         pipe.hget(skey, pname)
        #         pipe.hset(skey, pname, prop.json_value())
        #         old_value, _ = pipe.execute()
        #         if old_value is None:
        #             old_value = old_value_default
        #         else:
        #             old_value = json.loads(old_value)
        #
        #         new_value = prop.get_value()
        #
        # return new_value, old_value

    def get(self, prop):
        """
        Get a single property
        Raises AttributeError if not found
        """
        # skey = f"s:{self._subject}"
        # pname = f"{prop.type}{prop.name}"
        # with self._conn.pipeline() as pipe:
        #     pipe.hexists(skey, pname)
        #     pipe.hget(skey, pname)
        #     exists, value = pipe.execute()
        # if not exists:
        #     raise AttributeError(prop.name)
        # return json.loads(value)

    def delete(self, prop):
        """
        Delete a single property
        """
        # skey = f"s:{self._subject}"
        # pname = f"{prop.type}{prop.name}"
        # self._conn.hdel(skey, pname)

    def get_ext_props(self):
        pass
        # props = {}
        # skey = f"s:{self._subject}"
        # for pname, pval in self._conn.hscan_iter(skey, f"{PropertyType.EXTENDED}*"):
        #     props[pname[1:].decode("utf-8")] = json.loads(pval)
        # return props

    def flush(self):
        pass
        # skey = f"s:{self._subject}"
        # self._conn.delete(skey)
        # return self
