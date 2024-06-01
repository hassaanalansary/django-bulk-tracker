from __future__ import annotations

from unittest.mock import patch

from django.test import TransactionTestCase

from bulk_tracker.helper_objects import ModifiedObject, TrackingInfo
from bulk_tracker.signals import post_create_signal
from tests.models import Author, Post


class TestCreateSignal(TransactionTestCase):
    serialized_rollback = True

    def setUp(self):
        self.author_john = Author.objects.create(first_name="John", last_name="Doe")

    def test_model_create_should_emit_post_create_signal(self):
        # Arrange
        signal_called_with = {}

        def post_create_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            signal_called_with["objects"] = objects
            signal_called_with["tracking_info_"] = tracking_info_

        post_create_signal.connect(post_create_receiver, sender=Post)

        # Act
        Post.objects.create(title="Sound of Winter", publish_date="1998-03-08", author=self.author_john)

        # Assert
        self.assertTrue(signal_called_with != {})
        self.assertEqual(1, len(signal_called_with["objects"]))
        self.assertEqual(None, signal_called_with["tracking_info_"])

        modified_objects: list[ModifiedObject[Post]] = signal_called_with["objects"]
        self.assertEqual("Sound of Winter", modified_objects[0].instance.title)
        self.assertEqual("1998-03-08", modified_objects[0].instance.publish_date)
        self.assertEqual(self.author_john, modified_objects[0].instance.author)
        self.assertEqual({}, modified_objects[0].changed_values)

    def test_bulk_create_should_emit_post_create_signal(self):
        # Arrange
        signal_called_with = {}

        def post_create_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            signal_called_with["objects"] = objects
            signal_called_with["tracking_info_"] = tracking_info_

        post_create_signal.connect(post_create_receiver, sender=Post)
        posts = [
            Post(title="Sound of Winter", publish_date="1998-01-08", author=self.author_john),
            Post(title="Sound of Summer", publish_date="1998-06-08", author=self.author_john),
        ]

        # Act
        Post.objects.bulk_create(posts)

        # Assert
        self.assertTrue(signal_called_with != {})
        self.assertEqual(2, len(signal_called_with["objects"]))
        self.assertEqual(None, signal_called_with["tracking_info_"])

        modified_objects: list[ModifiedObject[Post]] = signal_called_with["objects"]

        self.assertEqual("Sound of Winter", modified_objects[0].instance.title)
        self.assertEqual("1998-01-08", modified_objects[0].instance.publish_date)
        self.assertEqual(self.author_john, modified_objects[0].instance.author)
        self.assertEqual({}, modified_objects[0].changed_values)

        self.assertEqual("Sound of Summer", modified_objects[1].instance.title)
        self.assertEqual("1998-06-08", modified_objects[1].instance.publish_date)
        self.assertEqual(self.author_john, modified_objects[1].instance.author)
        self.assertEqual({}, modified_objects[1].changed_values)

    def test_model_save_should_emit_post_create_signal(self):
        # Arrange
        signal_called_with = {}

        def post_create_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            signal_called_with["objects"] = objects
            signal_called_with["tracking_info_"] = tracking_info_

        post_create_signal.connect(post_create_receiver, sender=Post)

        # Act
        Post(title="Sound of Winter", publish_date="1998-01-08", author=self.author_john).save()

        # Assert
        self.assertTrue(signal_called_with != {})
        self.assertEqual(1, len(signal_called_with["objects"]))
        self.assertEqual(None, signal_called_with["tracking_info_"])

        modified_objects: list[ModifiedObject[Post]] = signal_called_with["objects"]

        self.assertEqual("Sound of Winter", modified_objects[0].instance.title)
        self.assertEqual("1998-01-08", modified_objects[0].instance.publish_date)
        self.assertEqual(self.author_john, modified_objects[0].instance.author)
        self.assertEqual({}, modified_objects[0].changed_values)

    @patch("bulk_tracker.signals.post_create_signal.send")
    def test_model_save_should_only_emit_post_create_signal_once(self, mocked_signal):
        # Arrange

        def post_create_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            pass

        post_create_signal.connect(post_create_receiver, sender=Post)

        # Act
        Post(title="Sound of Winter", publish_date="1998-01-08", author=self.author_john).save()

        # Assert
        mocked_signal.assert_called_once()

    @patch("bulk_tracker.signals.post_create_signal.send")
    def test_model_create_should_only_emit_post_create_signal_once(self, mocked_signal):
        # Arrange
        signal_called_with = {}

        def post_create_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            signal_called_with["objects"] = objects
            signal_called_with["tracking_info_"] = tracking_info_

        post_create_signal.connect(post_create_receiver, sender=Post)

        # Act
        Post.objects.create(title="Sound of Winter", publish_date="1998-03-08", author=self.author_john)

        # Assert
        mocked_signal.assert_called_once()

    @patch("bulk_tracker.signals.post_create_signal.send")
    def test_model_bulk_create_should_only_emit_post_create_signal_once(self, mocked_signal):
        # Arrange
        signal_called_with = {}

        def post_create_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            signal_called_with["objects"] = objects
            signal_called_with["tracking_info_"] = tracking_info_

        post_create_signal.connect(post_create_receiver, sender=Post)

        posts = [
            Post(title="Sound of Winter", publish_date="1998-01-08", author=self.author_john),
            Post(title="Sound of Summer", publish_date="1998-06-08", author=self.author_john),
        ]

        # Act
        Post.objects.bulk_create(posts)

        # Assert
        mocked_signal.assert_called_once()

    @patch("bulk_tracker.signals.post_create_signal.send")
    def test_create_signal_should_be_only_emitted_after_transaction_commit(self, mocked_signal):
        # Arrange

        def post_create_receiver(
            sender,
            objects: list[ModifiedObject[Post]],
            tracking_info_: TrackingInfo | None = None,
            **kwargs,
        ):
            pass

        post_create_signal.connect(post_create_receiver, sender=Post)

        posts = [
            Post(title="Sound of Winter", publish_date="1998-01-08", author=self.author_john),
            Post(title="Sound of Summer", publish_date="1998-06-08", author=self.author_john),
        ]

        # Act
        from django.db import transaction

        with transaction.atomic():
            Post.objects.bulk_create(posts)
            mocked_signal.assert_not_called()

            author = Author.objects.create(first_name="Jane", last_name="Doe")
            author.delete()

        # Assert
        self.assertEqual(
            mocked_signal.call_count,
            2,
            msg=f"The signal wasn't called twice. it was called {mocked_signal.call_count}.",
        )
        signal_called_with_first = mocked_signal.call_args_list[0].kwargs
        self.assertEqual(signal_called_with_first["sender"], Post)

        signal_called_with_second = mocked_signal.call_args_list[1].kwargs
        self.assertEqual(signal_called_with_second["sender"], Author)

    @patch("bulk_tracker.signals.post_create_signal.send")
    @patch("bulk_tracker.signals.post_create_signal.send_robust")
    def test_should_use_robust_send_if_is_robust_is_true_in_tracking_info(self, mocked_signal_robust, mocked_signal):
        # Arrange
        posts = [
            Post(title="Sound of Winter", publish_date="1998-01-08", author=self.author_john),
            Post(title="Sound of Summer", publish_date="1998-06-08", author=self.author_john),
        ]

        # Act
        Post.objects.bulk_create(posts, tracking_info_=TrackingInfo(is_robust=True))

        # Assert
        mocked_signal.assert_not_called()
        mocked_signal_robust.assert_called_once()
