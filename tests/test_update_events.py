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
            ["Penyakit hewan prioritas", "TADs"],
        )
        self.assertEqual(
            UPDATE_EVENTS.disease_groups_for("Avian influenza"),
            ["Penyakit hewan prioritas", "TADs", "Zoonosis/EID"],
        )
        self.assertEqual(
            UPDATE_EVENTS.disease_groups_for("Nipah"),
            ["Zoonosis/EID"],
        )
        self.assertEqual(
            UPDATE_EVENTS.disease_groups_for("Jembrana Disease"),
            ["Penyakit hewan prioritas"],
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
        self.assertIn("./assets/dashboard.js", index)
        self.assertIn('import(`../data/events.js?ts=${Date.now()}`)', script)
        self.assertNotIn("var EVENTS =", index)

    def test_automatic_refresh_is_scheduled_every_two_days(self):
        root = pathlib.Path(__file__).parents[1]
        workflow = (root / ".github" / "workflows" / "update-data.yml").read_text(encoding="utf-8")
        index = (root / "index.html").read_text(encoding="utf-8")
        self.assertIn('cron: "17 0 */2 * *"', workflow)
        self.assertIn("Pemeriksaan setiap 2 hari", index)
        self.assertNotIn("*/6", workflow)

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

    def test_deduplication_keeps_distinct_locations_from_one_report(self):
        records = [
            UPDATE_EVENTS.base_record(
                id="fmd-jateng",
                disease="Foot-and-Mouth Disease (FMD/PMK)",
                location="Jawa Tengah, Indonesia",
                iso3="IDN",
                source_id="wrlfmd.q1.2026",
                source_url="https://example.test/fmd-q1.pdf",
            ),
            UPDATE_EVENTS.base_record(
                id="fmd-jatim",
                disease="Foot-and-Mouth Disease (FMD/PMK)",
                location="Jawa Timur, Indonesia",
                iso3="IDN",
                source_id="wrlfmd.q1.2026",
                source_url="https://example.test/fmd-q1.pdf",
            ),
        ]
        self.assertEqual(len(UPDATE_EVENTS.deduplicate(records)), 2)


class HealthProfileCaseImportTests(unittest.TestCase):
    def setUp(self):
        records, _sources, report = UPDATE_EVENTS.imported_records()
        self.assertEqual(report["errors"], [])
        self.records = [
            record for record in records
            if record["source_id"] == "kemkes-profile-2024-cases"
        ]

    def records_for(self, disease, year=None):
        records = [record for record in self.records if record["disease"] == disease]
        if year is not None:
            records = [record for record in records if record["published"].startswith(str(year))]
        return records

    def test_profile_import_contains_only_vetted_case_series(self):
        self.assertEqual(len(self.records), 95)
        self.assertTrue(all(record["evidence"] == "confirmed" for record in self.records))
        self.assertTrue(all(record["record_type"] == "event" for record in self.records))
        self.assertEqual(
            {record["disease"] for record in self.records},
            {"Rabies", "Leptospirosis", "COVID-19", "Mpox", "Legionellosis", "Polio cVDPV2"},
        )

    def test_rabies_lyssa_totals_match_appendix(self):
        expected = {2022: 102, 2023: 146, 2024: 122}
        for year, total in expected.items():
            records = self.records_for("Rabies", year)
            self.assertEqual(sum(record["human"]["deaths"] or 0 for record in records), total)
            self.assertTrue(all(record["human"]["confirmed"] is None for record in records))

    def test_leptospirosis_totals_match_appendix(self):
        expected = {2022: (1624, 148), 2023: (2545, 205), 2024: (1506, 121)}
        for year, (cases, deaths) in expected.items():
            records = self.records_for("Leptospirosis", year)
            self.assertEqual(sum(record["human"]["confirmed"] or 0 for record in records), cases)
            self.assertEqual(sum(record["human"]["deaths"] or 0 for record in records), deaths)

    def test_2024_emerging_disease_totals_match_narrative(self):
        expected = {
            "COVID-19": (8624, 93),
            "Mpox": (14, 0),
            "Legionellosis": (16, 0),
            "Polio cVDPV2": (7, 0),
        }
        for disease, (cases, deaths) in expected.items():
            records = self.records_for(disease, 2024)
            self.assertEqual(sum(record["human"]["confirmed"] or 0 for record in records), cases)
            self.assertEqual(sum(record["human"]["deaths"] or 0 for record in records), deaths)


class OfficialNationalSourceTests(unittest.TestCase):
    AWR_PAGE = """
    <html><body>
      <h1>Laporan Perkembangan PMK Bulanan</h1>
      <table>
        <thead><tr><th></th><th>prop</th><th>kab</th><th>desa</th><th>kejadian</th><th>kasus</th></tr></thead>
        <tbody>
          <tr><td>1</td><td>Jawa Tengah</td><td>Klaten, Grobogan</td><td>3</td><td>4</td><td>17</td></tr>
          <tr><td>2</td><td>Jawa Timur</td><td>Blitar</td><td>1</td><td>2</td><td>9</td></tr>
        </tbody>
      </table>
      <table>
        <thead><tr><th></th><th>spec</th><th>kejadian</th><th>kasus</th></tr></thead>
        <tbody><tr><td>1</td><td>SAPI</td><td>6</td><td>26</td></tr></tbody>
      </table>
    </body></html>
    """

    def test_awr_table_is_normalized_as_confirmed_province_events(self):
        rows, species = UPDATE_EVENTS.parse_awr_page(self.AWR_PAGE)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["outbreaks"], 4)
        self.assertEqual(rows[0]["cases"], 17)
        self.assertEqual(species, "Sapi")

        record = UPDATE_EVENTS.awr_record("PMK", "202607", rows[0], species)
        self.assertEqual(record["record_type"], "event")
        self.assertEqual(record["evidence"], "confirmed")
        self.assertEqual(record["location_precision"], "province")
        self.assertEqual(record["animal"]["outbreaks"], 4)
        self.assertEqual(record["lab"]["result"], "Diagnosis definitif (DX)")
        self.assertIn("Penyakit hewan prioritas", record["disease_groups"])
        self.assertIn("TADs", record["disease_groups"])

    def test_awr_cloudflare_failure_keeps_vetted_snapshot(self):
        original_fetch = UPDATE_EVENTS.fetch_text
        UPDATE_EVENTS.fetch_text = lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("blocked"))
        try:
            with self.assertRaises(UPDATE_EVENTS.SourceFetchError) as raised:
                UPDATE_EVENTS.awr_records()
        finally:
            UPDATE_EVENTS.fetch_text = original_fetch
        self.assertEqual(len(raised.exception.fallback_records), 14)
        self.assertTrue(all(record["evidence"] == "confirmed" for record in raised.exception.fallback_records))

    def test_kemkes_profile_is_a_confirmed_report_not_an_event(self):
        page = """
        <a href="/id/profil-kesehatan-indonesia-2024" class="link">
          <h4 class="text-20">Profil Kesehatan Indonesia 2024</h4>
          <time datetime="2025-09-12"><em>12 Sep 2025</em></time>
        </a>
        """
        original_fetch = UPDATE_EVENTS.fetch_text
        UPDATE_EVENTS.fetch_text = lambda *_args, **_kwargs: page
        try:
            records = UPDATE_EVENTS.kemkes_profile_records()
        finally:
            UPDATE_EVENTS.fetch_text = original_fetch
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["record_type"], "report")
        self.assertEqual(records[0]["evidence"], "confirmed")
        self.assertEqual(records[0]["disease_groups"], ["Referensi kesehatan manusia"])

    def test_bps_profile_is_a_confirmed_report_not_an_event(self):
        record = UPDATE_EVENTS.bps_health_profile_records()[0]
        self.assertEqual(record["record_type"], "report")
        self.assertEqual(record["evidence"], "confirmed")
        self.assertIsNone(record["human"]["confirmed"])
        self.assertEqual(record["disease_groups"], ["Referensi kesehatan manusia"])


if __name__ == "__main__":
    unittest.main()
