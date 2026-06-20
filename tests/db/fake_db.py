from datetime import datetime, timezone


class FakeResult:
    def __init__(self, first=None, scalar=None, all_items=None, rowcount=0):
        self._first = first
        self._scalar = scalar
        self._all_items = all_items or []
        self.rowcount = rowcount

    def scalars(self):
        return self

    def first(self):
        return self._first

    def scalar(self):
        return self._scalar

    def all(self):
        return self._all_items


class FakeDB:
    def __init__(self, *results):
        self.results = list(results)
        self.executed = []
        self.added = []
        self.committed = False
        self.rolled_back = False

    async def execute(self, query):
        self.executed.append(query)
        if not self.results:
            raise AssertionError(f"Unexpected query: {query}")
        return self.results.pop(0)

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = len(self.added) + 1
        self.added.append(obj)

    async def commit(self):
        self.committed = True

    async def flush(self):
        return None

    async def refresh(self, obj, *args, **kwargs):
        if getattr(obj, "id", None) is None:
            obj.id = 1
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(timezone.utc)
        if getattr(obj, "updated_at", None) is None:
            obj.updated_at = datetime.now(timezone.utc)

    async def rollback(self):
        self.rolled_back = True
