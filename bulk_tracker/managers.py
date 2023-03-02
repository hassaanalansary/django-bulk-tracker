from __future__ import annotations

from django.db import connections, transaction
from django.db.models import Expression, Manager, QuerySet
from django.db.models.expressions import Case, Value, When
from django.db.models.functions import Cast

from bulk_tracker.helper_objects import TrackingInfo
from bulk_tracker.signals import (
    post_update_signal,
    send_post_create_signal,
    send_post_update_signal,
)
from bulk_tracker.utils import get_old_values


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
        old_values = (get_old_values(obj, kwargs) for obj in self)
        # 2- create a new queryset based on the PK.
        # because the user may be updating the same value as the criteria which will lead to an empty queryset if we
        # loop on `self` again. i.e. `Post.objects.filter(title="The Midnight Wolf").update(title="The Sunset Wolf")`
        queryset = self.model.objects.filter(pk__in=(instance.pk for instance in self)).only(*kwargs.keys())

        result = super().update(**kwargs)
        send_post_update_signal(queryset, self.model, old_values, tracking_info_)
        return result

    def create(self, *, tracking_info_: TrackingInfo | None = None, **kwargs):
        """
        Create a new object with the given kwargs, saving it to the database
        and returning the created object.
        """
        obj = super().create(**kwargs)
        send_post_create_signal([obj], model=self.model, tracking_info_=tracking_info_)
        return obj

    # This function is just copied from django core, with minor modification to accept TrackingInfo
    def bulk_update(
        self, objs, fields, batch_size=None, *args, tracking_info_: TrackingInfo | None = None, **kwargs
    ) -> None:
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

    def bulk_create(self, *args, tracking_info_: TrackingInfo | None = None, **kwargs):
        """
        Insert each of the instances into the database. Do *not* call
        save() on each of the instances, do not send any pre/post_save
        signals, and do not set the primary key attribute if it is an
        autoincrement field (except if features.can_return_rows_from_bulk_insert=True).
        Multi-table models are not supported.
        Will send `post_create_signal` with the created objects
        """
        objs = super().bulk_create(*args, **kwargs)
        send_post_create_signal(objs, self.model, tracking_info_)
        return objs


class BulkTrackerManager(Manager):
    pass
