from django.apps import AppConfig


class BulkTrackerConfig(AppConfig):
    name = "bulk_tracker"

    def ready(self):
        import bulk_tracker.signals
