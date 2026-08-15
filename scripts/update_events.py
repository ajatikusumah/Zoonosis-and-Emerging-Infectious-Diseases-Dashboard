#!/usr/bin/env python3
"""Build normalized near-real-time surveillance data for the static dashboard.

Only public machine-readable or public report pages are ingested. Sources that
require credentials or a licence are listed in the source registry but are not
scraped.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
EVENTS_PATH = DATA_DIR / "events.json"
STATUS_PATH = DATA_DIR / "source-status.json"
JS_PATH = DATA_DIR / "events.js"
USER_AGENT = (
    "ZoonosisDashboard/1.0 "
    "(+https://github.com/ajatikusumah/"
    "Zoonosis-and-Emerging-Infectious-Diseases-Dashboard)"
)
NOW = datetime.now(timezone.utc)
MAX_AGE_DAYS = 365


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
    ("Avian influenza", ["avian influenza", "bird flu", "h5n1", "h5n5", "h5n6", "h9n2", "flu burung"]),
    ("Anthrax", ["anthrax", "antraks"]),
    ("Rabies", ["rabies"]),
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
    ("Brucellosis", ["brucellosis", "brucellosis"]),
    ("Lassa fever", ["lassa fever"]),
    ("Yellow fever", ["yellow fever", "demam kuning"]),
    ("Dengue", ["dengue"]),
    ("Cholera", ["cholera", "kolera"]),
    ("Meningococcal disease", ["meningococcal", "meningokokus"]),
]


SOURCE_REGISTRY = [
    {
        "id": "kemkes-infem",
        "name": "Kemenkes RI • Infeksi Emerging",
        "level": "Nasional",
        "kind": "Laporan resmi",
        "url": "https://infeksiemerging.kemkes.go.id/",
        "default_status": "scheduled",
        "note": "Weekly update dan spot report publik; diperlakukan sebagai publikasi, bukan angka kasus terstruktur.",
    },
    {
        "id": "size-nasional",
        "name": "SIZE Nasional",
        "level": "Nasional",
        "kind": "Sistem lintas sektor",
        "url": "https://www.fao.org/indonesia/news/detail/SIZE-Nasional-Harnessing-Technology-for-Effective-Control-of-Infectious-Diseases/en",
        "default_status": "restricted",
        "note": "Akses data operasional memerlukan kemitraan/otorisasi.",
    },
    {
        "id": "skdr",
        "name": "SKDR Kemenkes",
        "level": "Nasional",
        "kind": "Surveilans indikator/event",
        "url": "https://skdr.surveilans.org/",
        "default_status": "restricted",
        "note": "Data rinci memerlukan akun berwenang.",
    },
    {
        "id": "isikhnas",
        "name": "iSIKHNAS",
        "level": "Nasional",
        "kind": "Kesehatan hewan",
        "url": "https://isikhnas.pertanian.go.id/",
        "default_status": "restricted",
        "note": "Akses data memerlukan akun/izin Direktorat Jenderal Peternakan dan Kesehatan Hewan.",
    },
    {
        "id": "who-sear",
        "name": "WHO SEARO • Epidemiological Bulletin",
        "level": "Regional",
        "kind": "Buletin resmi",
        "url": "https://www.who.int/southeastasia/outbreaks-and-emergencies/surveillance-and-alert/sear-epi-bulletins",
        "default_status": "scheduled",
        "note": "Buletin regional ditampilkan sebagai publikasi; ekstraksi angka tabel belum dilakukan.",
    },
    {
        "id": "who-wpro",
        "name": "WHO WPRO • Outbreaks and emergencies",
        "level": "Regional",
        "kind": "Portal resmi",
        "url": "https://www.who.int/westernpacific/emergencies",
        "default_status": "portal_only",
        "note": "Belum ditemukan feed peristiwa publik yang terdokumentasi; tautan portal disediakan.",
    },
    {
        "id": "abvc",
        "name": "ASEAN BioDiaspora Virtual Center",
        "level": "Regional",
        "kind": "Risk assessment",
        "url": "https://asean.org/our-communities/asean-socio-cultural-community/health/",
        "default_status": "portal_only",
        "note": "Publikasi regional tersedia, tetapi belum ada API peristiwa publik terdokumentasi.",
    },
    {
        "id": "who-don",
        "name": "WHO • Disease Outbreak News",
        "level": "Global",
        "kind": "Kejadian resmi",
        "url": "https://www.who.int/emergencies/disease-outbreak-news",
        "default_status": "scheduled",
        "note": "Diambil dari API publik WHO dan dipetakan pada centroid negara bila lokasi lebih rinci tidak tersedia.",
    },
    {
        "id": "gdelt",
        "name": "GDELT • Media signals",
        "level": "Global",
        "kind": "Sinyal media",
        "url": "https://www.gdeltproject.org/",
        "default_status": "scheduled",
        "note": "Semua rekaman tetap berstatus rumor/verifikasi; negara hanya dipetakan bila disebut dalam judul.",
    },
    {
        "id": "fao-empres",
        "name": "FAO • EMPRES-i+",
        "level": "Global",
        "kind": "Kesehatan hewan",
        "url": "https://empres-i.apps.fao.org/",
        "default_status": "authentication_required",
        "note": "Endpoint peristiwa memerlukan token; tidak dilakukan scraping aplikasi.",
    },
    {
        "id": "woah-wahis",
        "name": "WOAH • WAHIS",
        "level": "Global",
        "kind": "Notifikasi kesehatan hewan",
        "url": "https://wahis.woah.org/",
        "default_status": "portal_only",
        "note": "Data publik tersedia melalui portal; belum ada API publik terdokumentasi untuk otomasi ini.",
    },
    {
        "id": "glews",
        "name": "GLEWS+ (FAO–WHO–WOAH)",
        "level": "Global",
        "kind": "Validasi lintas organisasi",
        "url": "https://www.fao.org/animal-health/areas-of-work/early-warning-and-disease-intelligence/FAO%27s-EMPRES-Global-Animal-Disease-Information-System-%28EMPRES-i-%29/en",
        "default_status": "institutional_access",
        "note": "Mekanisme institusional; tidak tersedia feed peristiwa publik terpisah.",
    },
    {
        "id": "promed",
        "name": "ProMED",
        "level": "Global",
        "kind": "Expert-moderated signals",
        "url": "https://www.promedmail.org/subscribe/",
        "default_status": "license_required",
        "note": "API memerlukan lisensi; syarat layanan melarang scraping tanpa izin.",
    },
]


def fetch_text(url: str, timeout: int = 45) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json"})
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


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


def disease_from_title(title: str) -> str:
    folded = title.casefold()
    for disease, keywords in DISEASES:
        if any(keyword in folded for keyword in keywords):
            return disease
    head = re.split(r"\s[-–—]\s|,", title, maxsplit=1)[0].strip()
    return head[:90] if head else "Penyakit infeksi emerging"


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
    query = '("avian influenza" OR "bird flu" OR rabies OR anthrax OR leptospirosis OR Nipah OR hantavirus OR Ebola OR Marburg OR mpox)'
    params = urlencode({"query": query, "mode": "ArtList", "maxrecords": 75, "format": "json", "timespan": "7d"})
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + params
    payload = json.loads(fetch_text(url, timeout=60))
    records: list[dict] = []
    for article in payload.get("articles", []):
        title = strip_markup(article.get("title") or "")
        link = article.get("url") or ""
        if not title or not link:
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
            disease=disease_from_title(title),
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
    "who-don": who_don_records,
    "kemkes-infem": kemkes_records,
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
        key = (record.get("source_id"), record.get("source_url"), record.get("iso3"), record.get("record_type"))
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
            all_records.extend(retained)
            source_runtime[source_id] = {
                "status": "stale" if retained else "error",
                "last_checked": checked_at,
                "records": len(retained),
                "error": f"{type(exc).__name__}: {exc}"[:240],
            }
            print(f"{source_id}: {type(exc).__name__}: {exc}; retained {len(retained)}", file=sys.stderr)

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

    generated_at = NOW.isoformat().replace("+00:00", "Z")
    payload = {
        "metadata": {
            "generated_at": generated_at,
            "update_interval_hours": 6,
            "mode": "near-real-time",
            "records": len(all_records),
            "events": sum(record.get("record_type") == "event" for record in all_records),
            "reports": sum(record.get("record_type") == "report" for record in all_records),
            "method_note": "Official records and open media signals are stored separately; unknown counts remain null.",
        },
        "sources": sources,
        "records": all_records,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EVENTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    STATUS_PATH.write_text(json.dumps({"generated_at": generated_at, "sources": sources}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
