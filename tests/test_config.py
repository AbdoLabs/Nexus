"""Basic configuration and portal-state tests."""

import unittest

from nexus.config import settings, validate_settings
from nexus.portal_probe import classify_visible_text


class ConfigTests(unittest.TestCase):
    def test_default_region_is_madrid(self) -> None:
        self.assertEqual(settings.province, "Madrid")

    def test_default_procedure_matches_police_fingerprint_procedure(self) -> None:
        self.assertIn("TOMA DE HUELLA", settings.appointment_procedure)

    def test_default_office_selection_is_any_office(self) -> None:
        self.assertEqual(settings.office_selection, "Cualquier oficina")

    def test_check_interval_is_not_below_five_minutes(self) -> None:
        self.assertGreaterEqual(settings.check_interval_minutes, 5)
        validate_settings()

    def test_portal_url_uses_https(self) -> None:
        self.assertTrue(settings.portal_url.startswith("https://"))


class PortalStateTests(unittest.TestCase):
    def test_loaded_portal_is_not_misreported_as_availability(self) -> None:
        state = classify_visible_text("INTERNET CITA PREVIA")
        self.assertEqual(state, "appointment_portal_loaded")

    def test_no_appointments_message_is_detected(self) -> None:
        state = classify_visible_text(
            "No hay citas disponibles en este momento"
        )
        self.assertEqual(state, "no_appointments_message")

    def test_captcha_requires_manual_intervention(self) -> None:
        state = classify_visible_text("Verifique que es humano")
        self.assertEqual(state, "manual_intervention_required")

    def test_unknown_error_is_not_treated_as_no_availability(self) -> None:
        state = classify_visible_text("Se ha producido un error")
        self.assertEqual(state, "unknown_or_loading")


if __name__ == "__main__":
    unittest.main()
