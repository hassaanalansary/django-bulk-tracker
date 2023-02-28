from typing import Optional

from django.db import models
from model_utils import FieldTracker

from bulk_tracker.helper_objects import TrackingInfo
from bulk_tracker.signals import send_post_create_signal, send_post_update_signal


class BulkTrackerModel(models.Model):
    tracker: FieldTracker

    class Meta:
        abstract = True

    def _save_table(self, *args, **kwargs):
        updated = super()._save_table(*args, **kwargs)
        self._is_created = not updated
        return updated

    def save(
        self,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
        tracking_info_: Optional[TrackingInfo] = None,
    ):
        if hasattr(self, "tracker") and self.tracker:
            changed = self.tracker.changed()
            super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)
            if not self._is_created and changed:
                send_post_update_signal(
                    [self], model=self.__class__, old_values=[changed], tracking_info_=tracking_info_
                )
            elif self._is_created:
                send_post_create_signal([self], model=self.__class__, tracking_info_=tracking_info_)

        else:
            raise AttributeError(
                f"Model {self.__class__} doesn't have tracker, please add `tracker = FieldTracker()` to your model"
            )
