# Zoonosis and Emerging Infectious Diseases Dashboard

Dashboard near-real-time untuk memantau kejadian zoonosis, penyakit infeksi emerging, dan transboundary animal diseases (TADs) pada tingkat Indonesia, ASEAN, Asia-Pasifik, dan global.

Situs: https://ajatikusumah.github.io/Zoonosis-and-Emerging-Infectious-Diseases-Dashboard/

## Fitur

- Peta OpenStreetMap dengan tooltip nama penyakit, lokasi, kategori kasus, status bukti, dan sumber.
- Skala warna operasional: merah untuk kejadian terkonfirmasi dengan kematian, jingga untuk kasus/outbreak terkonfirmasi, kuning untuk monitoring resmi tanpa angka dampak terstruktur, dan hijau untuk sinyal awal yang belum diverifikasi.
- Pemisahan tegas antara rekaman resmi/terkonfirmasi dan rumor atau sinyal media yang masih perlu diverifikasi.
- Filter wilayah, periode, kelompok penyakit (Zoonosis/EID atau TADs), penyakit, sumber, dan status bukti.
- Kelompok tambahan memisahkan 11 penyakit hewan prioritas AWR dan publikasi referensi kesehatan manusia dari kejadian zoonosis/EID.
- TADs dapat beririsan dengan kelompok Zoonosis/EID—misalnya avian influenza dan Rift Valley fever—sehingga klasifikasi kelompok bersifat non-eksklusif.
- Publikasi dan laporan ditampilkan terpisah dari kejadian agar tidak menaikkan KPI kasus.
- Registri sumber menunjukkan apakah suatu sumber aktif, hanya tersedia melalui portal, memerlukan akun, token, akses institusi, atau lisensi.
- Impor CSV/Excel terotorisasi dengan validasi skema, persetujuan eksplisit `publish=true`, dan tampilan tingkat akses sumber.
- Angka yang tidak tersedia disimpan sebagai `null` dan ditampilkan sebagai `—`, bukan dianggap nol.
- Panel epidemiologi fase 1 menampilkan tren tahunan, CFR yang hanya dihitung dari kasus dan kematian yang sepadan, distribusi/proporsi provinsi, laju per 100.000 penduduk, dan skor kelengkapan elemen data.
- Pembaruan segera saat file laporan baru masuk atau saat gateway mengirim sinyal `new-surveillance-report`, dengan pemeriksaan cadangan setiap 2 hari (48 jam).

## Sumber yang diambil otomatis

| Sumber | Tingkat | Perlakuan |
|---|---|---|
| Ditjen PKH AWR SITREPS/iSIKHNAS | Nasional | Agregat kejadian penyakit hewan per provinsi/bulan dari diagnosis definitif (DX); `kejadian` menjadi outbreak dan `kasus` menjadi hewan sakit. Snapshot resmi terakhir dipertahankan bila proteksi situs menolak klien otomatis |
| Kemenkes RI Profil Kesehatan Indonesia | Nasional | Publikasi tahunan resmi sebagai referensi; agregat kasus zoonosis/PIE yang memiliki angka, periode, dan lokasi eksplisit dimuat sebagai kejadian historis terkonfirmasi, bukan kasus real-time |
| BPS Profil Statistik Kesehatan 2025 | Nasional | Publikasi statistik resmi berbasis Susenas Maret 2025; referensi nasional/provinsi dan bukan feed kejadian wabah |
| WHO Disease Outbreak News | Global | Kejadian resmi dari API publik WHO; lokasi dipetakan pada centroid negara bila lokasi rinci tidak tersedia |
| Kemenkes RI Infeksi Emerging | Nasional | Weekly update dan spot report publik sebagai publikasi, bukan angka kasus terstruktur |
| WHO SEARO Epidemiological Bulletin | Regional | Buletin resmi sebagai publikasi regional |
| GDELT | Global | Sinyal media tersaring; wajib memuat penyakit yang dikenali dan indikator kejadian, serta selalu berstatus rumor/verifikasi sampai ada sumber primer |

Pencarian GDELT mencakup TADs prioritas, termasuk PMK/FMD, ASF, LSD, CSF, PPR, Newcastle disease, African horse sickness, serta sheep/goat pox. Judul media TADs tetap ditempatkan dalam cluster **rumor/verifikasi** sampai dikonfirmasi oleh otoritas veteriner atau sumber resmi lain.

