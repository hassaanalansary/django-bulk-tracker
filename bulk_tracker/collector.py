from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy

from _operator import attrgetter
from django.db import transaction
from django.db.models import signals, sql
from django.db.models.deletion import Collector

from bulk_tracker.helper_objects import TrackingInfo
from bulk_tracker.signals import post_delete_signal, send_post_delete_signal


class BulkTrackerCollector(Collector):

    def delete(self, *, tracking_info_: TrackingInfo | None = None):
        # sort instance collections
        for model, instances in self.data.items():
            self.data[model] = sorted(instances, key=attrgetter("pk"))

        # if possible, bring the models in an order suitable for databases that
        # don't support transactions or cannot defer constraint checks until the
        # end of a transaction.
        self.sort()
        # number of objects deleted for each model label
        deleted_counter = Counter()

        # Optimize for the case with a single obj and no dependencies
        if len(self.data) == 1 and len(instances) == 1:
            instance = list(instances)[0]
            if self.can_fast_delete(instance):
                to_be_deleted = None
                if post_delete_signal.has_listeners(model):
                    to_be_deleted = deepcopy(instance)
                with transaction.mark_for_rollback_on_error(self.using):
                    count = sql.DeleteQuery(model).delete_batch([instance.pk], self.using)
                if to_be_deleted:
                    send_post_delete_signal([to_be_deleted], model, tracking_info_)
                setattr(instance, model._meta.pk.attname, None)
                return count, {model._meta.label: count}

        with transaction.atomic(using=self.using, savepoint=False):
            # send pre_delete signals
            for model, obj in self.instances_with_model():
                origin = {}
                if hasattr(self, "origin"):  # origin was removed in Django 3.2 and 4.0.
                    origin = {"origin": self.origin}
                if not model._meta.auto_created:
                    signals.pre_delete.send(
                        sender=model,
                        instance=obj,
                        using=self.using,
                        **origin,
                    )
            bulk_tracker_deletes = defaultdict(list)
            # fast deletes
            for qs in self.fast_deletes:
                if post_delete_signal.has_listeners(qs.model):
                    bulk_tracker_deletes[qs.model].extend(deepcopy(qs))

                count = qs._raw_delete(using=self.using)
                if count:
                    deleted_counter[qs.model._meta.label] += count

            # update fields
            for model, instances_for_fieldvalues in self.field_updates.items():
                for (field, value), instances in instances_for_fieldvalues.items():
                    query = sql.UpdateQuery(model)
                    query.update_batch([obj.pk for obj in instances], {field.name: value}, self.using)

            # reverse instance collections
            for instances in self.data.values():
                instances.reverse()

            # delete instances
            for model, instances in self.data.items():
                query = sql.DeleteQuery(model)
                pk_list = [obj.pk for obj in instances]
                count = query.delete_batch(pk_list, self.using)
                if count:
                    deleted_counter[model._meta.label] += count
                if post_delete_signal.has_listeners(model):
                    bulk_tracker_deletes[model].extend(deepcopy(instances))

                if not model._meta.auto_created:
                    origin = {}
                    if hasattr(self, "origin"):  # origin was removed in Django 3.2 and 4.0.
                        origin = {"origin": self.origin}
                    for obj in instances:
                        signals.post_delete.send(
                            sender=model,
                            instance=obj,
                            using=self.using,
                            **origin,
                        )
            for model, objs in bulk_tracker_deletes.items():
                send_post_delete_signal(objs, model, tracking_info_)

        # update collected instances
        for instances_for_fieldvalues in self.field_updates.values():
            for (field, value), instances in instances_for_fieldvalues.items():
                for obj in instances:
                    setattr(obj, field.attname, value)
        for model, instances in self.data.items():
            for instance in instances:
                setattr(instance, model._meta.pk.attname, None)
        return sum(deleted_counter.values()), dict(deleted_counter)
