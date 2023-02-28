from django.db import models
from model_utils import FieldTracker

from bulk_tracker.models import BulkTrackerModel
from tests.managers import AuthorManager, PostManager, PostQuerySet


class Author(BulkTrackerModel):
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)

    tracker = FieldTracker()
    objects = AuthorManager()


class Post(BulkTrackerModel):
    title = models.CharField(max_length=255)
    publish_date = models.DateField()
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="posts")

    tracker = FieldTracker()
    objects = PostQuerySet.as_manager()
