import importlib.util
import json
import pathlib
import unittest


SCRIPT = pathlib.Path(__file__).parents[1] / "scripts" / "update_events.py"
SPEC = importlib.util.spec_from_file_location("update_events", SCRIPT)
UPDATE_EVENTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UPDATE_EVENTS)


class GdeltSignalClassificationTests(unittest.TestCase):
    def test_rejects_market_access_false_positive(self):
        title = "Argentina Wins Back EU Market Access for Its Poultry"
        self.assertIsNone(UPDATE_EVENTS.gdelt_signal_disease(title))

    def test_rejects_non_event_even_when_disease_is_named(self):
        titles = [
            "Bird flu vaccine research advances in Australia",
            "Economic impact study of rabies in Indonesia",
            "Rabies prevention campaign launched in India",
            "H5 bird flu in Australia: preparing endangered species for a potential outbreak",
            "Regulatory approval for a Phase II clinical trial during an Ebola outbreak",
        ]
        for title in titles:
            with self.subTest(title=title):
                self.assertIsNone(UPDATE_EVENTS.gdelt_signal_disease(title))

    def test_accepts_clear_event_headlines(self):
        expected = {
            "Argentina confirms avian influenza outbreak in poultry": "Avian influenza",
            "Rabies cases reported in Indonesia": "Rabies",
            "Nipah virus infection detected in India": "Nipah",
            "Kasus flu burung terkonfirmasi di Indonesia": "Avian influenza",
            "Brote de gripe aviar confirmado en Argentina": "Avian influenza",
            "Penguin found dead from bird flu": "Avian influenza",
            "Little penguin dies from bird flu as case numbers grow": "Avian influenza",
            "NSW confirms fifth H5 bird flu case, expands vaccine plans": "Avian influenza",
            "Foot-and-mouth disease outbreak confirmed in Indonesia": "Foot-and-Mouth Disease (FMD/PMK)",
            "African swine fever detected in pigs in Viet Nam": "African Swine Fever (ASF)",
            "Lumpy skin disease cases reported in cattle in Thailand": "Lumpy Skin Disease (LSD)",
        }
        for title, disease in expected.items():
            with self.subTest(title=title):
                self.assertEqual(UPDATE_EVENTS.gdelt_signal_disease(title), disease)

    def test_accepts_concise_disease_and_location_headline(self):
        self.assertEqual(
            UPDATE_EVENTS.gdelt_signal_disease("Anthrax in cattle — Indonesia"),
            "Anthrax",
        )

    def test_does_not_match_mers_inside_farmers(self):
        self.assertIsNone(UPDATE_EVENTS.recognized_disease_from_text("Farmers receive support in Australia"))

    def test_rejects_tad_non_event_headlines(self):
        titles = [
            "Foot-and-mouth disease vaccine research advances in Indonesia",
            "African swine fever market impact study released",
            "Lumpy skin disease preparedness workshop held in Thailand",
            "Bird flu ruled out after hundreds of dead pelicans found in Australia",
            "Bird flu human infection detection methods explored",
        ]
        for title in titles:
            with self.subTest(title=title):
                self.assertIsNone(UPDATE_EVENTS.gdelt_signal_disease(title))

    def test_assigns_nonexclusive_disease_groups(self):
        self.assertEqual(
            UPDATE_EVENTS.disease_groups_for("African Swine Fever (ASF)"),
            ["TADs"],
        )
        self.assertEqual(
            UPDATE_EVENTS.disease_groups_for("Avian influenza"),
            ["TADs", "Zoonosis/EID"],
        )
        self.assertEqual(
            UPDATE_EVENTS.disease_groups_for("Nipah"),
            ["Zoonosis/EID"],
        )

    def test_rescreens_retained_gdelt_records(self):
        records = [
            {
                "title": "Argentina Wins Back EU Market Access for Its Poultry",
                "disease": "Argentina Wins Back EU Market Access for Its Poultry",
                "iso3": "ARG",
            },
            {
                "title": "Rabies cases reported in Indonesia",
                "disease": "Wrong label",
                "iso3": "IDN",
            },
        ]
        screened = UPDATE_EVENTS.sanitize_retained_gdelt(records)
        self.assertEqual(len(screened), 1)
        self.assertEqual(screened[0]["disease"], "Rabies")
        self.assertEqual(screened[0]["record_type"], "event")

    def test_gdelt_importer_only_emits_screened_signals(self):
        payload = {
            "articles": [
                {
                    "title": "Argentina Wins Back EU Market Access for Its Poultry",
                    "url": "https://example.test/trade",
                    "seendate": "20260815T000000Z",
                },
                {
                    "title": "Rabies cases reported in Indonesia",
                    "url": "https://example.test/rabies-event",
                    "seendate": "20260815T010000Z",
                    "domain": "example.test",
                },
            ]
        }
        original_fetch = UPDATE_EVENTS.fetch_text
        UPDATE_EVENTS.fetch_text = lambda *_args, **_kwargs: json.dumps(payload)
        try:
            records = UPDATE_EVENTS.gdelt_records()
        finally:
            UPDATE_EVENTS.fetch_text = original_fetch

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["disease"], "Rabies")
        self.assertEqual(records[0]["record_type"], "event")


class DashboardIntegrationTests(unittest.TestCase):
    def test_dashboard_loads_generated_dataset(self):
        root = pathlib.Path(__file__).parents[1]
        index = (root / "index.html").read_text(encoding="utf-8")
        script = (root / "assets" / "dashboard.js").read_text(encoding="utf-8")
        self.assertIn('src="./assets/dashboard.js"', index)
        self.assertIn('import("../data/events.js")', script)
        self.assertNotIn("var EVENTS =", index)

    def test_new_records_expose_tad_clusters_before_generation(self):
        confirmed = UPDATE_EVENTS.base_record(
            disease="African Swine Fever (ASF)",
            evidence="confirmed",
        )
        rumor = UPDATE_EVENTS.base_record(
            disease="Lumpy Skin Disease (LSD)",
            evidence="rumor",
        )
        self.assertIn("TADs", confirmed["disease_groups"])
        self.assertIn("TADs", rumor["disease_groups"])


if __name__ == "__main__":
    unittest.main()