Ketiga sumber nasional di atas berstatus **terkonfirmasi** karena merupakan sumber resmi. AWR menghasilkan rekaman `event` penyakit hewan. Halaman publikasi Profil Kesehatan Kemenkes dan Profil Statistik Kesehatan BPS tetap bertipe `report`; khusus angka kasus zoonosis/PIE yang diekstrak dan divalidasi dari Profil Kesehatan Indonesia 2024, rekamannya bertipe `event` historis dengan tanggal akhir periode. Untuk AWR, kematian atau pemusnahan yang tidak tersedia tetap disimpan sebagai `null`, bukan nol.

## Dataset historis Profil Kesehatan Indonesia 2024

File `data/import/kemkes-profile-2024-cases.csv` memuat 95 rekaman agregat dan de-identifikasi dari publikasi resmi Kemenkes. Data dapat ditampilkan dari filter periode **Semua periode (termasuk 2022–2024)** dan seluruhnya berada pada cluster **terkonfirmasi**.

| Kelompok data | Periode | Unit | Aturan ekstraksi |
|---|---|---|---|
| Rabies | 2022–2024 | Provinsi | Hanya kematian Lyssa pada Lampiran 74.c (halaman PDF 499); GHPR dan pemberian VAR tidak dihitung sebagai kasus rabies |
| Leptospirosis | 2022–2024 | Provinsi | Kasus dan kematian pada Lampiran 74.d (halaman PDF 500) |
| COVID-19 | 2024 | Nasional | 8.624 kasus konfirmasi dan 93 kematian pada Bab VI halaman buku 228 / PDF 260; angka kumulatif tidak digandakan |
| Mpox | 2024 | Provinsi | 14 kasus pada lima provinsi pada Bab VI halaman buku 228 / PDF 260 |
| Legionellosis | 2024 | Provinsi | Hanya 16 kasus konfirmasi pada Bab VI halaman buku 229 / PDF 261; 126 suspek tidak dimasukkan ke cluster terkonfirmasi |
| Polio cVDPV2 | 2024 | Provinsi | Tujuh kasus pada lima provinsi pada Bab VI halaman buku 229 / PDF 261 |

Dua berkas Profil Kesehatan Indonesia 2022 yang diterima identik byte-per-byte. Keduanya digunakan sebagai pemeriksaan silang, bukan diimpor dua kali. Tabel rabies dan leptospirosis 2022 memakai angka pada edisi 2024 karena merupakan seri terbaru 2022–2024. Peta risiko MERS, indikator kesiapsiagaan, serta angka pajanan tanpa definisi kasus tidak dimasukkan sebagai kejadian.

## Denominator dan definisi indikator

`data/denominators.js` memuat proyeksi penduduk BPS 2022–2024 menurut 34 provinsi pada batas wilayah proyeksi SP2020, serta total Indonesia. Nilai berasal dari skenario tren publikasi **Proyeksi Penduduk Indonesia 2020–2050 Hasil SP2020** dan dikonversi dari ribu orang menjadi orang. Provinsi baru hasil pemekaran Papua tidak dipaksakan bergabung dengan provinsi induk; laju ditampilkan `—` bila denominator wilayah yang sepadan tidak tersedia.

Aturan indikator:

- **CFR** hanya dihitung bila jumlah kasus dan kematian tersedia pada penyakit, wilayah, dan tahun yang sepadan.
- **Insidensi dilaporkan** dihitung sebagai kasus baru tahunan yang dilaporkan dibagi proyeksi penduduk pada provinsi dan tahun yang sama, dikalikan 100.000. Indikator ini tidak mengoreksi under-ascertainment atau perbedaan sensitivitas surveilans.
- Untuk rabies, numerator historis yang tersedia adalah kematian Lyssa; dashboard menampilkan **mortalitas dilaporkan**, bukan insidensi rabies.
- Tanggal pada tren adalah tahun publikasi/periode tabel karena tanggal onset tidak tersedia; dashboard menyatakannya secara eksplisit.
- Populasi sapi potong 2024 dari publikasi resmi Kementan dicatat sebagai denominator referensi. Rate penyakit hewan AWR belum dihitung ketika numerator menggabungkan sapi, kambing, dan domba atau periodenya bulanan, karena pasangan spesies dan periode tidak sepadan.

## Sumber yang tercatat tetapi belum diambil otomatis

