import unittest
from unittest.mock import patch
from xiaoetong_assistant.network import make_session


class NetworkTests(unittest.TestCase):
    def test_environment_proxies_do_not_affect_course_connections(self):
        with patch.dict("os.environ", {"HTTP_PROXY": "http://127.0.0.1:38080", "HTTPS_PROXY": "http://127.0.0.1:38080", "ALL_PROXY": "http://127.0.0.1:38081"}):
            with make_session() as session:
                settings = session.merge_environment_settings("https://study.xiaoe-tech.com", {}, False, True, None)
                self.assertFalse(settings["proxies"])
