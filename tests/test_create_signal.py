from __future__ import annotations

from django.test import TestCase

from bulk_tracker.helper_objects import ModifiedObject, TrackingInfo
from bulk_tracker.signals import post_create_signal
from tests.models import Author, Post


class TestCreateSignal(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author_john = Author.objects.create(first_name="John", last_name="Doe")

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
