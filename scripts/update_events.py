#!/usr/bin/env python3
"""Build normalized near-real-time surveillance data for the static dashboard.

Only public machine-readable or public report pages are ingested. Sources that
require credentials or a licence are listed in the source registry but are not
scraped. Disease groups are non-exclusive so a zoonosis may also appear under
TADs when epidemiologically appropriate.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import csv
import calendar
import posixpath
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
EVENTS_PATH = DATA_DIR / "events.json"
STATUS_PATH = DATA_DIR / "source-status.json"
JS_PATH = DATA_DIR / "events.js"
IMPORT_DIR = DATA_DIR / "import"
IMPORT_VALIDATION_PATH = DATA_DIR / "import-validation.json"
SEED_DIR = DATA_DIR / "seed"
USER_AGENT = (
    "ZoonosisDashboard/1.0 "
    "(+https://github.com/ajatikusumah/"
    "Zoonosis-and-Emerging-Infectious-Diseases-Dashboard)"
)
NOW = datetime.now(timezone.utc)
MAX_AGE_DAYS = 365


IMPORT_FIELDS = [
    "publish", "event_id", "record_type", "evidence", "disease", "title", "location", "iso3",
    "latitude", "longitude", "location_precision", "published", "updated", "response",
    "human_suspected", "human_confirmed", "human_deaths", "animal_outbreaks", "animal_sick",
    "animal_deaths", "animal_culled", "species", "source_id", "source_name", "source_level",
    "source_kind", "access_level", "source_url", "verification", "summary",
]
ALLOWED_RECORD_TYPES = {"event", "report"}
ALLOWED_EVIDENCE = {"confirmed", "rumor"}
ALLOWED_ACCESS_LEVELS = {"public", "restricted", "licensed", "institutional", "internal"}
ALLOWED_SOURCE_LEVELS = {"Lokal", "Nasional", "Regional", "Global"}


COUNTRIES = {
    "IDN": ("Indonesia", -2.55, 118.01, ["indonesia"]),
    "BRN": ("Brunei Darussalam", 4.54, 114.73, ["brunei", "brunei darussalam"]),
    "KHM": ("Cambodia", 12.57, 104.99, ["cambodia", "kamboja"]),
    "LAO": ("Lao PDR", 18.20, 103.90, ["lao pdr", "laos"]),
    "MYS": ("Malaysia", 4.21, 101.98, ["malaysia"]),
    "MMR": ("Myanmar", 21.92, 95.96, ["myanmar", "burma"]),
    "PHL": ("Philippines", 12.88, 121.77, ["philippines", "filipina"]),
    "SGP": ("Singapore", 1.35, 103.82, ["singapore", "singapura"]),
    "THA": ("Thailand", 15.87, 100.99, ["thailand"]),
    "TLS": ("Timor-Leste", -8.87, 125.73, ["timor-leste", "timor leste"]),
    "VNM": ("Viet Nam", 14.06, 108.28, ["viet nam", "vietnam"]),
    "AUS": ("Australia", -25.27, 133.78, ["australia", "tasmania", "tassie"]),
    "BGD": ("Bangladesh", 23.68, 90.36, ["bangladesh"]),
    "BTN": ("Bhutan", 27.51, 90.43, ["bhutan"]),
    "CHN": ("China", 35.86, 104.20, ["china", "cina", "tiongkok"]),
    "FJI": ("Fiji", -17.71, 178.07, ["fiji"]),
    "IND": ("India", 20.59, 78.96, ["india", "kerala"]),
    "JPN": ("Japan", 36.20, 138.25, ["japan", "jepang"]),
    "KOR": ("Republic of Korea", 35.91, 127.77, ["republic of korea", "south korea", "korea selatan"]),
    "MDV": ("Maldives", 3.20, 73.22, ["maldives", "maladewa"]),
    "NPL": ("Nepal", 28.39, 84.12, ["nepal"]),
    "NZL": ("New Zealand", -40.90, 174.89, ["new zealand", "selandia baru"]),
    "PAK": ("Pakistan", 30.38, 69.35, ["pakistan"]),
    "PNG": ("Papua New Guinea", -6.31, 143.96, ["papua new guinea"]),
    "LKA": ("Sri Lanka", 7.87, 80.77, ["sri lanka"]),
    "TWN": ("Taiwan", 23.70, 120.96, ["taiwan"]),
    "ARG": ("Argentina", -38.42, -63.62, ["argentina"]),
    "BRA": ("Brazil", -14.24, -51.93, ["brazil", "brasil"]),
    "CAN": ("Canada", 56.13, -106.35, ["canada", "kanada"]),
    "CHL": ("Chile", -35.68, -71.54, ["chile"]),
    "COL": ("Colombia", 4.57, -74.30, ["colombia"]),
    "CUB": ("Cuba", 21.52, -77.78, ["cuba", "kuba"]),
    "DOM": ("Dominican Republic", 18.74, -70.16, ["dominican republic", "republik dominika"]),
    "ECU": ("Ecuador", -1.83, -78.18, ["ecuador"]),
    "HTI": ("Haiti", 18.97, -72.29, ["haiti"]),
    "MEX": ("Mexico", 23.63, -102.55, ["mexico", "meksiko"]),
    "PER": ("Peru", -9.19, -75.02, ["peru"]),
    "USA": ("United States", 37.09, -95.71, ["united states", "united states of america", "amerika serikat", "u.s.", "usa"]),
    "VEN": ("Venezuela", 6.42, -66.59, ["venezuela"]),
    "COD": ("Democratic Republic of the Congo", -4.04, 21.76, ["democratic republic of the congo", "dr congo", "drc", "rd kongo"]),
    "ETH": ("Ethiopia", 9.15, 40.49, ["ethiopia", "ethiopia"]),
    "GHA": ("Ghana", 7.95, -1.02, ["ghana"]),
    "KEN": ("Kenya", -0.02, 37.91, ["kenya"]),
    "MLI": ("Mali", 17.57, -4.00, ["mali"]),
    "NAM": ("Namibia", -22.96, 18.49, ["namibia"]),
    "NGA": ("Nigeria", 9.08, 8.68, ["nigeria"]),
    "RWA": ("Rwanda", -1.94, 29.87, ["rwanda"]),
    "SDN": ("Sudan", 12.86, 30.22, ["sudan"]),
    "SSD": ("South Sudan", 6.88, 31.31, ["south sudan"]),
    "TZA": ("United Republic of Tanzania", -6.37, 34.89, ["tanzania"]),
    "UGA": ("Uganda", 1.37, 32.29, ["uganda"]),
    "ZAF": ("South Africa", -30.56, 22.94, ["south africa", "afrika selatan"]),
    "AFG": ("Afghanistan", 33.94, 67.71, ["afghanistan"]),
    "IRQ": ("Iraq", 33.22, 43.68, ["iraq"]),
    "JOR": ("Jordan", 30.59, 36.24, ["jordan"]),
    "OMN": ("Oman", 21.47, 55.98, ["oman"]),
    "QAT": ("Qatar", 25.35, 51.18, ["qatar"]),
    "SAU": ("Saudi Arabia", 23.89, 45.08, ["saudi arabia", "arab saudi"]),
    "ARE": ("United Arab Emirates", 23.42, 53.85, ["united arab emirates", "uni emirat arab", "uae"]),
    "CHE": ("Switzerland", 46.82, 8.23, ["switzerland", "swiss"]),
    "DEU": ("Germany", 51.17, 10.45, ["germany", "jerman"]),
    "ESP": ("Spain", 40.46, -3.75, ["spain", "spanyol"]),
    "FRA": ("France", 46.23, 2.21, ["france", "perancis"]),
    "GBR": ("United Kingdom", 55.38, -3.44, ["united kingdom", "inggris", "britain", "uk"]),
    "ITA": ("Italy", 41.87, 12.57, ["italy", "italia"]),
    "NLD": ("Netherlands", 52.13, 5.29, ["netherlands", "belanda"]),
    "SWE": ("Sweden", 60.13, 18.64, ["sweden", "swedia"]),
    "WSM": ("Samoa", -13.76, -172.10, ["samoa"]),
    "TON": ("Tonga", -21.18, -175.20, ["tonga"]),
    "PLW": ("Palau", 7.51, 134.58, ["palau"]),
}


DISEASES = [
    ("Avian influenza", [
        "avian influenza", "avian flu", "bird flu", "h5n1", "h5n5", "h5n6", "h9n2",
        "flu burung", "gripe aviar", "influenza aviar", "grippe aviaire", "influenza aviária",
    ]),
    ("Foot-and-Mouth Disease (FMD/PMK)", [
        "foot-and-mouth disease", "foot and mouth disease", "penyakit mulut dan kuku",
    ]),
    ("African Swine Fever (ASF)", ["african swine fever", "demam babi afrika"]),
    ("Lumpy Skin Disease (LSD)", ["lumpy skin disease", "penyakit kulit berbenjol"]),
    ("Classical Swine Fever (CSF)", ["classical swine fever", "hog cholera"]),
    ("Peste des Petits Ruminants (PPR)", ["peste des petits ruminants"]),
    ("Contagious Bovine Pleuropneumonia (CBPP)", ["contagious bovine pleuropneumonia"]),
    ("African Horse Sickness (AHS)", ["african horse sickness"]),
    ("Sheep Pox and Goat Pox", ["sheep pox", "sheeppox", "goat pox", "goatpox"]),
    ("Newcastle Disease", ["newcastle disease"]),
    ("Rinderpest", ["rinderpest"]),
    ("Anthrax", ["anthrax", "antraks"]),
    ("Rabies", ["rabies", "rabia", "raiva"]),
    ("Leptospirosis", ["leptospirosis"]),
    ("Nipah", ["nipah"]),
    ("Hantavirus", ["hantavirus", "hanta"]),
    ("Ebola virus disease", ["ebola", "bundibugyo"]),
    ("Marburg virus disease", ["marburg"]),
    ("Mpox", ["mpox", "monkeypox"]),
    ("MERS", ["mers", "middle east respiratory syndrome"]),
    ("West Nile fever", ["west nile"]),
    ("Crimean-Congo haemorrhagic fever", ["crimean-congo", "cchf"]),
    ("Rift Valley fever", ["rift valley fever"]),
    ("Brucellosis", ["brucellosis", "brucelosis"]),
    ("Septicaemia Epizootica (SE)", ["septicaemia epizootica", "septicemia epizootica"]),
    ("Jembrana Disease", ["jembrana disease", "penyakit jembrana"]),
    ("Surra (Trypanosomiasis)", ["surra", "trypanosomiasis"]),
    ("Lassa fever", ["lassa fever"]),
    ("Yellow fever", ["yellow fever", "demam kuning"]),
    ("Dengue", ["dengue"]),
    ("Cholera", ["cholera", "kolera"]),
    ("Meningococcal disease", ["meningococcal", "meningokokus"]),
]


# TADs can overlap with zoonotic/EID surveillance (for example avian influenza,
# Rift Valley fever, anthrax, rabies, and brucellosis). Purely animal TADs are
# kept out of human-case totals but remain available through the TADs filter.
TAD_DISEASES = {
    "Foot-and-Mouth Disease (FMD/PMK)",
    "African Swine Fever (ASF)",
    "Lumpy Skin Disease (LSD)",
    "Classical Swine Fever (CSF)",
    "Peste des Petits Ruminants (PPR)",
    "Contagious Bovine Pleuropneumonia (CBPP)",
    "African Horse Sickness (AHS)",
    "Sheep Pox and Goat Pox",
    "Newcastle Disease",
    "Rinderpest",
    "Avian influenza",
    "Rift Valley fever",
    "Anthrax",
    "Rabies",
    "Brucellosis",
}
PURE_ANIMAL_TADS = {
    "Foot-and-Mouth Disease (FMD/PMK)",
    "African Swine Fever (ASF)",
    "Lumpy Skin Disease (LSD)",
    "Classical Swine Fever (CSF)",
    "Peste des Petits Ruminants (PPR)",
    "Contagious Bovine Pleuropneumonia (CBPP)",
    "African Horse Sickness (AHS)",
    "Sheep Pox and Goat Pox",
    "Newcastle Disease",
    "Rinderpest",
}

ANIMAL_PRIORITY_DISEASES = {
    "Foot-and-Mouth Disease (FMD/PMK)",
    "Lumpy Skin Disease (LSD)",
    "Rabies",
    "Avian influenza",
    "Anthrax",
    "Septicaemia Epizootica (SE)",
    "Jembrana Disease",
    "African Swine Fever (ASF)",
    "Classical Swine Fever (CSF)",
    "Brucellosis",
    "Surra (Trypanosomiasis)",
}

PURE_ANIMAL_DISEASES = PURE_ANIMAL_TADS | {
    "Septicaemia Epizootica (SE)",
    "Jembrana Disease",
    "Surra (Trypanosomiasis)",
}


# GDELT searches full article text, so a query hit does not prove that the headline
# describes a disease event. These terms provide a deliberately high-precision
# event screen before a media item can enter the dashboard.
GDELT_EVENT_TERMS = (
    "outbreak", "case", "cases", "confirm", "confirms", "confirmed", "confirmation", "detected", "detection",
    "positive", "infection", "infections", "infected", "death", "deaths", "dead", "died", "dies",
    "fatal", "mortality",
    "suspect", "suspected", "sick", "illness", "culled", "culling", "quarantine",
    "wabah", "kasus", "terkonfirmasi", "terdeteksi", "positif", "infeksi", "terinfeksi",
    "kematian", "meninggal", "suspek", "sakit", "dimusnahkan", "karantina",
    "brote", "caso", "casos", "confirmado", "confirmada", "detectado", "detectada",
    "infectado", "infectada", "muertes", "muerte", "sospechoso", "sospechosa",
    "surto", "confirmada", "detectada", "infectada", "mortes", "suspeito", "suspeita",
    "épidémie", "foyer", "confirmé", "confirmée", "détecté", "détectée", "infecté",
    "infectée", "décès", "suspecté", "suspectée",
)

# These terms override a non-event context because they directly describe an
# epidemiological occurrence, e.g. "outbreak prompts vaccination".
GDELT_HARD_EVENT_TERMS = (
    "outbreak", "confirm", "confirms", "confirmed", "detected", "positive", "infection", "infections", "infected",
    "death", "deaths", "dead", "died", "dies", "fatal", "mortality", "culled", "culling",
    "wabah", "terkonfirmasi", "terdeteksi", "positif", "infeksi", "terinfeksi", "kematian",
    "meninggal", "dimusnahkan", "brote", "confirmado", "confirmada", "detectado", "detectada",
    "infectado", "infectada", "muertes", "muerte", "surto", "épidémie", "foyer", "confirmé",
    "confirmée", "détecté", "détectée", "infecté", "infectée", "décès",
)

GDELT_NON_EVENT_TERMS = (
    "market access", "market", "export", "exports", "import", "imports", "trade", "tariff",
    "earnings", "stock", "shares", "investor", "sales", "price", "economic impact",
    "vaccine", "vaccination", "vaccinate", "immunization", "immunisation",
    "research", "researchers", "study", "review", "method", "methods", "book", "conference", "seminar", "training",
    "guideline", "guidance", "policy", "preparedness", "readiness", "simulation", "exercise",
    "awareness", "campaign", "prevention", "prevent", "anniversary", "history", "evolving",
    "akses pasar", "ekspor", "impor", "perdagangan", "harga", "penelitian", "kajian",
    "pelatihan", "pedoman", "kebijakan", "kesiapsiagaan", "simulasi", "kampanye", "pencegahan",
)

# These phrases indicate that the headline is about preparedness, commentary,
# or a product/research announcement even when it mentions an existing outbreak.
GDELT_ALWAYS_NON_EVENT_TERMS = (
    "potential outbreak", "possible outbreak", "free status", "declared free", "at risk",
    "ruled out", "rule out", "tested negative", "tests negative", "negative for", "no evidence of",
    "detection method", "detection methods", "diagnostic method", "diagnostic methods",
    "clinical trial", "regulatory approval", "phase i trial", "phase ii trial", "phase iii trial",
    "everything you need to know", "what you need to know", "explainer",
    "potensi wabah", "kemungkinan wabah", "uji klinis", "persetujuan regulatori",
)


SOURCE_REGISTRY = [
    {
        "id": "kemkes-infem",
        "name": "Kemenkes RI • Infeksi Emerging",
        "level": "Nasional",
        "kind": "Laporan resmi",
        "access_level": "public",
        "url": "https://infeksiemerging.kemkes.go.id/",
        "default_status": "scheduled",
        "note": "Weekly update dan spot report publik; diperlakukan sebagai publikasi, bukan angka kasus terstruktur.",
    },
    {
        "id": "kemkes-profile",
        "name": "Kemenkes RI • Profil Kesehatan Indonesia",
        "level": "Nasional",
        "kind": "Statistik kesehatan manusia",
        "access_level": "public",
        "url": "https://www.kemkes.go.id/id/category/profil-kesehatan",
        "default_status": "scheduled",
        "note": "Publikasi tahunan resmi; ditampilkan sebagai referensi dan tidak menaikkan KPI kejadian/kasus.",
    },
    {
        "id": "awr-sitreps",
        "name": "Ditjen PKH • AWR SITREPS/iSIKHNAS",
        "level": "Nasional",
        "kind": "Kejadian penyakit hewan terkonfirmasi",
        "access_level": "public",
        "url": "https://awr.ditjenpkh.pertanian.go.id/sitreps/",
        "default_status": "scheduled",
        "note": "SITREPS bulanan 11 penyakit prioritas; kejadian telah dikonfirmasi sebagai diagnosis definitif (DX). Snapshot resmi terakhir dipertahankan bila proteksi situs menolak klien otomatis.",
    },
    {
        "id": "bps-health-profile",
        "name": "BPS • Profil Statistik Kesehatan 2025",
        "level": "Nasional",
        "kind": "Statistik kesehatan manusia",
        "access_level": "public",
        "url": "https://www.bps.go.id/id/publication/2025/12/12/7d17daec8d62c852fc354945/profil-statistik-kesehatan-2025.html",
        "default_status": "scheduled",
        "note": "Publikasi tahunan berbasis Susenas Maret 2025; referensi statistik, bukan feed kejadian wabah.",
    },
    {
        "id": "size-nasional",
        "name": "SIZE Nasional",
        "level": "Nasional",
        "kind": "Sistem lintas sektor",
        "access_level": "restricted",
        "url": "https://www.fao.org/indonesia/news/detail/SIZE-Nasional-Harnessing-Technology-for-Effective-Control-of-Infectious-Diseases/en",
        "default_status": "restricted",
        "note": "Akses data operasional memerlukan kemitraan/otorisasi.",
    },
    {
        "id": "skdr",
        "name": "SKDR Kemenkes",
        "level": "Nasional",
        "kind": "Surveilans indikator/event",
        "access_level": "restricted",
        "url": "https://skdr.surveilans.org/",
        "default_status": "restricted",
        "note": "Data rinci memerlukan akun berwenang.",
    },
    {
        "id": "isikhnas",
        "name": "iSIKHNAS",
        "level": "Nasional",
        "kind": "Kesehatan hewan",
        "access_level": "restricted",
        "url": "https://isikhnas.pertanian.go.id/",
        "default_status": "restricted",
        "note": "Akses data memerlukan akun/izin Direktorat Jenderal Peternakan dan Kesehatan Hewan.",
    },
    {
        "id": "who-sear",
        "name": "WHO SEARO • Epidemiological Bulletin",
        "level": "Regional",
        "kind": "Buletin resmi",
        "access_level": "public",
        "url": "https://www.who.int/southeastasia/outbreaks-and-emergencies/surveillance-and-alert/sear-epi-bulletins",
        "default_status": "scheduled",
        "note": "Buletin regional ditampilkan sebagai publikasi; ekstraksi angka tabel belum dilakukan.",
    },
    {
        "id": "who-wpro",
        "name": "WHO WPRO • Outbreaks and emergencies",
        "level": "Regional",
        "kind": "Portal resmi",
        "access_level": "public",
        "url": "https://www.who.int/westernpacific/emergencies",
        "default_status": "portal_only",
        "note": "Belum ditemukan feed peristiwa publik yang terdokumentasi; tautan portal disediakan.",
    },
    {
        "id": "abvc",
        "name": "ASEAN BioDiaspora Virtual Center",
        "level": "Regional",
        "kind": "Risk assessment",
        "access_level": "public",
        "url": "https://asean.org/our-communities/asean-socio-cultural-community/health/",
        "default_status": "portal_only",
        "note": "Publikasi regional tersedia, tetapi belum ada API peristiwa publik terdokumentasi.",
    },
    {
        "id": "who-don",
        "name": "WHO • Disease Outbreak News",
        "level": "Global",
        "kind": "Kejadian resmi",
        "access_level": "public",
        "url": "https://www.who.int/emergencies/disease-outbreak-news",
        "default_status": "scheduled",
        "note": "Diambil dari API publik WHO dan dipetakan pada centroid negara bila lokasi lebih rinci tidak tersedia.",
    },
    {
        "id": "gdelt",
        "name": "GDELT • Media signals",
        "level": "Global",
        "kind": "Sinyal media",
        "access_level": "public",
        "url": "https://www.gdeltproject.org/",
        "default_status": "scheduled",
        "note": "Judul disaring untuk nama penyakit dan indikator kejadian; semua rekaman tetap berstatus rumor/verifikasi, dan negara hanya dipetakan bila disebut dalam judul.",
    },
    {
        "id": "fao-empres",
        "name": "FAO • EMPRES-i+",
        "level": "Global",
        "kind": "Kesehatan hewan",
        "access_level": "restricted",
        "url": "https://empres-i.apps.fao.org/",
        "default_status": "authentication_required",
        "note": "Endpoint peristiwa memerlukan token; tidak dilakukan scraping aplikasi.",
    },
    {
        "id": "fao-tad-situation",
        "name": "FAO • Animal disease situation updates",
        "level": "Global",
        "kind": "Situasi resmi TADs",
        "access_level": "public",
        "url": "https://www.fao.org/animal-health/situation-updates/",
        "default_status": "portal_only",
        "note": "Pembaruan resmi ASF/FMD dan penyakit hewan lain; rekaman terstruktur dimasukkan melalui impor terotorisasi sampai feed publik terdokumentasi tersedia.",
    },
    {
        "id": "gf-tads",
        "name": "GF-TADs • FAO–WOAH",
        "level": "Global",
        "kind": "Kerangka resmi TADs",
        "access_level": "public",
        "url": "https://www.gf-tads.org/",
        "default_status": "portal_only",
        "note": "Sumber kebijakan dan situasi regional; bukan feed kejadian publik terpisah.",
    },
    {
        "id": "wrlfmd",
        "name": "WOAH–FAO FMD Reference Laboratory Network",
        "level": "Global",
        "kind": "Laporan laboratorium rujukan",
        "access_level": "public",
        "url": "https://www.wrlfmd.org/",
        "default_status": "manual_import",
        "note": "Laporan triwulanan digunakan sebagai sumber resmi PMK/FMD melalui impor terotorisasi dan verifikasi manual.",
    },
    {
        "id": "woah-wahis",
        "name": "WOAH • WAHIS",
        "level": "Global",
        "kind": "Notifikasi kesehatan hewan",
        "access_level": "public",
        "url": "https://wahis.woah.org/",
        "default_status": "portal_only",
        "note": "Data publik tersedia melalui portal; belum ada API publik terdokumentasi untuk otomasi ini.",
    },
    {
        "id": "glews",
        "name": "GLEWS+ (FAO–WHO–WOAH)",
        "level": "Global",
        "kind": "Validasi lintas organisasi",
        "access_level": "institutional",
        "url": "https://www.fao.org/animal-health/areas-of-work/early-warning-and-disease-intelligence/FAO%27s-EMPRES-Global-Animal-Disease-Information-System-%28EMPRES-i-%29/en",
        "default_status": "institutional_access",
        "note": "Mekanisme institusional; tidak tersedia feed peristiwa publik terpisah.",
    },
    {
        "id": "promed",
        "name": "ProMED",
        "level": "Global",
        "kind": "Expert-moderated signals",
        "access_level": "licensed",
        "url": "https://www.promedmail.org/subscribe/",
        "default_status": "license_required",
        "note": "API memerlukan lisensi; syarat layanan melarang scraping tanpa izin.",
    },
]


def fetch_text(url: str, timeout: int = 45) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json"})
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


class SourceFetchError(RuntimeError):
    """A source failed, but a vetted public snapshot may still be retained."""

    def __init__(self, message: str, fallback_records: list[dict] | None = None):
        super().__init__(message)
        self.fallback_records = fallback_records or []


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def stable_id(prefix: str, *parts: str) -> str:
    payload = "|".join(parts).encode("utf-8")
    return prefix + "-" + hashlib.sha1(payload).hexdigest()[:12]


def strip_markup(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def term_in_text(text: str, term: str) -> bool:
    """Match a term on Unicode word boundaries to avoid hits such as MERS in farmers."""
    return re.search(rf"(?<!\w){re.escape(term.casefold())}(?!\w)", text.casefold()) is not None


def recognized_disease_from_text(text: str) -> str | None:
    for disease, keywords in DISEASES:
        if any(term_in_text(text, keyword) for keyword in keywords):
            return disease
    return None


def disease_groups_for(disease: str) -> list[str]:
    """Return non-exclusive surveillance groups for a normalized disease."""
    groups: list[str] = []
    if disease in ANIMAL_PRIORITY_DISEASES:
        groups.append("Penyakit hewan prioritas")
    if disease in TAD_DISEASES:
        groups.append("TADs")
    if disease not in PURE_ANIMAL_DISEASES:
        groups.append("Zoonosis/EID")
    return groups or ["Zoonosis/EID"]


def disease_from_title(title: str) -> str:
    recognized = recognized_disease_from_text(title)
    if recognized:
        return recognized
    head = re.split(r"\s[-–—]\s|,", title, maxsplit=1)[0].strip()
    return head[:90] if head else "Penyakit infeksi emerging"


def gdelt_signal_disease(title: str) -> str | None:
    """Return a disease only when a GDELT headline plausibly describes an event."""
    disease = recognized_disease_from_text(title)
    if not disease:
        return None

    has_event_term = any(term_in_text(title, term) for term in GDELT_EVENT_TERMS)
    has_hard_event_term = any(term_in_text(title, term) for term in GDELT_HARD_EVENT_TERMS)
    has_non_event_term = any(term_in_text(title, term) for term in GDELT_NON_EVENT_TERMS)
    has_always_non_event_term = any(term_in_text(title, term) for term in GDELT_ALWAYS_NON_EVENT_TERMS)
    disease_keywords = next(keywords for name, keywords in DISEASES if name == disease)
    folded = title.casefold().lstrip(" \t:;,-–—[]()")
    disease_led = any(re.match(rf"{re.escape(keyword.casefold())}(?!\w)", folded) for keyword in disease_keywords)
    has_location = bool(locations_from_text(title))

    if has_always_non_event_term:
        return None
    if has_non_event_term and not has_hard_event_term:
        return None
    if not has_event_term and not (disease_led and has_location):
        return None
    return disease


def sanitize_retained_gdelt(records: list[dict]) -> list[dict]:
    """Re-screen retained GDELT data so stale false positives cannot persist."""
    screened = []
    for record in records:
        disease = gdelt_signal_disease(record.get("title") or "")
        if not disease:
            continue
        cleaned = dict(record)
        cleaned["disease"] = disease
        cleaned["disease_groups"] = disease_groups_for(disease)
        cleaned["record_type"] = "event" if cleaned.get("iso3") else "report"
        screened.append(cleaned)
    return screened


def locations_from_text(text: str) -> list[dict]:
    folded = " " + text.casefold() + " "
    found = []
    for iso3, (name, lat, lon, aliases) in COUNTRIES.items():
        for alias in sorted(aliases, key=len, reverse=True):
            if re.search(r"(?<![a-z])" + re.escape(alias.casefold()) + r"(?![a-z])", folded):
                found.append({"iso3": iso3, "location": name, "lat": lat, "lon": lon})
                break
    return found


def blank_impact() -> tuple[dict, dict, dict]:
    human = {"suspected": None, "confirmed": None, "deaths": None}
    animal = {"outbreaks": None, "sick": None, "deaths": None, "culled": None, "species": None}
    lab = {"result": None, "method": None, "name": None}
    return human, animal, lab


def base_record(**values) -> dict:
    human, animal, lab = blank_impact()
    record = {
        "id": "",
        "record_type": "event",
        "disease": "Penyakit infeksi emerging",
        "disease_groups": ["Zoonosis/EID"],
        "title": "",
        "location": "Lokasi belum dipetakan",
        "iso3": None,
        "lat": None,
        "lon": None,
        "location_precision": "unknown",
        "scopes": ["Global"],
        "published": None,
        "onset": None,
        "reported": None,
        "updated": None,
        "evidence": "confirmed",
        "response": "Monitoring",
        "changed24h": False,
        "changeType": "Pembaruan sumber",
        "change": "Publikasi sumber diperbarui.",
        "human": human,
        "animal": animal,
        "lab": lab,
        "actions": None,
        "pic": None,
        "next": None,
        "source": "",
        "source_id": "",
        "source_url": "",
        "verification": "",
        "economic": None,
        "summary": None,
    }
    record.update(values)
    if "disease_groups" not in values:
        record["disease_groups"] = disease_groups_for(record["disease"])
    return record


def scope_list(iso3: str | None) -> list[str]:
    scopes = ["Global"]
    if iso3 == "IDN":
        scopes.insert(0, "Indonesia")
    if iso3 in {"BRN", "KHM", "IDN", "LAO", "MYS", "MMR", "PHL", "SGP", "THA", "TLS", "VNM"}:
        scopes.insert(-1, "ASEAN")
    if iso3 in {
        "AUS", "BGD", "BTN", "BRN", "KHM", "CHN", "FJI", "IND", "IDN", "JPN", "KOR", "LAO",
        "MYS", "MDV", "MMR", "NPL", "NZL", "PAK", "PNG", "PHL", "SGP", "LKA", "THA", "TLS", "TWN", "VNM",
    }:
        scopes.insert(-1, "Asia-Pacific")
    return list(dict.fromkeys(scopes))


def import_issue(report: dict, severity: str, file_name: str, row: int | None, field: str | None, message: str) -> None:
    """Record validation details without copying any row values into public output."""
    report[severity].append({
        "file": file_name,
        "row": row,
        "field": field,
        "message": message,
    })


def clean_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def xlsx_column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference.upper())
    if not letters:
        return 0
    result = 0
    for char in letters.group(0):
        result = result * 26 + ord(char) - 64
    return result - 1


def xlsx_rows(path: Path) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
    """Read the first/Import worksheet using only the Python standard library."""
    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    pkg_rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in shared_root.findall(f"{{{main_ns}}}si"):
                shared.append("".join(node.text or "" for node in item.iter(f"{{{main_ns}}}t")))

        workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
        rel_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationships = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rel_root.findall(f"{{{pkg_rel_ns}}}Relationship")
        }
        sheets = workbook_root.find(f"{{{main_ns}}}sheets")
        if sheets is None or not list(sheets):
            raise ValueError("Workbook tidak memiliki worksheet.")
        sheet_node = next((item for item in sheets if item.attrib.get("name", "").casefold() == "import"), list(sheets)[0])
        rel_id = sheet_node.attrib.get(f"{{{rel_ns}}}id")
        target = relationships.get(rel_id or "")
        if not target:
            raise ValueError("Worksheet tidak dapat ditemukan di dalam workbook.")
        sheet_path = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
        sheet_root = ET.fromstring(archive.read(sheet_path))

        raw_rows: list[tuple[int, list[str]]] = []
        for row_node in sheet_root.iter(f"{{{main_ns}}}row"):
            row_number = int(row_node.attrib.get("r") or len(raw_rows) + 1)
            cells: dict[int, str] = {}
            for cell in row_node.findall(f"{{{main_ns}}}c"):
                index = xlsx_column_index(cell.attrib.get("r", "A1"))
                cell_type = cell.attrib.get("t")
                if cell_type == "inlineStr":
                    value = "".join(node.text or "" for node in cell.iter(f"{{{main_ns}}}t"))
                else:
                    value_node = cell.find(f"{{{main_ns}}}v")
                    value = value_node.text if value_node is not None and value_node.text is not None else ""
                    if cell_type == "s" and value:
                        value = shared[int(value)]
                    elif cell_type == "b":
                        value = "true" if value == "1" else "false"
                cells[index] = clean_cell(value)
            if cells:
                width = max(cells) + 1
                raw_rows.append((row_number, [cells.get(index, "") for index in range(width)]))

    if not raw_rows:
        return [], []
    header_position = next((i for i, (_, values) in enumerate(raw_rows) if any(values)), None)
    if header_position is None:
        return [], []
    headers = [clean_cell(value).casefold() for value in raw_rows[header_position][1]]
    output: list[tuple[int, dict[str, str]]] = []
    for row_number, values in raw_rows[header_position + 1:]:
        if not any(clean_cell(value) for value in values):
            continue
        padded = values + [""] * max(0, len(headers) - len(values))
        output.append((row_number, {header: clean_cell(padded[index]) for index, header in enumerate(headers) if header}))
    return headers, output


def csv_rows(path: Path) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = [clean_cell(value).casefold() for value in (reader.fieldnames or [])]
        rows = []
        for row_number, row in enumerate(reader, start=2):
            normalized = {clean_cell(key).casefold(): clean_cell(value) for key, value in row.items() if key is not None}
            if any(normalized.values()):
                rows.append((row_number, normalized))
    return headers, rows


def parse_import_date(value: str, field: str) -> tuple[str, datetime]:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} harus tanggal ISO 8601, misalnya 2026-08-15 atau 2026-08-15T09:00:00Z.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(timezone.utc)
    return parsed.isoformat().replace("+00:00", "Z"), parsed


def parse_nonnegative_integer(value: str, field: str) -> int | None:
    if not value:
        return None
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(f"{field} harus bilangan bulat non-negatif atau kosong.") from exc
    if number < 0:
        raise ValueError(f"{field} tidak boleh negatif.")
    return number


def parse_coordinate(value: str, field: str, minimum: float, maximum: float) -> float | None:
    if not value:
        return None
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"{field} harus berupa angka.") from exc
    if not minimum <= number <= maximum:
        raise ValueError(f"{field} harus berada antara {minimum:g} dan {maximum:g}.")
    return number


def normalize_import_row(row: dict[str, str]) -> dict:
    required = ["record_type", "evidence", "disease", "title", "location", "published", "source_id", "source_name", "source_level", "access_level"]
    missing = [field for field in required if not row.get(field)]
    if missing:
        raise ValueError("Kolom wajib kosong: " + ", ".join(missing) + ".")

    record_type = row["record_type"].casefold()
    evidence = row["evidence"].casefold()
    access_level = row["access_level"].casefold()
    source_level = row["source_level"].title()
    if record_type not in ALLOWED_RECORD_TYPES:
        raise ValueError("record_type harus event atau report.")
    if evidence not in ALLOWED_EVIDENCE:
        raise ValueError("evidence harus confirmed atau rumor.")
    if access_level not in ALLOWED_ACCESS_LEVELS:
        raise ValueError("access_level harus public, restricted, licensed, institutional, atau internal.")
    if source_level not in ALLOWED_SOURCE_LEVELS:
        raise ValueError("source_level harus Lokal, Nasional, Regional, atau Global.")

    source_id = row["source_id"].casefold()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,79}", source_id):
        raise ValueError("source_id hanya boleh berisi huruf kecil, angka, titik, garis bawah, atau tanda hubung.")
    source_url = row.get("source_url", "")
    if source_url and not re.match(r"^https?://", source_url, re.I):
        raise ValueError("source_url harus kosong atau URL http/https.")

    published, published_dt = parse_import_date(row["published"], "published")
    if row.get("updated"):
        updated, updated_dt = parse_import_date(row["updated"], "updated")
    else:
        updated, updated_dt = published, published_dt

    iso3 = row.get("iso3", "").upper() or None
    if iso3 and not re.fullmatch(r"[A-Z]{3}", iso3):
        raise ValueError("iso3 harus kode negara tiga huruf atau kosong.")
    lat = parse_coordinate(row.get("latitude", ""), "latitude", -90, 90)
    lon = parse_coordinate(row.get("longitude", ""), "longitude", -180, 180)
    if (lat is None) != (lon is None):
        raise ValueError("latitude dan longitude harus diisi bersama-sama atau sama-sama kosong.")
    precision = row.get("location_precision", "").casefold() or "unknown"
    if lat is None and iso3 in COUNTRIES:
        _, lat, lon, _ = COUNTRIES[iso3]
        precision = "country"

    human = {
        "suspected": parse_nonnegative_integer(row.get("human_suspected", ""), "human_suspected"),
        "confirmed": parse_nonnegative_integer(row.get("human_confirmed", ""), "human_confirmed"),
        "deaths": parse_nonnegative_integer(row.get("human_deaths", ""), "human_deaths"),
    }
    animal = {
        "outbreaks": parse_nonnegative_integer(row.get("animal_outbreaks", ""), "animal_outbreaks"),
        "sick": parse_nonnegative_integer(row.get("animal_sick", ""), "animal_sick"),
        "deaths": parse_nonnegative_integer(row.get("animal_deaths", ""), "animal_deaths"),
        "culled": parse_nonnegative_integer(row.get("animal_culled", ""), "animal_culled"),
        "species": row.get("species") or None,
    }
    record_id = row.get("event_id") or stable_id("import", source_id, row["title"], row["location"], published)
    return base_record(
        id=record_id,
        record_type=record_type,
        disease=row["disease"],
        title=row["title"],
        location=row["location"],
        iso3=iso3,
        lat=lat,
        lon=lon,
        location_precision=precision,
        scopes=scope_list(iso3),
        published=published,
        reported=published,
        updated=updated,
        evidence=evidence,
        response=row.get("response") or ("Perlu verifikasi" if evidence == "rumor" else "Monitoring"),
        changed24h=updated_dt >= NOW - timedelta(hours=24),
        changeType="Impor terotorisasi",
        change="Rekaman lolos validasi skema dan ditandai eksplisit untuk publikasi.",
        human=human,
        animal=animal,
        source=row["source_name"],
        source_id=source_id,
        source_url=source_url,
        source_level=source_level,
        source_kind=row.get("source_kind") or "Impor terotorisasi",
        access_level=access_level,
        verification=row.get("verification") or "Rekaman impor; buka sumber primer dan periksa otorisasi publikasi.",
        summary=row.get("summary") or None,
    )


def imported_records() -> tuple[list[dict], list[dict], dict]:
    report = {
        "generated_at": NOW.isoformat().replace("+00:00", "Z"),
        "files_scanned": 0,
        "rows_scanned": 0,
        "rows_published": 0,
        "rows_skipped": 0,
        "errors": [],
        "warnings": [],
    }
    records: list[dict] = []
    source_counts: dict[str, int] = defaultdict(int)
    source_metadata: dict[str, dict] = {}
    if not IMPORT_DIR.exists():
        return records, [], report

    candidates = sorted(
        path for path in IMPORT_DIR.iterdir()
        if path.is_file() and path.suffix.casefold() in {".csv", ".xlsx"} and not path.name.casefold().startswith("template")
    )
    for path in candidates:
        report["files_scanned"] += 1
        try:
            headers, rows = csv_rows(path) if path.suffix.casefold() == ".csv" else xlsx_rows(path)
        except Exception as exc:
            import_issue(report, "errors", path.name, None, None, f"File tidak dapat dibaca: {type(exc).__name__}.")
            continue
        report["rows_scanned"] += len(rows)
        unexpected = sorted({header for header in headers if header and header not in IMPORT_FIELDS})
        if unexpected:
            report["rows_skipped"] += len(rows)
            import_issue(report, "errors", path.name, None, None, "File ditolak karena memiliki kolom di luar skema yang diizinkan: " + ", ".join(unexpected) + ".")
            continue
        if "publish" not in headers:
            report["rows_skipped"] += len(rows)
            import_issue(report, "errors", path.name, None, "publish", "File ditolak karena kolom publish tidak tersedia.")
            continue

        for row_number, row in rows:
            publish_value = row.get("publish", "").casefold()
            if publish_value not in {"true", "1", "yes", "ya"}:
                report["rows_skipped"] += 1
                if publish_value not in {"", "false", "0", "no", "tidak"}:
                    import_issue(report, "warnings", path.name, row_number, "publish", "Baris dilewati karena nilai publish tidak dikenali.")
                continue
            try:
                record = normalize_import_row(row)
            except ValueError as exc:
                report["rows_skipped"] += 1
                import_issue(report, "errors", path.name, row_number, None, str(exc))
                continue
            records.append(record)
            report["rows_published"] += 1
            source_id = record["source_id"]
            source_counts[source_id] += 1
            candidate = {
                "id": source_id,
                "name": record["source"],
                "level": record["source_level"],
                "kind": record["source_kind"],
                "access_level": record["access_level"],
                "url": record["source_url"],
            }
            if source_id in source_metadata and source_metadata[source_id] != candidate:
                import_issue(report, "warnings", path.name, row_number, "source_id", "Metadata source_id tidak konsisten; metadata dari baris valid pertama dipertahankan.")
            else:
                source_metadata.setdefault(source_id, candidate)

    sources = []
    checked_at = report["generated_at"]
    for source_id, metadata in sorted(source_metadata.items()):
        sources.append({
            **metadata,
            "status": "imported",
            "last_checked": checked_at,
            "records": source_counts[source_id],
            "error": None,
            "note": "Rekaman agregat/de-identifikasi diimpor dari data/import setelah validasi skema dan persetujuan publish=true.",
        })
    return records, sources, report


def who_don_records() -> list[dict]:
    params = urlencode({"$top": 100, "$orderby": "PublicationDate desc"})
    url = "https://www.who.int/api/news/diseaseoutbreaknews?" + params
    payload = json.loads(fetch_text(url))
    records = []
    cutoff = NOW - timedelta(days=MAX_AGE_DAYS)
    for item in payload.get("value", []):
        published = item.get("PublicationDate")
        published_dt = parse_iso(published)
        if not published_dt or published_dt < cutoff:
            continue
        title = strip_markup(item.get("OverrideTitle") or item.get("Title") or "WHO Disease Outbreak News")
        summary = strip_markup(item.get("Summary") or "")[:600] or None
        item_url = urljoin("https://www.who.int", item.get("ItemDefaultUrl") or "")
        locations = locations_from_text(title)
        if not locations:
            locations = [{"iso3": None, "location": "Lokasi belum dipetakan", "lat": None, "lon": None}]
        for loc in locations:
            updated = item.get("LastModified") or published
            updated_dt = parse_iso(updated) or published_dt
            records.append(base_record(
                id=stable_id("who-don", str(item.get("Id") or item.get("DonId") or title), str(loc["iso3"])),
                disease=disease_from_title(title),
                title=title,
                location=loc["location"],
                iso3=loc["iso3"],
                lat=loc["lat"],
                lon=loc["lon"],
                location_precision="country" if loc["iso3"] else "unknown",
                scopes=scope_list(loc["iso3"]),
                published=published,
                reported=published,
                updated=updated,
                evidence="confirmed",
                response="Monitoring resmi",
                changed24h=updated_dt >= NOW - timedelta(hours=24),
                changeType="Konfirmasi/pembaruan resmi",
                change="WHO Disease Outbreak News diterbitkan atau diperbarui.",
                source="WHO Disease Outbreak News",
                source_id="who-don",
                source_url=item_url,
                verification="Sumber resmi WHO; koordinat menggunakan centroid negara.",
                summary=summary,
            ))
    return records


MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def parse_publication_date(value: str) -> datetime | None:
    clean = strip_markup(value).casefold().replace("mei", "may").replace("agu", "aug").replace("okt", "oct").replace("des", "dec")
    match = re.search(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", clean)
    if not match:
        return None
    month = MONTHS.get(match.group(2)) or MONTHS.get(match.group(2)[:3])
    if not month:
        return None
    return datetime(int(match.group(3)), month, int(match.group(1)), 5, 0, tzinfo=timezone.utc)


def kemkes_records() -> list[dict]:
    source_url = "https://infeksiemerging.kemkes.go.id/"
    page = fetch_text(source_url)
    records: list[dict] = []
    cutoff = NOW - timedelta(days=MAX_AGE_DAYS)

    spot_pattern = re.compile(
        r'<a[^>]+href="(?P<url>https://infeksiemerging\.kemkes\.go\.id/spot-report/[^"]+)"[^>]*>'
        r'\s*<h1[^>]*>(?P<title>.*?)</h1>\s*<p[^>]*>(?P<date>.*?)</p>\s*</a>',
        re.I | re.S,
    )
    seen_urls = set()
    for match in spot_pattern.finditer(page):
        link = html.unescape(match.group("url"))
        if link in seen_urls:
            continue
        seen_urls.add(link)
        title = strip_markup(match.group("title"))
        published_dt = parse_publication_date(match.group("date"))
        if not published_dt or published_dt < cutoff:
            continue
        locations = locations_from_text(title)
        location = locations[0] if locations else {"iso3": None, "location": "Lokasi dalam publikasi", "lat": None, "lon": None}
        rumor = any(token in title.casefold() for token in ("[rumor]", "suspek", "dicurigai", "dugaan"))
        records.append(base_record(
            id=stable_id("kemkes-spot", link),
            record_type="report",
            disease=disease_from_title(title),
            title=title,
            location=location["location"],
            iso3=location["iso3"],
            scopes=scope_list(location["iso3"]),
            published=published_dt.isoformat().replace("+00:00", "Z"),
            reported=published_dt.isoformat().replace("+00:00", "Z"),
            updated=published_dt.isoformat().replace("+00:00", "Z"),
            evidence="rumor" if rumor else "confirmed",
            response="Publikasi kewaspadaan",
            changed24h=published_dt >= NOW - timedelta(hours=24),
            changeType="Publikasi baru",
            change="Spot report Kemenkes dipublikasikan.",
            source="Kemenkes RI • Infeksi Emerging",
            source_id="kemkes-infem",
            source_url=link,
            verification="Publikasi resmi Kemenkes; bukan feed angka kasus terstruktur.",
        ))

    weekly_pattern = re.compile(
        r'<span[^>]*>(?P<date>\d{1,2}\s+[A-Za-z]+\s+\d{4})\s*\|[^<]*</span>\s*'
        r'.{0,900}?<a[^>]+href="(?P<url>https://infeksiemerging\.kemkes\.go\.id/weekly-update/[^"]+)"[^>]*>(?P<title>.*?)</a>',
        re.I | re.S,
    )
    for match in weekly_pattern.finditer(page):
        link = html.unescape(match.group("url"))
        if link in seen_urls:
            continue
        seen_urls.add(link)
        title = strip_markup(match.group("title"))
        published_dt = parse_publication_date(match.group("date"))
        if not published_dt or published_dt < cutoff:
            continue
        records.append(base_record(
            id=stable_id("kemkes-weekly", link),
            record_type="report",
            disease="Ringkasan penyakit infeksi emerging",
            title=title,
            location="Indonesia",
            iso3="IDN",
            scopes=scope_list("IDN"),
            published=published_dt.isoformat().replace("+00:00", "Z"),
            reported=published_dt.isoformat().replace("+00:00", "Z"),
            updated=published_dt.isoformat().replace("+00:00", "Z"),
            evidence="confirmed",
            response="Publikasi berkala",
            changed24h=published_dt >= NOW - timedelta(hours=24),
            changeType="Buletin baru",
            change="Weekly update Kemenkes dipublikasikan.",
            source="Kemenkes RI • Infeksi Emerging",
            source_id="kemkes-infem",
            source_url=link,
            verification="Publikasi resmi Kemenkes; angka rinci tersedia pada dokumen sumber.",
        ))
    return records


class HtmlTableCollector(HTMLParser):
    """Collect text cells from ordinary HTML tables without external packages."""

    def __init__(self):
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table_depth = 0
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, _attrs) -> None:
        tag = tag.casefold()
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._table = []
        elif self._table_depth == 1 and tag == "tr":
            self._row = []
        elif self._table_depth == 1 and tag in {"th", "td"} and self._row is not None:
            self._cell = []
        elif self._cell is not None and tag == "br":
            self._cell.append(" ")

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if self._table_depth == 1 and tag in {"th", "td"} and self._cell is not None:
            self._row.append(strip_markup(" ".join(self._cell)))
            self._cell = None
        elif self._table_depth == 1 and tag == "tr" and self._row is not None:
            if any(cell for cell in self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table_depth:
            if self._table_depth == 1 and self._table:
                self.tables.append(self._table)
                self._table = None
            self._table_depth -= 1


AWR_DISEASES = {
    "PMK": "Foot-and-Mouth Disease (FMD/PMK)",
    "LSD": "Lumpy Skin Disease (LSD)",
    "Rabies": "Rabies",
    "HPAI": "Avian influenza",
    "Anthraks": "Anthrax",
    "SE": "Septicaemia Epizootica (SE)",
    "Jembrana": "Jembrana Disease",
    "ASF": "African Swine Fever (ASF)",
    "CSF": "Classical Swine Fever (CSF)",
    "Brucellosis": "Brucellosis",
    "Surra": "Surra (Trypanosomiasis)",
}

# Approximate province centroids are used only for map placement. The original
# province and district names remain visible in the event detail and source link.
INDONESIA_PROVINCE_CENTROIDS = {
    "aceh": (4.70, 96.75),
    "sumatera utara": (2.12, 99.55),
    "sumatera barat": (-0.74, 100.80),
    "riau": (0.29, 101.71),
    "kepulauan riau": (3.95, 108.14),
    "jambi": (-1.49, 102.44),
    "sumatera selatan": (-3.32, 103.91),
    "bangka belitung": (-2.74, 106.44),
    "kepulauan bangka belitung": (-2.74, 106.44),
    "bengkulu": (-3.58, 102.35),
    "lampung": (-4.56, 105.41),
    "banten": (-6.41, 106.06),
    "dki jakarta": (-6.21, 106.85),
    "jawa barat": (-7.09, 107.67),
    "jawa tengah": (-7.15, 110.14),
    "di yogyakarta": (-7.88, 110.43),
    "d.i. yogyakarta": (-7.88, 110.43),
    "jawa timur": (-7.54, 112.24),
    "bali": (-8.34, 115.09),
    "nusa tenggara barat": (-8.65, 117.36),
    "nusa tenggara timur": (-8.66, 121.08),
    "kalimantan barat": (-0.28, 111.48),
    "kalimantan tengah": (-1.68, 113.38),
    "kalimantan selatan": (-3.09, 115.28),
    "kalimantan timur": (0.54, 116.42),
    "kalimantan utara": (3.07, 116.04),
    "sulawesi utara": (0.62, 123.98),
    "gorontalo": (0.70, 122.45),
    "sulawesi tengah": (-1.43, 121.45),
    "sulawesi barat": (-2.84, 119.23),
    "sulawesi selatan": (-3.67, 119.97),
    "sulawesi tenggara": (-4.14, 122.17),
    "maluku": (-3.24, 130.15),
    "maluku utara": (1.57, 127.81),
    "papua barat": (-1.34, 133.17),
    "papua barat daya": (-0.86, 131.25),
    "papua": (-4.27, 138.08),
    "papua selatan": (-6.71, 139.69),
    "papua tengah": (-3.74, 136.50),
    "papua pegunungan": (-4.00, 138.90),
}


def normalized_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", strip_markup(value).casefold()).strip()


def table_with_columns(tables: list[list[list[str]]], required: set[str]) -> tuple[dict[str, int], list[list[str]]] | None:
    for table in tables:
        for row_index, row in enumerate(table):
            columns = {normalized_header(cell): index for index, cell in enumerate(row) if normalized_header(cell)}
            if required.issubset(columns):
                return columns, table[row_index + 1:]
    return None


def awr_integer(value: str) -> int | None:
    cleaned = re.sub(r"[^0-9-]", "", value or "")
    if not cleaned or cleaned == "-":
        return None
    number = int(cleaned)
    return number if number >= 0 else None


def parse_awr_page(page: str) -> tuple[list[dict], str | None]:
    parser = HtmlTableCollector()
    parser.feed(page)
    spatial = table_with_columns(parser.tables, {"prop", "kab", "desa", "kejadian", "kasus"})
    species_table = table_with_columns(parser.tables, {"spec", "kejadian", "kasus"})
    species: list[str] = []
    if species_table:
        columns, rows = species_table
        for row in rows:
            if len(row) > columns["spec"]:
                name = strip_markup(row[columns["spec"]])
                if name and name.casefold() not in {"total", "jumlah"}:
                    species.append(name.title())

    output: list[dict] = []
    if not spatial:
        return output, ", ".join(dict.fromkeys(species)) or None
    columns, rows = spatial
    for row in rows:
        if len(row) <= max(columns.values()):
            continue
        province = strip_markup(row[columns["prop"]])
        if not province or province.casefold() in {"total", "jumlah"}:
            continue
        outbreaks = awr_integer(row[columns["kejadian"]])
        cases = awr_integer(row[columns["kasus"]])
        if outbreaks is None and cases is None:
            continue
        output.append({
            "province": province,
            "districts": strip_markup(row[columns["kab"]]),
            "villages": awr_integer(row[columns["desa"]]),
            "outbreaks": outbreaks,
            "cases": cases,
        })
    return output, ", ".join(dict.fromkeys(species)) or None


def month_keys_before(reference: datetime, count: int = 3) -> list[str]:
    year, month = reference.year, reference.month
    keys = []
    for _ in range(count):
        month -= 1
        if month == 0:
            year -= 1
            month = 12
        keys.append(f"{year:04d}{month:02d}")
    return keys


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def awr_record(disease_code: str, period: str, row: dict, species: str | None = None) -> dict:
    disease = AWR_DISEASES[disease_code]
    year, month = int(period[:4]), int(period[4:])
    final_day = calendar.monthrange(year, month)[1]
    period_end = datetime(year, month, final_day, 23, 59, 59, tzinfo=timezone.utc)
    province = row["province"]
    coords = INDONESIA_PROVINCE_CENTROIDS.get(normalized_header(province))
    lat, lon = coords if coords else COUNTRIES["IDN"][1:3]
    districts = row.get("districts") or "—"
    villages = row.get("villages")
    source_url = f"https://awr.ditjenpkh.pertanian.go.id/sitreps/{disease_code}/{period}.html"
    month_label = period_end.strftime("%B %Y")
    return base_record(
        id=f"awr-{disease_code.casefold()}-{period}-{slug(province)}",
        record_type="event",
        disease=disease,
        title=f"{disease} — SITREPS {month_label} · {province}",
        location=f"{province}, Indonesia",
        iso3="IDN",
        lat=lat,
        lon=lon,
        location_precision="province" if coords else "country",
        scopes=scope_list("IDN"),
        published=period_end.isoformat().replace("+00:00", "Z"),
        reported=period_end.isoformat().replace("+00:00", "Z"),
        updated=period_end.isoformat().replace("+00:00", "Z"),
        evidence="confirmed",
        response="Monitoring resmi",
        changed24h=False,
        changeType="Agregat bulanan resmi",
        change="AWR SITREPS memuat agregat kejadian dengan diagnosis definitif (DX).",
        animal={
            "outbreaks": row.get("outbreaks"),
            "sick": row.get("cases"),
            "deaths": None,
            "culled": None,
            "species": species,
        },
        lab={"result": "Diagnosis definitif (DX)", "method": None, "name": "iSIKHNAS"},
        source="Ditjen PKH • AWR SITREPS/iSIKHNAS",
        source_id="awr-sitreps",
        source_url=source_url,
        source_level="Nasional",
        source_kind="Kejadian penyakit hewan terkonfirmasi",
        access_level="public",
        verification="Sumber resmi Ditjen PKH; angka merupakan agregat provinsi/bulan dari laporan iSIKHNAS dengan diagnosis definitif (DX), bukan satu individu kasus.",
        summary=f"Kabupaten/kota: {districts}. Desa pelapor: {villages if villages is not None else '—'}.",
    )


def awr_seed_records() -> list[dict]:
    path = SEED_DIR / "awr-sitreps-202607.json"
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return [awr_record(item["disease_code"], item["period"], item, item.get("species")) for item in rows]


def awr_records() -> list[dict]:
    records: list[dict] = []
    valid_pages = 0
    for period in month_keys_before(NOW, count=3):
        for disease_code in AWR_DISEASES:
            url = f"https://awr.ditjenpkh.pertanian.go.id/sitreps/{disease_code}/{period}.html"
            try:
                page = fetch_text(url, timeout=18)
            except Exception:
                continue
            folded = page.casefold()
            if "attention required" in folded or "just a moment" in folded or "cf-mitigated" in folded:
                continue
            if "laporan perkembangan" not in folded and "provinsi dan kabupaten" not in folded:
                continue
            valid_pages += 1
            rows, species = parse_awr_page(page)
            records.extend(awr_record(disease_code, period, row, species) for row in rows)

    seed = awr_seed_records()
    if valid_pages == 0:
        raise SourceFetchError(
            "Halaman AWR tidak dapat dibaca otomatis (kemungkinan proteksi Cloudflare); snapshot resmi terakhir dipertahankan.",
            fallback_records=seed,
        )
    by_id = {record["id"]: record for record in seed}
    by_id.update({record["id"]: record for record in records})
    return list(by_id.values())


def kemkes_profile_records() -> list[dict]:
    source_url = "https://www.kemkes.go.id/id/category/profil-kesehatan"
    page = fetch_text(source_url)
    pattern = re.compile(
        r'<a\s+href="(?P<url>/id/profil-kesehatan-indonesia-[^"]+)"[^>]*>.*?'
        r'<h4[^>]*>(?P<title>.*?)</h4>.*?'
        r'<time\s+datetime="(?P<date>\d{4}-\d{2}-\d{2})"',
        re.I | re.S,
    )
    publications = []
    for match in pattern.finditer(page):
        published_dt = parse_iso(match.group("date"))
        if published_dt:
            publications.append((published_dt, strip_markup(match.group("title")), urljoin(source_url, match.group("url"))))
    if not publications:
        raise ValueError("Daftar Profil Kesehatan Kemenkes tidak ditemukan pada halaman sumber.")
    published_dt, title, link = max(publications, key=lambda item: item[0])
    published = published_dt.isoformat().replace("+00:00", "Z")
    return [base_record(
        id=stable_id("kemkes-profile", link),
        record_type="report",
        disease="Profil kesehatan manusia",
        disease_groups=["Referensi kesehatan manusia"],
        title=title,
        location="Indonesia",
        iso3="IDN",
        scopes=scope_list("IDN"),
        published=published,
        reported=published,
        updated=published,
        evidence="confirmed",
        response="Referensi statistik tahunan",
        changed24h=published_dt >= NOW - timedelta(hours=24),
        changeType="Publikasi resmi",
        change="Profil Kesehatan Indonesia terbaru tersedia pada portal Kemenkes.",
        source="Kemenkes RI • Profil Kesehatan Indonesia",
        source_id="kemkes-profile",
        source_url=link,
        source_level="Nasional",
        source_kind="Statistik kesehatan manusia",
        access_level="public",
        verification="Publikasi tahunan resmi Kemenkes; tidak dihitung sebagai kejadian wabah atau kasus real-time.",
    )]


def bps_health_profile_records() -> list[dict]:
    link = "https://www.bps.go.id/id/publication/2025/12/12/7d17daec8d62c852fc354945/profil-statistik-kesehatan-2025.html"
    published = "2025-12-12T00:00:00Z"
    return [base_record(
        id="bps-health-profile-2025",
        record_type="report",
        disease="Profil statistik kesehatan",
        disease_groups=["Referensi kesehatan manusia"],
        title="Profil Statistik Kesehatan 2025",
        location="Indonesia",
        iso3="IDN",
        scopes=scope_list("IDN"),
        published=published,
        reported=published,
        updated=published,
        evidence="confirmed",
        response="Referensi statistik tahunan",
        changed24h=False,
        changeType="Publikasi resmi",
        change="BPS menerbitkan Profil Statistik Kesehatan 2025.",
        source="BPS • Profil Statistik Kesehatan 2025",
        source_id="bps-health-profile",
        source_url=link,
        source_level="Nasional",
        source_kind="Statistik kesehatan manusia",
        access_level="public",
        verification="Publikasi resmi BPS berbasis Susenas Maret 2025; tidak dihitung sebagai kejadian wabah atau kasus real-time.",
        summary="Indikator kesehatan penduduk tersedia pada tingkat nasional dan provinsi, termasuk kesehatan balita, wanita usia subur, dan pengeluaran kesehatan rumah tangga.",
    )]


def who_sear_records() -> list[dict]:
    source_url = "https://www.who.int/southeastasia/outbreaks-and-emergencies/surveillance-and-alert/sear-epi-bulletins"
    page = fetch_text(source_url)
    records: list[dict] = []
    cutoff = NOW - timedelta(days=MAX_AGE_DAYS)
    first_pattern = re.compile(
        r'<a href="(?P<url>https://cdn\.who\.int/media/docs/[^"]+\.pdf[^\"]*)"[^>]*>.*?'
        r'<div[^>]+class="item--title"[^>]*>(?P<title>.*?)</div>.*?'
        r'<div[^>]+class="item--subtitle"[^>]*>(?P<date>.*?)</div>',
        re.I | re.S,
    )
    item_pattern = re.compile(
        r'<span>(?P<date>\d{1,2}\s+[A-Za-z]+\s+\d{4})</span>.*?'
        r'<h3[^>]+sf-publications-item__title[^>]*>(?P<title>.*?)</h3>.*?'
        r'<a[^>]+class="download-url[^\"]*"\s+href="(?P<url>[^"]+)"',
        re.I | re.S,
    )
    seen = set()
    for pattern in (first_pattern, item_pattern):
        for match in pattern.finditer(page):
            link = html.unescape(match.group("url"))
            if link in seen:
                continue
            seen.add(link)
            title = strip_markup(match.group("title"))
            published_dt = parse_publication_date(match.group("date"))
            if not published_dt or published_dt < cutoff:
                continue
            records.append(base_record(
                id=stable_id("who-sear", link),
                record_type="report",
                disease="Epidemiological bulletin",
                title=title,
                location="WHO South-East Asia Region",
                scopes=["ASEAN", "Asia-Pacific", "Global"],
                published=published_dt.isoformat().replace("+00:00", "Z"),
                reported=published_dt.isoformat().replace("+00:00", "Z"),
                updated=published_dt.isoformat().replace("+00:00", "Z"),
                evidence="confirmed",
                response="Buletin regional",
                changed24h=published_dt >= NOW - timedelta(hours=24),
                changeType="Buletin baru",
                change="Buletin epidemiologi regional WHO diterbitkan.",
                source="WHO SEARO • Epidemiological Bulletin",
                source_id="who-sear",
                source_url=link,
                verification="Publikasi resmi WHO Regional Office for South-East Asia.",
            ))
    return records


def gdelt_records() -> list[dict]:
    queries = [
        '("avian influenza" OR "bird flu" OR rabies OR anthrax OR leptospirosis OR Nipah OR hantavirus OR Ebola OR Marburg OR mpox)',
        '("foot-and-mouth disease" OR "african swine fever" OR "lumpy skin disease" OR "classical swine fever" OR "peste des petits ruminants" OR "newcastle disease" OR "african horse sickness" OR "sheep pox" OR "goat pox")',
    ]
    records: list[dict] = []
    articles: list[dict] = []
    for query in queries:
        params = urlencode({"query": query, "mode": "ArtList", "maxrecords": 75, "format": "json", "timespan": "7d"})
        url = "https://api.gdeltproject.org/api/v2/doc/doc?" + params
        payload = json.loads(fetch_text(url, timeout=60))
        articles.extend(payload.get("articles", []))
    seen_links: set[str] = set()
    for article in articles:
        title = strip_markup(article.get("title") or "")
        link = article.get("url") or ""
        if not title or not link or link in seen_links:
            continue
        seen_links.add(link)
        disease = gdelt_signal_disease(title)
        if not disease:
            continue
        locations = locations_from_text(title)
        loc = locations[0] if locations else {"iso3": None, "location": "Lokasi belum teridentifikasi", "lat": None, "lon": None}
        seen = article.get("seendate") or ""
        try:
            published_dt = datetime.strptime(seen, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            published_dt = NOW
        records.append(base_record(
            id=stable_id("gdelt", link),
            record_type="event" if loc["iso3"] else "report",
            disease=disease,
            title=title,
            location=loc["location"],
            iso3=loc["iso3"],
            lat=loc["lat"],
            lon=loc["lon"],
            location_precision="country" if loc["iso3"] else "unknown",
            scopes=scope_list(loc["iso3"]),
            published=published_dt.isoformat().replace("+00:00", "Z"),
            reported=published_dt.isoformat().replace("+00:00", "Z"),
            updated=published_dt.isoformat().replace("+00:00", "Z"),
            evidence="rumor",
            response="Perlu verifikasi",
            changed24h=published_dt >= NOW - timedelta(hours=24),
            changeType="Sinyal baru",
            change="Artikel media terdeteksi; belum dianggap kejadian terkonfirmasi.",
            source=f"GDELT • {article.get('domain') or 'media'}",
            source_id="gdelt",
            source_url=link,
            verification="Sinyal media terbuka; wajib diverifikasi terhadap sumber primer.",
            summary=f"Bahasa: {article.get('language') or '—'}; negara media: {article.get('sourcecountry') or '—'}.",
        ))
    return records


IMPORTERS = {
    "awr-sitreps": awr_records,
    "who-don": who_don_records,
    "kemkes-infem": kemkes_records,
    "kemkes-profile": kemkes_profile_records,
    "bps-health-profile": bps_health_profile_records,
    "who-sear": who_sear_records,
    "gdelt": gdelt_records,
}


def load_previous() -> dict:
    try:
        return json.loads(EVENTS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"records": []}


def deduplicate(records: list[dict]) -> list[dict]:
    unique: dict[tuple, dict] = {}
    for record in records:
        # IDs include source-specific event/location identity. A publication URL
        # alone is not a safe key because one official report may contain
        # several distinct outbreaks in the same country.
        key = (record.get("id") or stable_id(
            "fallback",
            str(record.get("source_id") or ""),
            str(record.get("source_url") or ""),
            str(record.get("location") or ""),
            str(record.get("record_type") or ""),
        ),)
        current = unique.get(key)
        if not current or (record.get("updated") or "") > (current.get("updated") or ""):
            unique[key] = record
    return sorted(unique.values(), key=lambda item: item.get("published") or "", reverse=True)


def main() -> int:
    previous = load_previous()
    previous_records = previous.get("records", [])
    all_records: list[dict] = []
    source_runtime: dict[str, dict] = {}

    for source_id, importer in IMPORTERS.items():
        checked_at = NOW.isoformat().replace("+00:00", "Z")
        try:
            records = importer()
            all_records.extend(records)
            source_runtime[source_id] = {
                "status": "live",
                "last_checked": checked_at,
                "records": len(records),
                "error": None,
            }
            print(f"{source_id}: {len(records)} records", file=sys.stderr)
        except Exception as exc:  # Keep last known good data per source.
            retained = [record for record in previous_records if record.get("source_id") == source_id]
            if not retained and isinstance(exc, SourceFetchError):
                retained = exc.fallback_records
            if source_id == "gdelt":
                retained = sanitize_retained_gdelt(retained)
            all_records.extend(retained)
            source_runtime[source_id] = {
                "status": "stale" if retained else "error",
                "last_checked": checked_at,
                "records": len(retained),
                "error": f"{type(exc).__name__}: {exc}"[:240],
            }
            print(f"{source_id}: {type(exc).__name__}: {exc}; retained {len(retained)}", file=sys.stderr)

    manual_records, manual_sources, import_validation = imported_records()
    all_records.extend(manual_records)
    print(
        f"authorized-import: {import_validation['rows_published']} published, "
        f"{import_validation['rows_skipped']} skipped",
        file=sys.stderr,
    )

    all_records = deduplicate(all_records)
    sources = []
    for source in SOURCE_REGISTRY:
        merged = dict(source)
        runtime = source_runtime.get(source["id"])
        if runtime:
            merged.update(runtime)
        else:
            merged.update({
                "status": source["default_status"],
                "last_checked": None,
                "records": 0,
                "error": None,
            })
        merged.pop("default_status", None)
        sources.append(merged)
    sources.extend(manual_sources)

    generated_at = NOW.isoformat().replace("+00:00", "Z")
    payload = {
        "metadata": {
            "generated_at": generated_at,
            "update_interval_hours": 48,
            "mode": "near-real-time",
            "records": len(all_records),
            "events": sum(record.get("record_type") == "event" for record in all_records),
            "reports": sum(record.get("record_type") == "report" for record in all_records),
            "imported_records": len(manual_records),
            "import_files_scanned": import_validation["files_scanned"],
            "import_validation_errors": len(import_validation["errors"]),
            "import_validation_warnings": len(import_validation["warnings"]),
            "method_note": "Official records and open media signals are stored separately; unknown counts remain null.",
            "tads_records": sum("TADs" in record.get("disease_groups", []) for record in all_records),
            "tads_confirmed": sum(
                "TADs" in record.get("disease_groups", []) and record.get("evidence") == "confirmed"
                for record in all_records
            ),
            "tads_rumor": sum(
                "TADs" in record.get("disease_groups", []) and record.get("evidence") == "rumor"
                for record in all_records
            ),
        },
        "sources": sources,
        "records": all_records,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EVENTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    STATUS_PATH.write_text(json.dumps({"generated_at": generated_at, "sources": sources}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    IMPORT_VALIDATION_PATH.write_text(json.dumps(import_validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    js = (
        "// Generated by scripts/update_events.py. Do not edit manually.\n"
        f"export const metadata = {json.dumps(payload['metadata'], ensure_ascii=False, separators=(',', ':'))};\n"
        f"export const sources = {json.dumps(sources, ensure_ascii=False, separators=(',', ':'))};\n"
        f"export const events = {json.dumps(all_records, ensure_ascii=False, separators=(',', ':'))};\n"
    )
    JS_PATH.write_text(js, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
