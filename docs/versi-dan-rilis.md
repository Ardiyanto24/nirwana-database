# Versi dan rilis

## Sumber versi

Versi resmi repositori ini ada di [`VERSION`](../VERSION). Versi tersebut
mengikuti Semantic Versioning (`MAJOR.MINOR.PATCH`):

- `MAJOR` untuk perubahan yang memutus kontrak pengguna atau operasional.
- `MINOR` untuk kemampuan baru yang tetap kompatibel.
- `PATCH` untuk perbaikan kompatibel atau dokumentasi rilis.

`warehouse/dbt_project.yml` dan baris versi di README adalah deklarasi turunan
yang wajib sama dengan `VERSION`. Jalankan pemeriksaan berikut sebelum membuat
rilis:

```powershell
python scripts/release/check_version.py
```

GitHub Actions menjalankan pemeriksaan yang sama pada setiap pull request dan
push ke `main`.

Folder `api/` dan `web/` tidak tercakup dalam kontrak ini karena keduanya
dideploy dari repositori terpisah; lihat `milestones/1.6-public-monitoring-api/decisions.md`.

## Proses rilis

1. Tentukan kenaikan versi sesuai dampaknya, lalu ubah `VERSION` dan
   `warehouse/dbt_project.yml` bersamaan.
2. Perbarui baris versi pada README serta tambahkan entri berorientasi pengguna
   di [`CHANGELOG.md`](../CHANGELOG.md), dikelompokkan sebagai Added, Changed,
   Fixed, Deprecated, Removed, atau Security bila relevan.
3. Jalankan `python scripts/release/check_version.py` dan verifikasi pipeline
   terkait perubahan tersebut.
4. Commit perubahan rilis. Setelah commit telah berada di `main`, buat tag
   beranotasi dengan prefix `v`, misalnya:

   ```powershell
   git tag -a v1.0.0 -m "Release 1.0.0"
   git push origin v1.0.0
   ```

Tag menunjuk ke commit rilis yang tidak berubah, sehingga versi yang sedang
dijalankan dapat ditelusuri kembali ke source dan changelog yang tepat.
