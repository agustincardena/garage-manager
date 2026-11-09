"""Work order statuses. Values match the ``order_status`` table ids.

The flow is: PENDING -> COMPLETED or CANCELLED. The former intermediate
statuses (2 scheduled, 3 in_progress, 4 waiting_parts) were removed; the
database migration moves any order still in them back to PENDING.
"""

from __future__ import annotations

from enum import IntEnum


class OrderStatus(IntEnum):
    PENDING = 1
    COMPLETED = 5
    CANCELLED = 6


CLOSED_STATUSES = (OrderStatus.COMPLETED, OrderStatus.CANCELLED)
REMOVED_STATUS_IDS = (2, 3, 4)
