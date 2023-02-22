from django.dispatch import Signal


"""
Signal that will be emitted when a bulk operations are used.
If you use the BulkTrackerModel

The receiver function should look like this
@receiver(post_update_signal, sender=MyModel)
def i_am_a_receiver_function(
    sender,
    objects: list[ModifiedObject[MyModel]],
    tracking_info_: Optional[TrackingInfo] = None,
    **kwargs,
):
    do_stuff()
"""

# custom signal for bulk update
post_update_signal = Signal()

# custom signal for bulk create
post_create_signal = Signal()
