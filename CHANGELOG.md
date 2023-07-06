# Changelog

All notable changes to this project will be documented in this file.

## 0.0.7 (2023-07-06)
- A fix where `send_post_create_signal()` was being called twice when creating an object through `BulkTrackerQuerySet.create()`

## 0.0.6 (2023-05-28)
- Inheriting from BulkTrackerQuerySet is no longer mandatory. 
- If you don't have a custom Manager/QuerySet, You can just make your model inherit BulkTrackerModel.

## 0.0.5 (2023-03-07)
- Fix where `send_post_update_signal()` was relying on the queryset being ordered
