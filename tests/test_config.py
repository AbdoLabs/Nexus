"""Configuration and portal-state tests."""

import unittest

from nexus.config import settings, validate_settings
from nexus.portal_probe import classify_portal_result, extract_office_options


class ConfigTests(unittest.TestCase):
    def test_default_region_is_madrid(self) -> None:
        self.assertEqual(settings.province, "Madrid")

    def test_default_office_mode_is_all_offices(self) -> None:
        self.assertEqual(settings.office_selection, "Cualquier oficina")

    def test_default_procedure_is_fingerprint_collection(self) -> None:
        self.assertIn("TOMA DE HUELLA", settings.appointment_procedure)

    def test_check_interval_is_not_below_five_minutes(self) -> None:
        self.assertGreaterEqual(settings.check_interval_minutes, 5)
        validate_settings()

    def test_portal_url_uses_https(self) -> None:
        self.assertTrue(settings.portal_url.startswith("https://"))


class PortalStateTests(unittest.TestCase):
    def test_office_selector_is_the_positive_availability_signal(self) -> None:
        frames = [{
            "selects": [{
                "visible": True,
                "disabled": False,
                "label": "Oficina",
                "id": "oficina",
                "name": "oficina",
                "options": [
                    {"value": "0", "label": "Seleccionar ...", "disabled": False},
                    {"value": "2801", "label": "Comisaría Centro", "disabled": False},
                    {"value": "2802", "label": "Comisaría Norte", "disabled": False},
                ],
            }]
        }]
        self.assertEqual(
            extract_office_options(frames),
            ["Comisaría Centro", "Comisaría Norte"],
        )
        self.assertEqual(
            classify_portal_result(frames, "Seleccione la oficina"),
            "office_selection_available",
        )

    def test_cualquier_oficina_is_not_counted_as_a_specific_office(self) -> None:
        frames = [{
            "selects": [{
                "visible": True,
                "label": "Oficina",
                "id": "oficina",
                "name": "oficina",
                "options": [
                    {"value": "0", "label": "Seleccionar ...", "disabled": False},
                    {"value": "1", "label": "Cualquier oficina", "disabled": False},
                ],
            }]
        }]
        self.assertEqual(extract_office_options(frames), [])

    def test_explicit_no_appointments_message_wins(self) -> None:
        self.assertEqual(
            classify_portal_result([], "No hay citas disponibles en este momento"),
            "no_appointments_message",
        )

    def test_captcha_requires_manual_intervention(self) -> None:
        self.assertEqual(
            classify_portal_result([], "Verifique que es humano"),
            "manual_intervention_required",
        )

    def test_unknown_error_is_not_treated_as_no_availability(self) -> None:
        self.assertEqual(
            classify_portal_result([], "Se ha producido un error"),
            "unknown_or_loading",
        )


if __name__ == "__main__":
    unittest.main()
