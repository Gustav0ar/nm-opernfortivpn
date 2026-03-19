# SPDX-License-Identifier: GPL-2.0-only
"""
Tests for certificate hash parsing from openfortivpn stderr output.
"""
import os
import sys
import re
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'service'))

from nm_openfortivpn_service import CERT_HASH_RE, CERT_HASH_RE2, CERT_HASH_RE3


class TestCertHashParsing(unittest.TestCase):
    """Test extraction of SHA256 cert hashes from openfortivpn stderr."""

    def _find_hash(self, text):
        for pattern in (CERT_HASH_RE, CERT_HASH_RE2, CERT_HASH_RE3):
            m = pattern.search(text)
            if m:
                return m.group(1).strip()
        return None

    def test_standard_error_format(self):
        """Test the typical openfortivpn error output."""
        stderr = (
            "ERROR: Gateway certificate validation failed, and the "
            "certificate digest is not in the local whitelist. If you "
            "trust it, rerun with:\n"
            "    --trusted-cert "
            "a1:b2:c3:d4:e5:f6:a1:b2:c3:d4:e5:f6:a1:b2:c3:d4:"
            "e5:f6:a1:b2:c3:d4:e5:f6:a1:b2:c3:d4:e5:f6:a1:b2\n"
        )
        result = self._find_hash(stderr)
        self.assertIsNotNone(result)
        self.assertIn('a1:b2:c3', result)

    def test_sha256_format(self):
        """Test alternative SHA256: prefix format."""
        stderr = (
            "Certificate:\n"
            "SHA256: "
            "ab:cd:ef:01:23:45:67:89:ab:cd:ef:01:23:45:67:89:"
            "ab:cd:ef:01:23:45:67:89:ab:cd:ef:01:23:45:67:89\n"
        )
        result = self._find_hash(stderr)
        self.assertIsNotNone(result)
        self.assertIn('ab:cd:ef', result)

    def test_no_cert_hash(self):
        """Test that normal output doesn't match."""
        stderr = "INFO: Connected to gateway.\n"
        result = self._find_hash(stderr)
        self.assertIsNone(result)

    def test_digest_is_format(self):
        """Test 'certificate digest is: <hash>' format."""
        stderr = (
            "certificate digest is: "
            "aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99:"
            "aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99\n"
        )
        result = self._find_hash(stderr)
        self.assertIsNotNone(result)

    def test_partial_hash_not_matched(self):
        """Test that short/partial hashes are not matched."""
        stderr = "certificate digest: ab:cd:ef:01\n"
        result = self._find_hash(stderr)
        self.assertIsNone(result)

    def test_multiline_stderr(self):
        """Test extracting from multi-line stderr output."""
        stderr = (
            "WARN: some warning\n"
            "ERROR: peer certificate validation failed\n"
            "certificate digest: "
            "11:22:33:44:55:66:77:88:99:00:aa:bb:cc:dd:ee:ff:"
            "11:22:33:44:55:66:77:88:99:00:aa:bb:cc:dd:ee:ff\n"
            "INFO: disconnecting\n"
        )
        result = self._find_hash(stderr)
        self.assertIsNotNone(result)
        self.assertEqual(len(result.replace(':', '')), 64)


if __name__ == '__main__':
    unittest.main()
