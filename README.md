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
- Pembaruan segera saat file laporan baru masuk atau saat gateway mengirim sinyal `new-surveillance-report`, dengan pemeriksaan cadangan setiap 6 jam.

## Sumber yang diambil otomatis

| Sumber | Tingkat | Perlakuan |
|---|---|---|
| Ditjen PKH AWR SITREPS/iSIKHNAS | Nasional | Agregat kejadian penyakit hewan per provinsi/bulan dari diagnosis definitif (DX); `kejadian` menjadi outbreak dan `kasus` menjadi hewan sakit. Snapshot resmi terakhir dipertahankan bila proteksi situs menolak klien otomatis |
| Kemenkes RI Profil Kesehatan Indonesia | Nasional | Publikasi tahunan resmi sebagai referensi kesehatan manusia; tidak menaikkan KPI kejadian atau kasus real-time |
| BPS Profil Statistik Kesehatan 2025 | Nasional | Publikasi statistik resmi berbasis Susenas Maret 2025; referensi nasional/provinsi dan bukan feed kejadian wabah |
| WHO Disease Outbreak News | Global | Kejadian resmi dari API publik WHO; lokasi dipetakan pada centroid negara bila lokasi rinci tidak tersedia |
| Kemenkes RI Infeksi Emerging | Nasional | Weekly update dan spot report publik sebagai publikasi, bukan angka kasus terstruktur |
| WHO SEARO Epidemiological Bulletin | Regional | Buletin resmi sebagai publikasi regional |
| GDELT | Global | Sinyal media tersaring; wajib memuat penyakit yang dikenali dan indikator kejadian, serta selalu berstatus rumor/verifikasi sampai ada sumber primer |

Pencarian GDELT mencakup TADs prioritas, termasuk PMK/FMD, ASF, LSD, CSF, PPR, Newcastle disease, African horse sickness, serta sheep/goat pox. Judul media TADs tetap ditempatkan dalam cluster **rumor/verifikasi** sampai dikonfirmasi oleh otoritas veteriner atau sumber resmi lain.

Ketiga sumber nasional di atas berstatus **terkonfirmasi** karena merupakan sumber resmi. Namun hanya AWR menghasilkan rekaman bertipe `event`. Profil Kesehatan Kemenkes dan Profil Statistik Kesehatan BPS bertipe `report`, sehingga tidak dipetakan sebagai wabah dan tidak masuk penjumlahan KPI kasus. Untuk AWR, kematian atau pemusnahan yang tidak tersedia tetap disimpan sebagai `null`, bukan nol.

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
3. jadwal cadangan setiap 6 jam untuk memeriksa sumber publik;
4. pemicu manual dari tab **Actions**.

Sumber publik seperti WHO, Kemenkes, WHO SEARO, dan GDELT tidak semuanya menyediakan webhook. Karena itu, kasus baru pada sumber tersebut akan terdeteksi pada pemeriksaan berikutnya, paling lambat sesuai jadwal 6 jam. Sistem/gateway yang memiliki notifikasi kasus baru dapat memanggil `repository_dispatch` agar pemeriksaan dilakukan tanpa menunggu jadwal.

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
