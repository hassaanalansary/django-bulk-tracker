from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from django.test import TransactionTestCase

from bulk_tracker.helper_objects import ModifiedObject, TrackingInfo
from bulk_tracker.signals import post_update_signal
from tests.models import Author, Post


class TestUpdateSignal(TransactionTestCase):
    def setUp(self):
        self.author_john = Author.objects.create(first_name="John", last_name="Doe")
        self.author_soha = Author.objects.create(first_name="Soha", last_name="Reid")

        Post.objects.create(title="Defend the Lie", publish_date="1999-05-19", author=self.author_john)
        Post.objects.create(title="Cold Vice", publish_date="2001-07-22", author=self.author_john)
        Post.objects.create(title="Sound of Winter", publish_date="2000-09-12", author=self.author_john)

        Post.objects.create(title="Prince's Advent", publish_date="1999-05-19", author=self.author_soha)
        Post.objects.create(title="The Midnight Wolf", publish_date="2002-01-12", author=self.author_soha)

    @staticmethod
    def use_bulk_update():
        posts = Post.objects.filter(publish_date="1999-05-19").order_by("publish_date")
        for post in posts:
            post.publish_date = "1999-12-31"
        signal_called_with: dict = {}
        return posts, signal_called_with

    def test_bulk_update_should_emit_post_update_signal(self):
        # Arrange
        signal_called_with: dict = {}

        def post_update_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            signal_called_with["objects"] = objects
            signal_called_with["tracking_info_"] = tracking_info_

        post_update_signal.connect(post_update_receiver, sender=Post)

        # Act
        posts = Post.objects.filter(publish_date="1999-05-19").order_by("publish_date")
        for post in posts:
            post.publish_date = "1999-12-31"
        Post.objects.bulk_update(posts, fields=["publish_date"])

        # Assert
        self.assertTrue(signal_called_with != {})
        self.assertEqual(2, len(signal_called_with["objects"]))
        self.assertEqual(None, signal_called_with["tracking_info_"])

        ### split into another test case
        modified_objects: list[ModifiedObject[Post]] = signal_called_with["objects"]
        for modified_object in modified_objects:
            self.assertEqual(datetime.strptime("1999-12-31", "%Y-%m-%d").date(), modified_object.instance.publish_date)
            self.assertEqual(
                datetime.strptime("1999-05-19", "%Y-%m-%d").date(), modified_object.changed_values["publish_date"]
            )

    def test_should_raise_attribute_error_when_model_does_not_have_tracker(self):
        # Arrange
        cache_tracker = Post.tracker
        del Post.tracker
        posts = Post.objects.filter(publish_date="1999-05-19").order_by("publish_date")
        for post in posts:
            post.publish_date = "1999-12-31"

        # Act & Assert
        with self.assertRaises(AttributeError) as context:
            posts[0].save()
        self.assertEqual(
            f"Model {Post} doesn't have tracker, please add `tracker = FieldTracker()` to your model",
            context.exception.args[0],
        )

        # Cleanup
        Post.tracker = cache_tracker

    def test_model_save_should_emit_post_update_signal(self):
        # Arrange
        signal_called_with = {}

        def post_update_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            signal_called_with["objects"] = objects
            signal_called_with["tracking_info_"] = tracking_info_

        post_update_signal.connect(post_update_receiver, sender=Post)

        # Act
        post = Post.objects.get(title="Sound of Winter")
        post.title = "Sound of Summer"
        post.save()

        # Assert
        self.assertTrue(signal_called_with != {})
        self.assertEqual(1, len(signal_called_with["objects"]))
        self.assertEqual(None, signal_called_with["tracking_info_"])

        ### split into another test case
        modified_objects: list[ModifiedObject[Post]] = signal_called_with["objects"]
        self.assertEqual("Sound of Summer", modified_objects[0].instance.title)
        self.assertEqual("Sound of Winter", modified_objects[0].changed_values["title"])

    def test_queryset_update_should_emit_post_update_signal(self):
        # Arrange
        signal_called_with = {}

        def post_update_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            signal_called_with["objects"] = objects
            signal_called_with["tracking_info_"] = tracking_info_

        post_update_signal.connect(post_update_receiver, sender=Post)

        # Act
        Post.objects.filter(title="The Midnight Wolf").update(title="The Sunset Wolf")

        # Assert
        self.assertTrue(signal_called_with != {})
        self.assertEqual(1, len(signal_called_with["objects"]))
        self.assertEqual(None, signal_called_with["tracking_info_"])

        modified_objects: list[ModifiedObject[Post]] = signal_called_with["objects"]
        self.assertEqual("The Sunset Wolf", modified_objects[0].instance.title)
        self.assertEqual("The Midnight Wolf", modified_objects[0].changed_values["title"])

    @patch("bulk_tracker.signals.post_update_signal.send")
    def test_update_signal_should_be_only_emitted_after_transaction_commit(self, mocked_signal):
        # Arrange

        def post_update_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            pass

        post_update_signal.connect(post_update_receiver, sender=Post)
        post = Post.objects.create(title="Sound of Summer", publish_date="1998-06-08", author=self.author_john)

        # Act
        from django.db import transaction

        with transaction.atomic():
            post.title = "Sound of Winter"
            Post.objects.bulk_update([post], fields=["title"])
            mocked_signal.assert_not_called()

            self.author_john.first_name = "Johny"
            Author.objects.bulk_update([self.author_john], fields=["first_name"])

        # Assert
        mocked_signal.assert_called_once()
        signal_called_with_first = mocked_signal.call_args_list[0].kwargs
        self.assertEqual(signal_called_with_first["sender"], Post)

    @patch("bulk_tracker.signals.post_update_signal.send")
    @patch("bulk_tracker.signals.post_update_signal.send_robust")
    def test_should_use_robust_send_if_is_robust_is_true_in_tracking_info(self, mocked_signal_robust, mocked_signal):
        # Arrange
        self.author_john.first_name = "Johny"

        # Act
        self.author_john.save(tracking_info_=TrackingInfo(is_robust=True))

        # Assert
        mocked_signal.assert_not_called()
        mocked_signal_robust.assert_called_once()
