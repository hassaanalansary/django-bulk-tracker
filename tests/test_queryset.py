from __future__ import annotations

from datetime import datetime

from django.test import TestCase

from bulk_tracker.helper_objects import ModifiedObject, TrackingInfo
from bulk_tracker.signals import post_update_signal
from tests.models import Author, Post


class TestBulkUpdate(TestCase):
    @classmethod
    def setUpTestData(cls):
        author_john = Author.objects.create(first_name="John", last_name="Doe")
        Post.objects.create(title="Defend the Lie", publish_date="1999-05-19", author=author_john)
        Post.objects.create(title="Cold Vice", publish_date="2001-07-22", author=author_john)
        Post.objects.create(title="Defend the Lie", publish_date="2000-09-12", author=author_john)

        author_soha = Author.objects.create(first_name="Soha", last_name="Reid")
        Post.objects.create(title="Prince's Advent", publish_date="1996-07-09", author=author_soha)
        Post.objects.create(title="The Midnight Wolf", publish_date="2002-01-12", author=author_soha)

        author_bert = Author.objects.create(first_name="Bert", last_name="Butler")
        Post.objects.create(title="Sharing Season", publish_date="2001-08-20", author=author_bert)
        Post.objects.create(title="Before Us", publish_date="1999-11-01", author=author_bert)

    @staticmethod
    def use_bulk_update():
        posts = Post.objects.filter(publish_date__year="1999").order_by("publish_date")
        for post in posts:
            post.publish_date = "1999-12-31"
        signal_called_with: dict = {}
        return posts, signal_called_with

    def test_bulk_update_should_emit_post_update_signal(self):
        posts, signal_called_with = self.use_bulk_update()

        def post_update_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            signal_called_with["objects"] = objects
            signal_called_with["tracking_info_"] = tracking_info_

        post_update_signal.connect(post_update_receiver, sender=Post)
        Post.objects.bulk_update(posts, fields=["publish_date"])
        self.assertTrue(signal_called_with != {})
        self.assertEqual(2, len(signal_called_with["objects"]))
        self.assertEqual(None, signal_called_with["tracking_info_"])

        ### split into another test case
        modified_objects: list[ModifiedObject[Post]] = signal_called_with["objects"]
        for modified_object in modified_objects:
            self.assertEqual(datetime.strptime("1999-12-31", "%Y-%m-%d").date(), modified_object.obj.publish_date)

    def test_should_raise_attribute_error_when_model_does_not_have_tracker(self):
        del Post.tracker
        posts, signal_called_with = self.use_bulk_update()
        with self.assertRaises(AttributeError) as context:
            posts[0].save()
        self.assertEqual(
            f"Model {Post} doesn't have tracker, please add `tracker = FieldTracker()` to your model",
            context.exception.args[0],
        )
