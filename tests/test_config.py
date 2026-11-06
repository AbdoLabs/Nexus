"""Basic configuration tests."""

import unittest

from nexus.config import settings, validate_settings


class ConfigTests(unittest.TestCase):
    def test_default_region_is_madrid(self) -> None:
        self.assertEqual(settings.province, "Madrid")

    def test_default_procedure_is_fingerprint_collection(self) -> None:
        self.assertEqual(settings.appointment_procedure, "TOMA DE HUELLAS")

    def test_check_interval_is_not_below_five_minutes(self) -> None:
        self.assertGreaterEqual(settings.check_interval_minutes, 5)
        validate_settings()


if __name__ == "__main__":
    unittest.main()
