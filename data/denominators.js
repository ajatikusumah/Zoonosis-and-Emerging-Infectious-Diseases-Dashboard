// Official denominator reference data used by the epidemiology panels.
// Human population values are persons (BPS SP2020 projection, scenario trend,
// tables 2.1.1.3–2.34.1.3; source tables are reported in thousands).
// Livestock values are heads and intentionally limited to beef cattle: they
// must not be used for multi-species AWR numerators.
export const denominatorMetadata = {
  generated_at: "2026-08-25T00:00:00Z",
  methodology_version: "1.0.0",
  human_population_source: {
    name: "BPS — Proyeksi Penduduk Indonesia 2020–2050 Hasil SP2020",
    url: "https://www.bps.go.id/id/publication/2023/05/16/fad83131cd3bb9be3bb2a657/proyeksi-penduduk-indonesia-2020-2050-hasil-",
    unit: "orang",
    years: [2022, 2023, 2024],
    note: "Skenario tren; nilai provinsi dikonversi dari ribu orang menjadi orang.",
  },
  livestock_population_source: {
    name: "Kementan — Analisis Kinerja Perdagangan Daging Sapi 2025",
    url: "https://satudata.pertanian.go.id/details/publikasi/855",
    unit: "ekor",
    year: 2024,
    species: "Sapi potong",
    note: "Angka sementara 2024; tujuh provinsi sentra dan total Indonesia. Tidak cocok untuk numerator multispecies.",
  },
};

export const humanPopulation = {
  "Indonesia": { 2022: 275719930, 2023: 278696210, 2024: 281603810 },
  "Aceh": { 2022: 5409190, 2023: 5482530, 2024: 5554820 },
  "Sumatera Utara": { 2022: 15180530, 2023: 15386640, 2024: 15588530 },
  "Sumatera Barat": { 2022: 5677550, 2023: 5757210, 2024: 5836160 },
  "Riau": { 2022: 6555750, 2023: 6642870, 2024: 6728050 },
  "Jambi": { 2022: 3633190, 2023: 3679170, 2024: 3724280 },
  "Sumatera Selatan": { 2022: 8647260, 2023: 8743520, 2024: 8837300 },
  "Bengkulu": { 2022: 2059370, 2023: 2086010, 2024: 2112240 },
  "Lampung": { 2022: 9206260, 2023: 9313990, 2024: 9419580 },
  "Kepulauan Bangka Belitung": { 2022: 1491990, 2023: 1511900, 2024: 1531530 },
  "Kepulauan Riau": { 2022: 2121480, 2023: 2152630, 2024: 2183290 },
  "DKI Jakarta": { 2022: 10640010, 2023: 10672100, 2024: 10684950 },
  "Jawa Barat": { 2022: 49306780, 2023: 49860330, 2024: 50345190 },
  "Jawa Tengah": { 2022: 37180410, 2023: 37540960, 2024: 37892280 },
  "DI Yogyakarta": { 2022: 3712570, 2023: 3736490, 2024: 3759500 },
  "Jawa Timur": { 2022: 41229980, 2023: 41527930, 2024: 41814500 },
  "Banten": { 2022: 12167040, 2023: 12307730, 2024: 12431390 },
  "Bali": { 2022: 4374310, 2023: 4404260, 2024: 4433260 },
  "Nusa Tenggara Barat": { 2022: 5473970, 2023: 5560290, 2024: 5646020 },
  "Nusa Tenggara Timur": { 2022: 5481790, 2023: 5569070, 2024: 5656040 },
  "Kalimantan Barat": { 2022: 5549700, 2023: 5623330, 2024: 5695480 },
  "Kalimantan Tengah": { 2022: 2737190, 2023: 2773750, 2024: 2809700 },
  "Kalimantan Selatan": { 2022: 4170170, 2023: 4222330, 2024: 4273400 },
  "Kalimantan Timur": { 2022: 3856780, 2023: 3909740, 2024: 4045860 },
  "Kalimantan Utara": { 2022: 720060, 2023: 730010, 2024: 739780 },
  "Sulawesi Utara": { 2022: 2660760, 2023: 2681540, 2024: 2701780 },
  "Sulawesi Tengah": { 2022: 3051150, 2023: 3086750, 2024: 3121750 },
  "Sulawesi Selatan": { 2022: 9260070, 2023: 9362290, 2024: 9463390 },
  "Sulawesi Tenggara": { 2022: 2704610, 2023: 2749010, 2024: 2793070 },
  "Gorontalo": { 2022: 1198420, 2023: 1213180, 2024: 1227790 },
  "Sulawesi Barat": { 2022: 1458890, 2023: 1481080, 2024: 1503230 },
  "Maluku": { 2022: 1895070, 2023: 1920460, 2024: 1945650 },
  "Maluku Utara": { 2022: 1318470, 2023: 1337150, 2024: 1355620 },
  "Papua Barat": { 2022: 1168420, 2023: 1187270, 2024: 1205820 },
  "Papua": { 2022: 4420740, 2023: 4482690, 2024: 4542580 },
};

export const livestockPopulation = {
  species: "Sapi potong",
  year: 2024,
  values: {
    "Indonesia": 11749780,
    "Jawa Timur": 3110123,
    "Jawa Tengah": 1257225,
    "Lampung": 820246,
    "Sulawesi Selatan": 814177,
    "Nusa Tenggara Barat": 811886,
    "Sumatera Utara": 762216,
    "Nusa Tenggara Timur": 593636,
  },
};
