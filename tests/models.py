from django.db import models
from model_utils import FieldTracker

from bulk_tracker.models import BulkTrackerModel


class Author(BulkTrackerModel):
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)

    tracker = FieldTracker()


class Post(BulkTrackerModel):
    title = models.CharField(max_length=255)
    publish_date = models.DateField()
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="posts")

    tracker = FieldTracker()
