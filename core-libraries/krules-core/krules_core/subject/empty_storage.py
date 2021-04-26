class EmptySubjectStorage:

    def is_concurrency_safe(self):

        return False

    def is_persistent(self):

        return False

    def load(self):
        return {}, {}

    def store(self, inserts=[], updates=[], deletes=[]):
        pass

    def set(self, prop, old_value_default=None):

        return None, None

    def get(self, prop):

        return None

    def delete(self, prop):
        pass

    def get_ext_props(self):

        return {}

    def flush(self):

        return self
