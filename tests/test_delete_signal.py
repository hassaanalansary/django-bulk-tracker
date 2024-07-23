from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from django.db.models.signals import pre_delete
from django.test import TransactionTestCase

from bulk_tracker.helper_objects import ModifiedObject, TrackingInfo
from bulk_tracker.signals import post_delete_signal
from tests.models import Author, Post


class TestDeleteSignal(TransactionTestCase):
    def setUp(self):
        self.author_john = Author.objects.create(first_name="John", last_name="Doe")

    def test_model_delete_should_emit_post_delete_signal(self):
        # Arrange
        signal_called_with = {}

        def post_delete_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            signal_called_with["objects"] = objects
            signal_called_with["tracking_info_"] = tracking_info_

        post_delete_signal.connect(post_delete_receiver, sender=Post)
        post = Post.objects.create(title="Sound of Winter", publish_date="1998-03-08", author=self.author_john)

        # Act
        post.delete()
        # Assert
        self.assertTrue(signal_called_with != {})
        self.assertEqual(1, len(signal_called_with["objects"]))
        self.assertEqual(None, signal_called_with["tracking_info_"])

        modified_objects: list[ModifiedObject[Post]] = signal_called_with["objects"]
        self.assertEqual("Sound of Winter", modified_objects[0].instance.title)
        self.assertEqual("1998-03-08", modified_objects[0].instance.publish_date)
        self.assertEqual(self.author_john, modified_objects[0].instance.author)
        self.assertEqual({}, modified_objects[0].changed_values)

    def test_query_delete_should_emit_post_delete_signal(self):
        # Arrange
        signal_called_with = {}

        def post_delete_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            signal_called_with["objects"] = objects
            signal_called_with["tracking_info_"] = tracking_info_

        post_delete_signal.connect(post_delete_receiver, sender=Post)
        posts = [
            Post(title="Sound of Winter", publish_date="1998-01-08", author=self.author_john),
            Post(title="Sound of Summer", publish_date="1998-06-08", author=self.author_john),
        ]
        Post.objects.bulk_create(posts)

        # Act
        Post.objects.all().order_by("publish_date").delete()

        # Assert
        self.assertTrue(signal_called_with != {})
        self.assertEqual(2, len(signal_called_with["objects"]))
        self.assertEqual(None, signal_called_with["tracking_info_"])

        modified_objects: list[ModifiedObject[Post]] = signal_called_with["objects"]

        self.assertEqual("Sound of Winter", modified_objects[0].instance.title)
        self.assertEqual(datetime.strptime("1998-01-08", "%Y-%m-%d").date(), modified_objects[0].instance.publish_date)
        self.assertEqual(self.author_john, modified_objects[0].instance.author)
        self.assertEqual({}, modified_objects[0].changed_values)

        self.assertEqual("Sound of Summer", modified_objects[1].instance.title)
        self.assertEqual(datetime.strptime("1998-06-08", "%Y-%m-%d").date(), modified_objects[1].instance.publish_date)
        self.assertEqual(self.author_john, modified_objects[1].instance.author)
        self.assertEqual({}, modified_objects[1].changed_values)

    @patch("bulk_tracker.signals.post_delete_signal.send")
    def test_delete_signal_should_be_only_emitted_after_transaction_commit(self, mocked_signal):
        # Arrange

        def post_delete_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            pass

        post_delete_signal.connect(post_delete_receiver, sender=Post)

        # Act
        from django.db import transaction

        with transaction.atomic():
            post = Post.objects.create(title="Sound of Winter", publish_date="1998-01-08", author=self.author_john)
            post.delete()
            mocked_signal.assert_not_called()

            Author.objects.create(first_name="Jane", last_name="Doe")

        # Assert
        mocked_signal.assert_called_once()
        signal_called_with_first = mocked_signal.call_args_list[0].kwargs
        self.assertEqual(signal_called_with_first["sender"], Post)

    @patch("bulk_tracker.signals.post_delete_signal.send")
    @patch("bulk_tracker.signals.post_delete_signal.send_robust")
    def test_should_use_robust_send_if_is_robust_is_true_in_tracking_info(self, mocked_signal_robust, mocked_signal):
        # Arrange

        # Act
        self.author_john.delete(tracking_info_=TrackingInfo(is_robust=True))

        # Assert
        mocked_signal.assert_not_called()
        mocked_signal_robust.assert_called_once()

    def test_queryset_delete_should_send_post_delete_signal_for_foreign_keys_with_cascade_if_fast_delete_is_used(self):
        # Arrange
        signal_called_with = {}

        def post_delete_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            signal_called_with["sender"] = sender
            signal_called_with["objects"] = objects
            signal_called_with["tracking_info_"] = tracking_info_

        post_delete_signal.connect(post_delete_receiver, sender=Post)
        post = Post.objects.create(title="Sound of Winter", publish_date="1998-01-08", author=self.author_john)

        # Act
        Author.objects.filter(id=self.author_john.id).delete()

        # Assert
        modified_objects: list[ModifiedObject[Post]] = signal_called_with["objects"]
        self.assertEqual(signal_called_with["sender"], Post)
        self.assertEqual(post.id, modified_objects[0].instance.id)
        self.assertEqual("Sound of Winter", modified_objects[0].instance.title)
        self.assertEqual(datetime.strptime("1998-01-08", "%Y-%m-%d").date(), modified_objects[0].instance.publish_date)
        self.assertEqual(self.author_john.id, modified_objects[0].instance.author_id)

    def test_queryset_delete_should_send_post_delete_signal_for_foreign_keys_with_cascade_if_fast_delete_is_not_used(
        self,
    ):
        # Arrange
        signal_called_with = {}

        def pre_delete_receiver(**kwargs):
            pass

        def post_delete_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            signal_called_with["sender"] = sender
            signal_called_with["objects"] = objects
            signal_called_with["tracking_info_"] = tracking_info_

        pre_delete.connect(pre_delete_receiver, sender=Post)  # disable fast delete in `Collector`
        post_delete_signal.connect(post_delete_receiver, sender=Post)
        post = Post.objects.create(title="Sound of Winter", publish_date="1998-01-08", author=self.author_john)

        # Act
        Author.objects.filter(id=self.author_john.id).delete()

        # Assert
        modified_objects: list[ModifiedObject[Post]] = signal_called_with["objects"]
        self.assertEqual(signal_called_with["sender"], Post)
        self.assertEqual(post.id, modified_objects[0].instance.id)
        self.assertEqual("Sound of Winter", modified_objects[0].instance.title)
        self.assertEqual(datetime.strptime("1998-01-08", "%Y-%m-%d").date(), modified_objects[0].instance.publish_date)
        self.assertEqual(self.author_john.id, modified_objects[0].instance.author_id)

    def test_model_delete_should_send_post_delete_signal_for_foreign_keys_with_cascade_if_fast_delete_is_used(self):
        # Arrange
        signal_called_with = {}

        def post_delete_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            signal_called_with.setdefault("times_called", 0)
            signal_called_with["times_called"] += 1
            signal_called_with["sender"] = sender
            signal_called_with["objects"] = objects
            signal_called_with["tracking_info_"] = tracking_info_

        post_delete_signal.connect(post_delete_receiver, sender=Post)
        post = Post.objects.create(title="Sound of Winter", publish_date="1998-01-08", author=self.author_john)
        author_id = self.author_john.id

        # Act
        self.author_john.delete(tracking_info_=TrackingInfo(comment="This is a comment"))

        # Assert
        modified_objects: list[ModifiedObject[Post]] = signal_called_with["objects"]
        self.assertEqual(signal_called_with["sender"], Post)
        self.assertEqual(post.id, modified_objects[0].instance.id)
        self.assertEqual("Sound of Winter", modified_objects[0].instance.title)
        self.assertEqual(datetime.strptime("1998-01-08", "%Y-%m-%d").date(), modified_objects[0].instance.publish_date)
        self.assertEqual(author_id, modified_objects[0].instance.author_id)
        self.assertEqual("This is a comment", signal_called_with["tracking_info_"].comment)
        self.assertEqual(1, signal_called_with["times_called"])

    def test_model_delete_should_send_post_delete_signal_for_foreign_keys_with_cascade_if_fast_delete_is_not_used(self):
        # Arrange
        signal_called_with = {}

        def pre_delete_receiver(**kwargs):
            pass

        def post_delete_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            signal_called_with.setdefault("times_called", 0)
            signal_called_with["times_called"] += 1
            signal_called_with["sender"] = sender
            signal_called_with["objects"] = objects
            signal_called_with["tracking_info_"] = tracking_info_

        pre_delete.connect(pre_delete_receiver, sender=Post)  # disable fast delete in `Collector`
        post_delete_signal.connect(post_delete_receiver, sender=Post)
        post = Post.objects.create(title="Sound of Winter", publish_date="1998-01-08", author=self.author_john)
        author_id = self.author_john.id

        # Act
        self.author_john.delete(tracking_info_=TrackingInfo(comment="This is a comment"))

        # Assert
        modified_objects: list[ModifiedObject[Post]] = signal_called_with["objects"]
        self.assertEqual(signal_called_with["sender"], Post)
        self.assertEqual(post.id, modified_objects[0].instance.id)
        self.assertEqual("Sound of Winter", modified_objects[0].instance.title)
        self.assertEqual(datetime.strptime("1998-01-08", "%Y-%m-%d").date(), modified_objects[0].instance.publish_date)
        self.assertEqual(author_id, modified_objects[0].instance.author_id)
        self.assertEqual("This is a comment", signal_called_with["tracking_info_"].comment)
        self.assertEqual(1, signal_called_with["times_called"])
