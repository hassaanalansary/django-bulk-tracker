from django.db import models
from model_utils import FieldTracker

from bulk_tracker.helper_objects import TrackingInfo
from bulk_tracker.signals import post_update_signal


class ModelWithLogging(models.Model):
    tracker: FieldTracker

    class Meta:
        abstract = True

    def _save_table(self, *args, **kwargs):
        updated = super()._save_table(*args, **kwargs)
        self._is_created = not updated
        return updated

    def save(self, *args, tracking_info_: TrackingInfo | None = None, **kwargs):
        if hasattr(self, "tracker") and self.tracker:
            changed = self.tracker.changed()
            super().save(*args, **kwargs)
            if not self._is_created and changed:
                post_update_signal([self], model=self.__class__, old_values=[changed])
        else:
            raise AttributeError(
                f"Model {self.__class__} doesn't have tracker, please add `tracker = FieldTracker()` to your model"
            )
