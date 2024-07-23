Usage
=====

``django-bulk-tracker`` will emit a signal whenever you update, create, or delete a record in the database

``django-bulk-tracker`` supports bulk operations:

- ``queryset.update()``
- ``queryset.bulk_update()``
- ``queryset.bulk_create()``
- ``queryset.delete()``

and single operations:

- ``create()``
- ``save() # update and create``
- ``delete()``

all you need to do is to define your Model and inherit from::

    from bulk_tracker.models import BulkTrackerModel

    class Author(BulkTrackerModel):
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)

OR if you have a custom queryset inherit from or Don't want to support single-operation::

    from bulk_tracker.managers import BulkTrackerQuerySet

    class MyModelQuerySet(BulkTrackerQuerySet):
        def do_something_custom(self):
            pass


now you can listen to the signals ``post_update_signal``, ``post_create_signal``, ``post_delete_signal``::

    @receiver(post_update_signal, sender=MyModel)
    def i_am_a_receiver_function(
        sender,
        objects: list[ModifiedObject[MyModel]],
        tracking_info_: TrackingInfo | None = None,
        **kwargs,
    ):
        do_stuff()

.. hint::
    all signals have the same signature for consistency,
    and also in case you want to assign one function to listen to multiple signals


``ModifiedObject`` is a very simple object, it contains 2 attributes:
1- ``instance`` this is your model instance after it has been updated, or created
2- ``changed_values`` is dict[str, Any] which contains the changed fields only in case of ``post_update_signal``,
in case of ``post_create_signal`` and ``post_delete_signal``, ``changed_values`` will be an empty dict ``{}``


**Optionally** you can pass ``tracking_info_`` to your functions, as in::

    from bulk_tracker.helper_objects import TrackingInfo

    def a_function_that_updates_records():
        user = self.request.user
        MyModel.objects.filter(name='john').update(
            name='jack',
            tracking_info_=TrackingInfo(user=user, comment="Updated from a function", kwargs={'app-build':'1.1.8'}, is_robust=True),
            )

.. hint::
     ``tracking_info_`` has a trailing underscore to avoid collision with your actual fields

you can use ``TrackingInfo`` to implement any kind of behavior like logging in your
signal handlers and you need to capture more info about the operation that is happening.



For single operations as well
-----------------------------

- ``create()``
- ``save() # update and create``
- ``delete()``

to support we rely on the amazing library ``django-model-utils`` to track the model instances

1. do the above
2. you need to to inherit your model from ``BulkTrackerModel``
3. add ``tracker = FieldTracker()`` to your model

as in ::

    from bulk_tracker.models import BulkTrackerModel
    from model_utils import FieldTracker


    class MyModel(BulkTrackerModel):

        objects = MyModelQuerySet.as_manager() # MyModelManager() if you have
        tracker = FieldTracker()


robust_send
----------

``robust_send`` if you have multiple receivers for the same signal, and you want to make sure that all of them are executed, even if one of them raise an exception.
you can add ``TrackingInfo(is_robust=True)`` in your operation.
you can read more about robust_send in the [official documentation](https://docs.djangoproject.com/en/5.0/topics/signals/#sending-signals)

as in::

    MyModel.objects.filter(name='john').update(
        name='jack',
        tracking_info_=TrackingInfo(is_robust=True),
        )
Complete Example
================

::

    # models.py
    from bulk_tracker.models import BulkTrackerModel
    from model_utils import FieldTracker

    from myapp.managers import MyModelManager


    class MyModel(BulkTrackerModel):
        first_field = models.CharField()
        second_field = models.CharField()

        objects = MyModelManager()
        tracker = FieldTracker()

::

    # managers.py
    from bulk_tracker.managers import BulkTrackerQuerySet # optional


    class MyModelQuerySet(BulkTrackerQuerySet):
        pass


    class MyModelManager(BulkTrackerManager.from_queryset(MyModelQuerySet)): # optional
        pass

::

    # signal_handlers.py
    from bulk_tracker.signals import post_update_signal
    from bulk_tracker.helper_objects import ModifiedObject, TrackingInfo


    @receiver(post_update_signal, sender=MyModel)
    def i_am_a_receiver_function(
        sender,
        objects: list[ModifiedObject[MyModel]],
        tracking_info_: TrackingInfo | None = None,
        **kwargs,
    ):
        user = tracking_info_.user if tracking_info_ else None
        for modified_objects in modified_objects:
            if 'name' in modified_object.changed_values:
                log(f"field 'name' has changed by {user or ''}")
                notify_user()
