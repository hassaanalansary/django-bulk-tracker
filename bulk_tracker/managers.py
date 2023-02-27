from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from django.db import connections, transaction
from django.db.models import Case, Expression, Manager, QuerySet, Value, When
from django.db.models.functions import Cast

from bulk_tracker.helper_objects import ModifiedObject, TrackingInfo
from bulk_tracker.signals import post_update_signal


if TYPE_CHECKING:
    from bulk_tracker.models import BulkTrackerModel


class BulkTrackerQuerySet(QuerySet):
    def update(self, *, tracking_info_: TrackingInfo | None = None, **kwargs):
        """
        This will be the single place for updating objects
        This will prevent other users from using post_save signals and other built-in signals
        because in my opinion they are bad practice, and prevent developers from supporting bulk operations
        instead this will send `post_update_signal` with all the changed objects and their old_values

        if `post_update_signal` has listeners this will result in an extra 2 queries in order to retrieve the diff.
        """
        signal_has_listener = post_update_signal.has_listeners(sender=self.model)
        # if the model doesn't have any listener on this signal, don't bother doing anything
        if not signal_has_listener:
            return super().update(**kwargs)

        # if we have listeners:
        # 1- we will consume the queryset
        old_values = (_get_old_values(obj, kwargs) for obj in self)
        # 2- create a new queryset based on the PK.
        # because the user may be updating the same value as the criteria which will lead to an empty queryset if we
        # loop on `self` again. i.e. `Post.objects.filter(title="The Midnight Wolf").update(title="The Sunset Wolf")`
        queryset = self.model.objects.filter(pk__in=(instance.pk for instance in self)).only(*kwargs.keys())

        result = super().update(**kwargs)
        send_post_update_signal(queryset, self.model, old_values, tracking_info_)
        return result


def send_post_update_signal(
    queryset: Iterable[BulkTrackerModel],
    model: type[BulkTrackerModel],
    old_values: Iterable[dict[str, Any]],
    tracking_info_: TrackingInfo | None = None,
) -> None:
    modified_objects = []
    for obj, changed in zip(queryset, old_values):
        diff_dict = {}
        for key, old_value in changed.items():
            if getattr(obj, key) != old_value:  # if new_values != old_value
                diff_dict[key] = old_value
        if diff_dict:
            modified_objects.append(ModifiedObject(obj, diff_dict))

    if modified_objects:
        post_update_signal.send(
            sender=model,
            objects=modified_objects,
            tracking_info_=tracking_info_,
        )


class BulkTrackerManager(Manager):
    # This function is just copied from django core, with minor modification to accept TrackingInfo
    def bulk_update(self, objs, fields, batch_size=None, *, tracking_info_: TrackingInfo | None = None) -> None:
        """
        Update the given fields in each of the given objects in the database.
        """
        if batch_size is not None and batch_size < 0:
            raise ValueError("Batch size must be a positive integer.")
        if not fields:
            raise ValueError("Field names must be given to bulk_update().")
        objs = tuple(objs)
        if any(obj.pk is None for obj in objs):
            raise ValueError("All bulk_update() objects must have a primary key set.")
        fields = [self.model._meta.get_field(name) for name in fields]
        if any(not f.concrete or f.many_to_many for f in fields):
            raise ValueError("bulk_update() can only be used with concrete fields.")
        if any(f.primary_key for f in fields):
            raise ValueError("bulk_update() cannot be used with primary key fields.")
        if not objs:
            return
        # PK is used twice in the resulting update query, once in the filter
        # and once in the WHEN. Each field will also have one CAST.
        max_batch_size = connections[self.db].ops.bulk_batch_size(["pk", "pk"] + fields, objs)
        batch_size = min(batch_size, max_batch_size) if batch_size else max_batch_size
        requires_casting = connections[self.db].features.requires_casted_case_in_updates
        batches = (objs[i : i + batch_size] for i in range(0, len(objs), batch_size))
        updates = []
        for batch_objs in batches:
            update_kwargs = {}
            for field in fields:
                when_statements = []
                for obj in batch_objs:
                    attr = getattr(obj, field.attname)
                    if not isinstance(attr, Expression):
                        attr = Value(attr, output_field=field)
                    when_statements.append(When(pk=obj.pk, then=attr))
                case_statement = Case(*when_statements, output_field=field)
                if requires_casting:
                    case_statement = Cast(case_statement, output_field=field)
                update_kwargs[field.attname] = case_statement
            updates.append(([obj.pk for obj in batch_objs], update_kwargs))
        with transaction.atomic(using=self.db, savepoint=False):
            for pks, update_kwargs in updates:
                self.filter(pk__in=pks).update(tracking_info_=tracking_info_, **update_kwargs)


def _get_old_values(obj, kwargs):
    return {key: getattr(obj, key) for key, value in kwargs.items()}
