django-bulk-tracker documentation
=================================
django-bulk-tracker is a reusable app for Django that allow you to have signals (``post_update_signal`` and ``post_create_signal``)
that will be sent with your bulk operations.
i.e. ``bulk_update()``, ``bulk_create()``, ``queryset.update()``.

django-bulk-tracker allows you to pass tracking date related to your save/create operation.
a feature that is missing from django builtin ``post_save`` signal.

You can use ``post_update_signal`` and ``post_create_signal`` and ``tracking_info`` to stop relying
on ``post_save`` method that force you to use ``.save()`` method.
which is a bottleneck for a lot of django projects.

django-bulk-tracker will send
- ``post_update_signal`` when you do ``.save()`` on an existing model instance, ``queryset.update()``, or ``bulk_update()``
- ``post_create_signal`` when you do ``.save()`` on a new model instance, ``create()``, or ``bulk_create()``

Dependencies
============
1. Python >=3.9
2. Django >=3.2
3. django-model-utils >=4.0.0



Contents
--------

.. toctree::
   :maxdepth: 2

   installation
   usage
   internals


Contribute to django-bulk-tracker
---------------------------------

If you discovered a bug or want to improve the code, please submit an issue and/or pull request via GitHub.
Before submitting a new issue, please make sure there is no issue submitted that involves the same problem.

| GitHub repository: https://github.com/hassaanalansary/django-bulk-tracker
| Issues: https://github.com/hassaanalansary/django-bulk-tracker


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
