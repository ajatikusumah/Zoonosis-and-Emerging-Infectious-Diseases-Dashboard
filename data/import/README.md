# Impor data terotorisasi

Folder ini menerima data kejadian/laporan agregat dan sudah dide-identifikasi dalam format CSV atau Excel (`.xlsx`). GitHub Pages dan repository ini bersifat **publik**. Jangan pernah mengunggah data individu, nama, nomor identitas, alamat rinci, nomor telepon, surel, rekam medis, kredensial, atau data mentah yang dibatasi.

## Cara memakai

1. Unduh `template.csv` atau `template.xlsx`.
2. Salin file dengan nama baru; jangan mengubah file template.
3. Isi satu rekaman per baris pada sheet `Import` atau pada CSV.
4. Biarkan `publish=false` selama penyiapan dan penelaahan.
5. Setelah data dipastikan agregat, de-identifikasi, berizin, dan layak publik, ubah baris yang disetujui menjadi `publish=true`.
6. Unggah file ke folder `data/import/`. Workflow otomatis memproses unggahan baru segera; pemeriksaan cadangan berjalan setiap 2 hari.
7. Periksa `data/import-validation.json` bila ada baris yang dilewati.

Baris hanya dipublikasikan bila `publish` bernilai `true`, `1`, `yes`, atau `ya`. Nilai lain dilewati. File yang memiliki kolom di luar skema ditolak seluruhnya agar kolom sensitif tidak ikut masuk tanpa sengaja.

## Kolom wajib

- `publish`: persetujuan eksplisit untuk publikasi.
- `record_type`: `event` atau `report`.
- `evidence`: `confirmed` atau `rumor`.
- `disease`, `title`, `location`, `published`.
- `source_id`: pengenal konsisten berisi huruf kecil/angka/titik/garis bawah/tanda hubung.
- `source_name`.
- `source_level`: `Lokal`, `Nasional`, `Regional`, atau `Global`.
- `access_level`: `public`, `restricted`, `licensed`, `institutional`, atau `internal`.

`published` dan `updated` memakai ISO 8601, misalnya `2026-08-15` atau `2026-08-15T09:00:00Z`. `iso3` memakai kode negara tiga huruf. Jika koordinat kosong tetapi `iso3` dikenal, dashboard memakai centroid negara dan menandai presisi `country`. Angka dampak boleh kosong; kosong berarti tidak tersedia, bukan nol.

## Konfirmasi dan rumor

- Gunakan `confirmed` hanya untuk rekaman yang didukung sumber resmi/primer sesuai prosedur organisasi.
- Gunakan `rumor` untuk media, laporan komunitas, atau sinyal yang belum diverifikasi.
- `access_level` menjelaskan tingkat akses sumber asal, bukan izin untuk membuka data mentah. `publish=true` tetap menyatakan bahwa **rekaman agregat pada baris tersebut** disetujui untuk tampil di situs publik.

## Validasi otomatis

Pipeline memeriksa skema, kolom wajib, tanggal, koordinat, bilangan non-negatif, status bukti, tingkat sumber, tingkat akses, dan URL. Baris yang gagal dilewati tanpa menghentikan sumber lain. Laporan validasi tidak menyalin nilai baris sehingga mengurangi risiko data sensitif muncul dalam pesan kesalahan.

## Data yang harus tetap “behind the door”

Jangan unggah data rahasia/restricted ke repository ini, termasuk dengan `publish=false`, karena file sumber tetap dapat dibaca publik. Untuk data tersebut gunakan gateway privat terpisah (misalnya database/API dengan autentikasi) yang hanya mengekspor agregat yang telah disetujui. Gateway sebaiknya:

1. menyimpan data mentah di sistem privat;
2. menerapkan kontrol akses dan audit log;
3. melakukan de-identifikasi/agregasi;
4. mengirim hanya kolom pada skema ini setelah persetujuan publikasi;
5. menyimpan token sebagai GitHub Actions Secret, tidak di HTML atau repository.

Integrasi gateway privat tidak diaktifkan pada repository ini karena memerlukan pilihan layanan, endpoint, dan kredensial organisasi.
