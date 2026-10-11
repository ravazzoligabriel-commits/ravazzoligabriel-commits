import urllib.error
import unittest
from unittest.mock import patch, MagicMock
from community.private_storage import verify_private


class PrivateStorageTests(unittest.TestCase):
    def test_public_repository_is_rejected(self):
        with patch('urllib.request.urlopen', return_value=MagicMock()):
            with self.assertRaises(ValueError):
                verify_private('owner/storage')

    def test_ssh_repository_must_be_hidden_from_public_api(self):
        error = urllib.error.HTTPError('url', 404, 'Not Found', {}, None)
        with patch('urllib.request.urlopen', side_effect=error):
            verify_private('owner/storage')

    def test_api_outage_never_counts_as_private(self):
        error = urllib.error.HTTPError('url', 503, 'Unavailable', {}, None)
        with patch('urllib.request.urlopen', side_effect=error):
            with self.assertRaises(urllib.error.HTTPError):
                verify_private('owner/storage')
