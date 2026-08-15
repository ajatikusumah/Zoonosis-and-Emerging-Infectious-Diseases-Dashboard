# Zoonosis and Emerging Infectious Diseases Dashboard

Prototipe dashboard interaktif untuk memantau kejadian zoonosis dan penyakit infeksi emerging pada tingkat Indonesia, ASEAN, Asia-Pasifik, dan global.

## Fitur

- Pemisahan kejadian **terkonfirmasi** dan **rumor/open-source signal**.
- Dampak pada manusia dan hewan ditampilkan secara terpisah.
- Peta OpenStreetMap dengan filter wilayah, periode, penyakit, dan status verifikasi.
- Tooltip marker saat disorot atau difokuskan menampilkan nama kejadian, status bukti, dan sumber informasi.
- Ringkasan laboratorium, respons dan PIC, sumber informasi, serta dampak ekonomi.
- Tren berdasarkan tanggal publikasi untuk mendukung event-based surveillance.

## Status data

> **Penting:** data yang tampil pada versi awal ini adalah data ilustratif untuk demonstrasi desain dan fungsi. Data tersebut tidak boleh digunakan sebagai dasar keputusan operasional.

Basemap menggunakan data © OpenStreetMap contributors dengan atribusi yang ditampilkan pada peta. Untuk penggunaan berskala tinggi, layanan tile perlu dievaluasi sesuai kebijakan penyedia.

Versi produksi perlu menghubungkan dan memvalidasi data dari sumber resmi, antara lain SIZE/SKDR/iSIKHNAS, ASEAN BioDiaspora Virtual Center, WOAH WAHIS, FAO EMPRES-i+, WHO Disease Outbreak News, serta GLEWS+.

## Menjalankan secara lokal

Buka `index.html` melalui server HTTP lokal, misalnya:

```bash
python3 -m http.server 8000
```

Lalu kunjungi `http://localhost:8000`.

## GitHub Pages

Deployment otomatis dikonfigurasi melalui `.github/workflows/deploy-pages.yml`. Di pengaturan repository, pilih **Settings → Pages → Build and deployment → Source: GitHub Actions**.

Setelah deployment berhasil, alamat situs yang diharapkan:

https://ajatikusumah.github.io/Zoonosis-and-Emerging-Infectious-Diseases-Dashboard/
