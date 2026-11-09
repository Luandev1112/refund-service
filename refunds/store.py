"""In-memory stand-ins for DynamoDB and Redis, so the exercise runs with no AWS account or server.
Same ideas as the real services, with a smaller API. You don't need to change this file."""

import copy


class ConditionalCheckFailed(Exception):
    """Raised like DynamoDB's ConditionalCheckFailedException."""


class Table:
    """Like a DynamoDB table whose partition key is "pk"."""

    def __init__(self):
        self._items = {}

    def put_item(self, item, only_if_new=False):
        """Save the item under item["pk"], replacing any item with the same key.
        only_if_new=True works like ConditionExpression="attribute_not_exists(pk)":
        if the key already exists, nothing is saved and ConditionalCheckFailed is raised."""
        if only_if_new and item["pk"] in self._items:
            raise ConditionalCheckFailed(item["pk"])
        self._items[item["pk"]] = copy.deepcopy(item)

    def transact_write(self, puts, adds=()):
        """Like TransactWriteItems. puts is a list of (item, only_if_new) pairs.
        adds is a list of (pk, attribute, delta) triples, like UpdateExpression="ADD attribute :delta":
        the number changes by delta, and a missing item or attribute starts at 0.
        Every condition is checked first. If any fails, nothing is saved and
        ConditionalCheckFailed is raised. Otherwise every put and add is applied."""
        for item, only_if_new in puts:
            if only_if_new and item["pk"] in self._items:
                raise ConditionalCheckFailed(item["pk"])
        for item, _ in puts:
            self._items[item["pk"]] = copy.deepcopy(item)
        for pk, attribute, delta in adds:
            item = self._items.setdefault(pk, {"pk": pk})
            item[attribute] = item.get(attribute, 0) + delta

    def get_item(self, pk):
        """Return a copy of the item with that key, or None."""
        item = self._items.get(pk)
        return copy.deepcopy(item) if item else None

    def query(self, prefix):
        """Return copies of every item whose key starts with prefix."""
        return [copy.deepcopy(v) for k, v in self._items.items() if k.startswith(prefix)]


class Cache:
    """Like Redis GET, SET and DEL."""

    def __init__(self):
        self._values = {}

    def get(self, key):
        return self._values.get(key)

    def set(self, key, value):
        self._values[key] = value

    def delete(self, key):
        self._values.pop(key, None)
