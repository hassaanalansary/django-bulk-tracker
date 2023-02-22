from bulk_tracker.managers import BulkTrackerManager, BulkTrackerQuerySet


class PostQuerySet(BulkTrackerQuerySet):
    pass


class PostManager(BulkTrackerManager.from_queryset(PostQuerySet)):
    pass


class AuthorQuerySet(BulkTrackerQuerySet):
    pass


class AuthorManager(BulkTrackerManager.from_queryset(PostQuerySet)):
    pass
