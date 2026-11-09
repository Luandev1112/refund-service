"""Refunds for merchants. create_refund() is called by an AWS Lambda function; when the call times out,
Lambda retries it with the same request_id."""

import uuid

from .store import Cache, ConditionalCheckFailed, Table


class RefundService:
    def __init__(self, table: Table, cache: Cache):
        self.table = table
        self.cache = cache

    def create_refund(self, request_id: str, merchant_id: str, amount_cents: int) -> str:
        """Refund amount_cents from the merchant's balance and return the refund id."""
        refund_id = str(uuid.uuid4())
        # One transaction: the request marker, the refund and the balance change are saved together or not at all.
        # The balance uses an atomic ADD, so two refunds for one merchant never overwrite each other.
        try:
            self.table.transact_write(
                puts=[
                    ({"pk": f"request#{request_id}", "refund_id": refund_id}, True),
                    ({
                        "pk": f"refund#{refund_id}",
                        "request_id": request_id,
                        "merchant_id": merchant_id,
                        "amount_cents": amount_cents,
                    }, False),
                ],
                adds=[(f"merchant#{merchant_id}", "balance_cents", -amount_cents)],
            )
        except ConditionalCheckFailed:
            return self.table.get_item(f"request#{request_id}")["refund_id"]
        self.cache.delete(f"balance:{merchant_id}")
        return refund_id

    def balance(self, merchant_id: str) -> int:
        """The merchant's balance in cents. Read very often, so it is cached."""
        key = f"balance:{merchant_id}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        item = self.table.get_item(f"merchant#{merchant_id}")
        value = item["balance_cents"] if item else 0
        self.cache.set(key, value)
        return value

    def refunds_for(self, merchant_id: str) -> list:
        return [r for r in self.table.query("refund#") if r["merchant_id"] == merchant_id]
