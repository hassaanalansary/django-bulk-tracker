# Changelog

All notable changes to this project will be documented in this file.

## 0.2.1 (2024-07-24)
- A fix where `post_delete_signal()` was called twice for a model in a foreign-key relationship gets deleted with a cascade deletion constraint.

## 0.2.0 (2024-07-24)
- `post_delete_signal()` is now being sent if a parent model was deleted and triggered a cascade delete.

now `post_delete_signal()` will be sent for all objects that are deleted in a cascade delete.
This requires the parent to inherit from `BulkTrackerModel` or have a custom manager that inherits from `BulkTrackerManager`.
post_delete_signal()` is not being sent yet if child is tracked by `BulkTrackerModel` but parent is not.

## 0.1.0 (2024-05-31)
- `post_create_signal()`, `post_update_signal()`, and `post_delete_signal()` were not waiting for transaction to commit before sending signals.

This was causing the signals to be sent before the object was actually created/updated/deleted, Causing a race condition.
This has been fixed by using `transaction.on_commit()`.
This will ensure that the signals are sent after the transaction is committed.
- Add support for send_robust by using `tracking_info_TrackingInfo(is_robust=True)`. `is_robust=False` by default.

## 0.0.7 (2023-07-06)
- A fix where `send_post_create_signal()` was being called twice when creating an object through `BulkTrackerQuerySet.create()`

## 0.0.6 (2023-05-28)
- Inheriting from BulkTrackerQuerySet is no longer mandatory.
- If you don't have a custom Manager/QuerySet, You can just make your model inherit BulkTrackerModel.

## 0.0.5 (2023-03-07)
- Fix where `send_post_update_signal()` was relying on the queryset being ordered
