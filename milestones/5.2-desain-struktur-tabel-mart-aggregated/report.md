# Report — Milestone 5.2: Desain Struktur Tabel Mart Aggregated

Milestone ini berbasis **dokumen/desain**. Desain mart agregat disusun sebagai kontrak implementasi dbt dengan fokus pada grain yang jelas, filter analitik, dan pencegahan PII granular.

## 1. Ringkasan Hasil

**Status akhir: Completed.** `docs/07-mart-aggregated/DataSchema-mart-aggregated.md` mendokumentasikan rancangan awal 45 fact dan 27 dimension dengan grain eksplisit, kebutuhan partisi/cluster, serta keputusan PII. Implementasi M5.3 kemudian merasionalisasi struktur menjadi 49 fact dan 27 dimension (76 tabel) untuk merefleksikan grain aktual dan pemecahan beberapa metrik.

Desain ini menautkan setiap kebutuhan M5.1 ke tabel agregat, tanpa membawa identitas tamu atau informasi kontak ke mart. Perubahan tambahan `dim_employee.property_id` yang belum ada pada desain awal diselesaikan secara resmi pada M5.7.

## 2. Kriteria Keberhasilan vs Bukti Nyata

| Kriteria | Bukti nyata |
| --- | --- |
| Kebutuhan prioritas dan pola khusus memiliki desain tabel | Kebutuhan M5.1 diterjemahkan ke fact/dimension beserta grain dan sumbernya. |
| Kolom filter penting dipertimbangkan | Property, department, dan waktu dinyatakan sebagai dasar partition/cluster sesuai pola akses analitik. |
| Grain mencegah ambiguitas agregasi | Grain fact dinyatakan eksplisit sehingga implementasi dapat menguji duplikasi dan relasi. |
| PII dikendalikan sejak desain | Hanya `dim_employee.full_name`, nama tier loyalitas, dan nama kelompok kebangsaan yang diizinkan; kontak tamu dan guest identifier tidak dibawa. |

## 3. Cara Kerja dan Arsitektur

Tidak ada sistem runtime baru pada milestone ini. Desain dibuat dengan memetakan kebutuhan terkonsolidasi ke dimension bersama dan fact per domain, kemudian menilai grain, sumber, filter, serta eksposur PII sebelum SQL ditulis.

Keputusan pentingnya adalah memilih mart yang sepenuhnya agregat. Dengan itu, model yang kelak memerlukan data per-entitas—misalnya feedback ML—harus hadir sebagai fact agregat tersendiri, bukan menurunkan data granular ke mart.

## 4. Perubahan dari Plan

Rancangan awal menyebut 45 fact dan 27 dimension. Saat implementasi, beberapa grain yang semula terlalu lebar dipecah agar mencerminkan data nyata; hasilnya 49 fact dan 27 dimension. Ini merupakan penyempurnaan desain terhadap bukti sumber, bukan perluasan PII atau perubahan tujuan mart.

## 5. Keterbatasan dan Item Provisional

- Ambang SLA dan aturan pengelompokan kebangsaan membutuhkan kebijakan/validasi operasional tersendiri.
- `dim_employee.property_id` belum tercakup pada desain awal; M5.7 menambahkannya setelah kebutuhan aktual dicatat di backlog.
- Ketentuan append-only pace booking perlu disesuaikan dengan batas BigQuery Sandbox dan data sintetis statis.

## 6. Follow-up

- M5.3 mengimplementasikan desain ini dan menerbitkan kamus data serta metadata aktual.
- M5.4 menambah fact feedback ML agregat secara provisional.
- M5.7 menutup perubahan dimensi karyawan melalui jalur perubahan cakupan yang terdokumentasi.