- **SIZE Nasional, SKDR, dan iSIKHNAS:** memerlukan akun atau kemitraan data.
- **FAO EMPRES-i+:** endpoint kejadian memerlukan token.
- **ProMED:** akses API memerlukan lisensi; dashboard tidak melakukan scraping.
- **GLEWS+:** mekanisme berbagi informasi institusional FAO–WHO–WOAH, bukan feed publik terpisah.
- **WOAH WAHIS, WHO WPRO, dan ASEAN BioDiaspora Virtual Center:** tautan portal ditampilkan; integrasi menunggu API/feed publik yang terdokumentasi.
- **FAO Animal Disease Situation Updates, GF-TADs, dan WOAH–FAO FMD Reference Laboratory Network:** digunakan sebagai rujukan resmi TADs; rekaman terstruktur dimasukkan melalui impor terotorisasi ketika tidak tersedia feed publik yang terdokumentasi.

## Arsitektur pembaruan

`scripts/update_events.py` menormalkan semua sumber menjadi satu skema, mempertahankan data terakhir bila satu sumber sementara gagal, dan menghasilkan:

- `data/events.json` untuk audit dan penggunaan ulang;
- `data/events.js` untuk dashboard statis GitHub Pages;
- `data/source-status.json` untuk status konektor.
- `data/import-validation.json` untuk hasil validasi impor tanpa menyalin isi baris.

Workflow `.github/workflows/update-data.yml` mempunyai empat pemicu:

1. file baru atau perubahan pada `data/import/**` — diproses segera;
2. sinyal eksternal `repository_dispatch` dengan tipe `new-surveillance-report` — diproses segera;
3. jadwal cadangan setiap 2 hari (48 jam) untuk memeriksa sumber publik;
4. pemicu manual dari tab **Actions**.

Sumber publik seperti WHO, Kemenkes, WHO SEARO, GDELT, dan AWR tidak semuanya menyediakan webhook. Karena itu, kasus baru pada sumber tersebut akan terdeteksi pada pemeriksaan berikutnya, paling lambat sesuai jadwal 2 hari. Sistem/gateway yang memiliki notifikasi kasus baru dapat memanggil `repository_dispatch` agar pemeriksaan dilakukan tanpa menunggu jadwal.

Sinyal GDELT disaring secara konservatif sebelum dipublikasikan. Judul harus memuat nama penyakit yang dikenali dan indikator kejadian epidemiologis, atau berupa judul langsung nama penyakit dengan lokasi yang dapat dikenali. Artikel perdagangan, akses pasar, laporan keuangan, riset, vaksinasi, kebijakan, hasil negatif/kejadian yang telah disingkirkan, dan materi non-kejadian ditolak kecuali judul juga memuat bukti kejadian yang kuat. Judul media tidak pernah digunakan sebagai nama penyakit.

Contoh pemicu dari gateway terotorisasi:

```bash
curl -L -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/ajatikusumah/Zoonosis-and-Emerging-Infectious-Diseases-Dashboard/dispatches \
  -d '{"event_type":"new-surveillance-report"}'
```

Simpan token hanya di secret manager/gateway privat, bukan di HTML atau repository. Setelah pipeline selesai, dashboard GitHub Pages langsung dideploy ulang.

## Impor CSV/Excel yang aman

Gunakan template pada `data/import/template.csv` atau `data/import/template.xlsx`, kemudian unggah salinan berisi data ke folder `data/import/`. Hanya baris agregat/de-identifikasi dengan `publish=true` yang diproses. File dengan kolom di luar skema ditolak untuk mengurangi risiko kolom sensitif ikut dipublikasikan.

Repository dan GitHub Pages ini bersifat publik. **Jangan mengunggah data individu atau data mentah restricted**, bahkan bila `publish=false`. Panduan lengkap dan rancangan integrasi gateway privat tersedia di [`data/import/README.md`](data/import/README.md).

## Menjalankan secara lokal

```bash
python3 -m unittest discover -s tests -v
python3 scripts/update_events.py
python3 -m http.server 8000
```

Lalu buka `http://localhost:8000`.

## Catatan penggunaan

Dashboard ini adalah alat situational awareness. Status “resmi/terkonfirmasi” berarti rekaman berasal dari publikasi resmi; hal itu tidak selalu berarti setiap jumlah kasus telah dikonfirmasi laboratorium. Selalu buka sumber primer sebelum mengambil keputusan operasional.

Basemap menggunakan data © OpenStreetMap contributors dengan atribusi pada peta.
