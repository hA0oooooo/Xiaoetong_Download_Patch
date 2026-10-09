import unittest
from unittest.mock import Mock

from xiaoetong_assistant.native import NativeResource
from xiaoetong_assistant.service import discover_videos


class CatalogTests(unittest.TestCase):
    def test_course_roots_publish_before_slow_resources_and_snapshots_do_not_mutate(self):
        client = Mock()
        client.status.return_value = {"authenticated": True}
        courses = [{"resource_type": 50, "resource_id": "first"}, {"resource_type": 50, "resource_id": "second"}]
        client.course_pages.return_value = [courses]
        snapshots = []
        first = NativeResource("a", "u", "first", "v", "Video", "Course", 3, True, False)
        second = NativeResource("a", "u", "second", "d", "Document", "Course 2", 51, True, False)
        def resources(course):
            self.assertEqual(snapshots[0].course_rows, courses)
            self.assertEqual(snapshots[0].resources, [])
            if course is courses[0]:
                return [first]
            self.assertEqual(snapshots[1].resources, [first])
            return [second]
        client.resources.side_effect = resources
        result = discover_videos(client, on_catalog=snapshots.append)
        self.assertEqual(len(snapshots), 3)
        self.assertEqual(snapshots[1].resources, [first])
        self.assertEqual(snapshots[-1].resources, result.resources)

    def test_incomplete_types_and_denials_remain_visible_and_trials_excluded(self):
        client = Mock()
        client.status.return_value = {"authenticated":True}
        client.course_pages.return_value = [[{"resource_type":50},{"resource_type":4},{"resource_type":50}]]
        def resource(identity, kind, unlocked=True, trial=False):
            return NativeResource("a","u","c",identity,identity,"Course",kind,unlocked,trial)
        client.resources.side_effect = [[resource("video",3),resource("trial",3,trial=True),resource("locked",3,False),resource("doc",51)],PermissionError()]
        result = discover_videos(client)
        self.assertEqual([item.resource_id for item in result.videos],["video"])
        self.assertEqual([item.resource_id for item in result.resources],["video","doc"])
        self.assertEqual(len(result.course_rows),3)

    def test_logged_out_client_does_not_fetch_catalog(self):
        client = Mock()
        client.status.return_value = {"authenticated":False}
        with self.assertRaises(PermissionError):
            discover_videos(client)
        client.course_pages.assert_not_called()
