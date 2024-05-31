from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from django.db import transaction
from django.dispatch import Signal

from bulk_tracker.helper_objects import ModifiedObject, TrackingInfo


if TYPE_CHECKING:
    from bulk_tracker.models import BulkTrackerModel


"""
Signals that will be emitted when a bulk operations are used.
If you use the BulkTrackerModel
"""

"""
The receiver function should look like this
@receiver(post_update_signal, sender=MyModel)
def i_am_a_receiver_function(
    sender,
    objects: list[ModifiedObject[MyModel]],
    tracking_info_: TrackingInfo | None = None,
    **kwargs,
):
    do_stuff()
"""
post_update_signal = Signal()  # custom signal for bulk and single update


"""
@receiver(post_create_signal, sender=MyModel)
def i_am_a_receiver_function(
    sender,
    objects: list[ModifiedObject[MyModel]],
    tracking_info_: TrackingInfo | None = None,
    **kwargs,
):
    do_stuff()
"""
post_create_signal = Signal()  # custom signal for bulk and single create

"""
@receiver(post_delete_signal, sender=MyModel)
def i_am_a_receiver_function(
    sender,
    objects: list[ModifiedObject[MyModel]],
    tracking_info_: TrackingInfo | None = None,
    **kwargs,
):
    do_stuff()
"""
post_delete_signal = Signal()  # custom signal for bulk and single delete


def send_post_create_signal(
    objs: Iterable[BulkTrackerModel], model: type[BulkTrackerModel], tracking_info_: TrackingInfo | None = None
):
    modified_objects = [ModifiedObject(ob, {}) for ob in objs]
    if modified_objects:
        if tracking_info_ and tracking_info_.is_robust:
            method = post_create_signal.send_robust
        else:
            method = post_create_signal.send
        transaction.on_commit(
            lambda: method(
                objects=modified_objects,
                sender=model,
                tracking_info_=tracking_info_,
            )
        )


def send_post_update_signal(
    queryset: Iterable[BulkTrackerModel],
    model: type[BulkTrackerModel],
    old_values: dict[int, [dict[str, Any]]],  # {pk: changed_values}
    tracking_info_: TrackingInfo | None = None,
) -> None:
    modified_objects = []
    for obj in queryset:
        changed = old_values[obj.pk]
        diff_dict = {}
        for key, old_value in changed.items():
            if getattr(obj, key) != old_value:  # if new_values != old_value
                diff_dict[key] = old_value
        if diff_dict:
            modified_objects.append(ModifiedObject(obj, diff_dict))

    if modified_objects:
        if tracking_info_ and tracking_info_.is_robust:
            method = post_update_signal.send_robust
        else:
            method = post_update_signal.send
        transaction.on_commit(
            lambda: method(
                sender=model,
                objects=modified_objects,
                tracking_info_=tracking_info_,
            )
        )


def send_post_delete_signal(
    objs: Iterable[BulkTrackerModel],
    model: type[BulkTrackerModel],
    tracking_info_: TrackingInfo | None = None,
):
    modified_objects = [ModifiedObject(ob, {}) for ob in objs]
    if modified_objects:
        if tracking_info_ and tracking_info_.is_robust:
            method = post_delete_signal.send_robust
        else:
            method = post_delete_signal.send
        transaction.on_commit(
            lambda: method(
                objects=modified_objects,
                sender=model,
                tracking_info_=tracking_info_,
            )
        )
