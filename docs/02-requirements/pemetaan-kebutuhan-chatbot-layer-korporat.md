# Pemetaan Kebutuhan AI Chatbot — Layer Korporat

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dokumen induk** | `rancangan-arsitektur-data-platform-elt.md` |
| **Dokumen terkait** | `rancangan-rbac-ai-chatbot.md`, `role_permissions_chatbot_v2.csv`, `pemetaan-kebutuhan-chatbot-layer-staff.md`, `pemetaan-kebutuhan-chatbot-layer-manager.md` |
| **Tujuan dokumen** | Memetakan kebutuhan tanya-jawab AI Chatbot untuk 5 posisi Korporat, sebagai masukan cakupan mart_aggregated |
| **Metodologi** | Role-play per posisi → audit kebutuhan → verifikasi ke DataSchema.md → audit superset terhadap Manager di bawahnya (termasuk efek berantai) |
| **Status** | Layer Korporat selesai. Seluruh 20 persona (7 Staff + 8 Manager + 5 Korporat) telah dipetakan, dengan RBAC final teraudit penuh di seluruh hierarki |

---

## Cara Membaca Dokumen Ini — Prinsip Superset

Setiap posisi Korporat mewarisi seluruh kebutuhan dari Manager (atau beberapa Manager sekaligus) yang berada dalam cakupan domainnya (satu kalimat referensi di awal tiap posisi, bukan disalin ulang). Badan tiap posisi hanya memuat kebutuhan tambahan yang khas di level Korporat: umumnya berupa benchmarking/ranking antar 5 properti, yang secara konsisten ditolak di layer Manager (own_property).

---

## 1. CEO

RBAC: Semua 7 domain + properties_ref + employees_directory + guests_pii + guests_profile, all_properties

Mewarisi seluruh kebutuhan dari General Manager dan keempat Corporate Director lainnya (lihat kebutuhan tambahan masing-masing di dokumen ini dan dokumen layer Manager). Berikut kemampuan tambahan yang khas CEO:

### Role-Play (Tambahan)

Pengawasan penuh lintas grup — akses terluas di seluruh sistem. Berbeda dari GM (lintas domain tapi satu properti), CEO lintas domain dan lintas properti sekaligus. Pertanyaan tambahan cenderung ringkasan strategis lintas grup, bukan detail operasional harian.

Pertanyaan tambahan yang mungkin diajukan: ringkasan performa grup bulan ini (properti mana paling kuat/lemah), GOP margin tiap properti dibanding rata-rata grup, properti mana yang butuh perhatian minggu ini, turnover rate tertinggi di properti mana, tren revenue grup YoY, detail spesifik satu tamu tertentu (komplain besar), isi tabel role_permissions untuk audit internal.

### Audit dan Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| Ringkasan performa dan benchmarking antar properti | Semua domain tersedia dengan access_scope=all_properties | Dalam cakupan, inilah yang membedakan CEO dari GM |
| GOP margin tiap properti vs rata-rata grup | financial_summary.gop, property_id, agregasi lintas 5 properti | Dalam cakupan |
| Turnover rate tertinggi antar properti | employees.status, department, property_id | Dalam cakupan |
| Tren revenue grup YoY | financial_summary.departmental_revenue, agregasi lintas properti | Dalam cakupan |
| Detail spesifik satu tamu (komplain besar) | guests, CEO satu-satunya dengan guests_pii+guests_profile all_properties | Dalam cakupan, kasus jarang/pengecualian |
| Isi tabel role_permissions untuk audit internal | role_permissions sengaja tidak diberikan ke peran mana pun, termasuk CEO | Ditolak — kunci sistem tidak boleh dibaca lewat jalur yang ia atur sendiri |
| Jejak audit siapa mengakses data apa | Domain berbeda (audit log), tidak termasuk 7 domain data operasional | Di luar cakupan dokumen ini |

### Kebutuhan Data Tambahan

1. Benchmarking/ranking metrik apa pun (GOP, okupansi, turnover, dst) antar 5 properti
2. Ringkasan performa grup lintas seluruh domain sekaligus
3. Tren YoY tingkat grup
4. Akses granular ke satu tamu spesifik jika diperlukan (kasus jarang, bukan pola rutin)

Di luar cakupan (ditolak RBAC, prinsip permanen): isi tabel role_permissions

Di luar cakupan dokumen ini: jejak audit akses

---

## 2. Corporate Finance Director

RBAC: financial (mencakup payroll) + reservation (direvisi) + properties_ref + employees_directory, all_properties

Mewarisi seluruh kebutuhan Finance Manager. Berikut kebutuhan tambahan khusus Corporate Finance Director:

### Role-Play (Tambahan)

Mengawasi laporan keuangan seluruh properti grup — kebutuhan tambahan berupa konsolidasi dan benchmarking lintas 5 properti, plus overhead korporat yang tidak ada di level properti (beda dari Finance Manager yang satu properti).

Pertanyaan tambahan yang mungkin diajukan: GOP margin tiap properti (ranking tertinggi ke terendah), total revenue/expense grup bulan ini, overhead korporat, payroll grup breakdown per properti, labor cost sebagai persen revenue antar properti, service charge pool lintas properti mana yang paling menyimpang.

### Audit dan Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| GOP margin ranking antar properti | financial_summary.gop, filter department='Overall', all_properties memungkinkan ranking | Dalam cakupan |
| Total revenue/expense grup | Agregasi financial_summary lintas 5 properti | Dalam cakupan |
| Overhead korporat | financial_summary.department='Corporate Overhead', terverifikasi ada sebagai nilai department terpisah dari 'Overall'. Belum pernah dibahas di layer manapun sebelumnya | Temuan baru, ditambahkan sebagai metrik tersendiri, relevan hanya di level all_properties |
| Payroll grup breakdown per properti | payroll x employees.property_id | Dalam cakupan |
| Service charge pool vs okupansi, lintas properti | payroll.service_charge x daily_occupancy.occupancy_rate. Finance Manager sudah punya metrik ini (hasil revisi reservation), awalnya tidak diwariskan ke Director karena domain reservation belum dimiliki | Revisi RBAC: ditambahkan reservation, agar metrik yang sudah dimiliki Finance Manager tetap tersedia bagi atasannya, kini dengan kemampuan membandingkan properti mana yang paling menyimpang |

### Kebutuhan Data Tambahan

1. GOP dan GOP margin per properti, ranking antar 5 properti
2. Total revenue/expense/profit grup, agregasi lintas 5 properti
3. Overhead korporat (department='Corporate Overhead')
4. Undistributed expense per properti, perbandingan antar properti
5. Total komponen payroll per properti, MoM
6. Labor cost sebagai persen revenue, dibanding antar properti
7. Service charge pool dan korelasinya dengan occupancy rate, per properti, serta properti mana yang polanya paling menyimpang

---

## 3. Corporate HR Director

RBAC: hr + properties_ref + employees_directory, all_properties

Mewarisi seluruh kebutuhan HR Manager. Berikut kebutuhan tambahan khusus Corporate HR Director:

### Role-Play (Tambahan)

Mengawasi kepegawaian seluruh properti grup — kebutuhan tambahan berupa kebijakan SDM tingkat grup, benchmarking turnover antar properti (beda dari HR Manager yang satu properti).

Pertanyaan tambahan yang mungkin diajukan: turnover rate tertinggi di properti mana, attendance rate rata-rata grup (properti mana paling rendah), skor performa rata-rata grup dan trennya, jumlah karyawan aktif seluruh grup.

### Audit dan Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| Turnover rate tertinggi antar properti | employees.status, property_id, department, all_properties memungkinkan ranking | Dalam cakupan |
| Attendance rate rata-rata grup | staff_shifts.status, agregasi lintas property_id | Dalam cakupan |
| Skor performa rata-rata grup | employee_performance.score, agregasi lintas properti | Dalam cakupan |
| Jumlah karyawan aktif seluruh grup | employees.status='active', agregasi lintas properti | Dalam cakupan |
| Payroll grup | Corporate HR Director tidak memiliki domain financial | Di luar cakupan RBAC, murni domain Corporate Finance Director |

Tidak ditemukan gap dokumentasi maupun gap RBAC — seluruh kebutuhan granular HR Manager (jam lembur, keterlambatan individu, watchlist) sudah otomatis diwariskan karena domainnya identik (hr), hanya diperluas ke all_properties.

### Kebutuhan Data Tambahan

1. Turnover rate per properti/departemen, ranking antar 5 properti
2. Attendance rate rata-rata per properti, per periode
3. Skor performa rata-rata per properti/departemen, tren antar periode
4. Jumlah karyawan aktif per properti/seluruh grup

Di luar cakupan (ditolak RBAC): payroll grup, murni domain Corporate Finance Director

---

## 4. Corporate Operations Director

RBAC: facility + fnb + spa_event + reservation (direvisi) + properties_ref + employees_directory (direvisi) + guests_pii (direvisi), all_properties

Mewarisi seluruh kebutuhan F&B Manager, Housekeeping Manager, Maintenance Manager, dan Spa & Event Manager sekaligus. Berikut kebutuhan tambahan khusus Corporate Operations Director:

### Role-Play (Tambahan)

Mengawasi operasional non-finansial seluruh properti grup — gabungan 4 domain Manager lintas grup. Kebutuhan tambahan berupa benchmark antar 5 properti untuk setiap metrik yang sudah dimiliki keempat Manager tersebut.

Pertanyaan tambahan yang mungkin diajukan: benchmark maintenance cost antar properti, tiket per kamar per tahun dinormalisasi usia gedung, benchmark revenue F&B antar properti, benchmark utilisasi venue antar properti, benchmark waste ratio antar properti.

### Audit dan Verifikasi

Audit sistematis menemukan bahwa kebutuhan Corporate Operations Director awalnya jauh lebih dangkal dari gabungan 4 Manager yang seharusnya dia awasi — bukan karena domainnya sempit, tapi karena banyak item yang belum dituliskan sebagai kebutuhan tambahan eksplisit.

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| Benchmark maintenance cost & tiket per kamar per tahun | maintenance_tickets.cost, properties.opening_date (untuk normalisasi usia gedung) — terverifikasi ada | Dalam cakupan, ini levelnya untuk benchmark yang ditolak di Maintenance Manager |
| Benchmark revenue F&B, food cost, waste ratio, walk-in ratio antar properti | fnb_transactions, fnb_waste_log, lintas 5 properti | Ditambahkan sebagai benchmark eksplisit, sebelumnya sebagian tidak dituliskan |
| Benchmark distribusi status kamar, delayed rate housekeeping antar properti | rooms.status, housekeeping_log, lintas properti | Ditambahkan, sebelumnya tidak dituliskan sama sekali |
| Benchmark SLA breach rate, kamar tiket berulang antar properti | maintenance_tickets, lintas properti | Ditambahkan |
| Benchmark revenue spa & event, cancellation rate, tren layanan antar properti | spa_bookings, event_bookings, lintas properti | Ditambahkan |
| **Capture rate & delayed rate vs okupansi, lintas grup** | Butuh domain reservation — awalnya tidak dimiliki, padahal F&B Manager dan Housekeeping Manager (bawahannya) sudah memiliki via revisi sebelumnya | **Revisi RBAC**: ditambahkan reservation |
| **Nama staff/teknisi untuk workload lintas grup** | Butuh employees_directory — awalnya tidak dimiliki, padahal seluruh 4 Manager sudah memilikinya | **Revisi RBAC**: ditambahkan employees_directory |
| Total maintenance/F&B cost sebagai bagian GOP | Butuh financial_summary, domain financial, tidak dimiliki | Tetap di luar cakupan — murni domain Corporate Finance Director |

### Kebutuhan Data Tambahan

**Benchmark antar 5 properti untuk seluruh metrik yang diwarisi dari 4 Manager**, termasuk:
1. Revenue per outlet, food cost ratio, waste ratio, capture rate, walk-in ratio F&B — benchmark antar properti
2. Distribusi status kamar, durasi pembersihan, delayed rate housekeeping (termasuk vs okupansi) — benchmark antar properti
3. Jumlah tiket, SLA breach rate, cost maintenance, kamar tiket berulang, tiket per kamar per tahun dinormalisasi usia gedung (properties.opening_date) — benchmark antar properti
4. Revenue spa & event, utilisasi venue, cancellation rate, tren layanan spa, walk-in ratio spa — benchmark antar properti
5. Jumlah staff/teknisi aktif dan workload per departemen, lintas properti

Di luar cakupan (ditolak RBAC): implikasi finansial/GOP dari operasional — murni domain Corporate Finance Director

---

## 5. Corporate Revenue Director

RBAC: reservation + financial (mencakup payroll) + properties_ref + guests_profile + guests_pii (direvisi berantai), all_properties

Mewarisi seluruh kebutuhan Revenue Manager. Berikut kebutuhan tambahan khusus Corporate Revenue Director:

### Role-Play (Tambahan)

Mengawasi revenue dan tamu seluruh properti grup, bertanggung jawab atas prediksi guest churn — kebutuhan tambahan berupa benchmark antar 5 properti, dan analisis dampak pricing terhadap GOP (dimungkinkan oleh kombinasi domain reservation+financial yang unik).

Pertanyaan tambahan yang mungkin diajukan: benchmark okupansi/ADR/RevPAR antar properti, benchmark cancellation rate, repeat guest rate grup, dampak strategi pricing terhadap GOP margin properti.

### Audit dan Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| Benchmark okupansi/ADR/RevPAR, cancellation rate, repeat guest rate | daily_occupancy, bookings, lintas 5 properti | Dalam cakupan |
| Dampak pricing terhadap GOP | pricing_history (reservation) x financial_summary.gop (financial), keduanya dimiliki | Dalam cakupan, kombinasi domain unik satu-satunya di layer Korporat |
| Breakdown pricing manual/promo/dynamic-AI, room type paling menguntungkan, lead time booking, lintas grup | Ada di Revenue Manager sebagai item eksplisit, sebelumnya tidak dituliskan untuk Director meski domainnya identik | Ditambahkan — gap dokumentasi murni, sudah dalam cakupan RBAC sejak awal |
| **Kontak tamu untuk kasus eskalasi tingkat grup** | Revenue Manager kini memiliki guests_pii (hasil revisi), Director sebagai atasannya di domain reservation yang sama awalnya tidak — akan menjadi lebih sempit dari bawahannya jika tidak ikut direvisi | **Revisi RBAC**: ditambahkan guests_pii (all_properties), menutup rantai superset Front Office Staff → Revenue Manager → Corporate Revenue Director |

### Kebutuhan Data Tambahan

1. Benchmark okupansi, ADR, RevPAR antar 5 properti
2. Benchmark cancellation rate antar properti
3. Repeat guest rate grup
4. Dampak strategi pricing terhadap GOP margin — cross-domain reservation+financial
5. Breakdown pricing (reason), room type paling menguntungkan, lead time booking — lintas grup
6. Kontak tamu untuk kasus yang dieskalasi ke tingkat grup

---

## Ringkasan Layer Korporat

| Posisi | Ciri khas dibanding Manager setara |
|---|---|
| CEO | Superset penuh dari GM + 4 Director, satu-satunya dengan akses penuh 7 domain + 4 kelompok granular. Tetap tidak dapat role_permissions |
| Corporate Finance Director | Superset penuh Finance Manager (kini termasuk reservation), plus metrik baru Corporate Overhead |
| Corporate HR Director | Superset penuh HR Manager sejak awal, tanpa perlu revisi RBAC |
| Corporate Operations Director | Setelah revisi, superset penuh dari 4 Manager sekaligus (F&B, Housekeeping, Maintenance, Spa & Event) |
| Corporate Revenue Director | Superset penuh Revenue Manager, plus kombinasi domain unik (reservation+financial) |

Prinsip yang ditegakkan: AI Chatbot menggantikan rantai eskalasi manual antar layer organisasi. Siapa pun di posisi lebih tinggi untuk domain yang sama wajib memiliki seluruh akses granular yang dimiliki bawahannya — bukan hanya versi ringkasan/benchmark-nya. Audit ini dilakukan dua arah (Director superset Manager, Manager superset Staff) dan diverifikasi tidak ada mata rantai bocor lewat pemeriksaan terprogram atas seluruh 20 peran sekaligus, termasuk memastikan CEO dan General Manager tetap superset dari seluruh peran di bawahnya setelah setiap revisi.

---

## Penutup: Seluruh 20 Persona Selesai Dipetakan dan Diverifikasi Bebas Pelanggaran Superset

RBAC final (`role_permissions_chatbot_v2.csv`, 77 baris) telah diverifikasi terprogram bebas dari pelanggaran superset di keempat jalur pemeriksaan: Staff→Manager, Manager→Corporate Director, Manager→General Manager, dan seluruh peran→CEO. Total revisi RBAC yang terjadi selama seluruh proses pemetaan:

1. HR Staff dan Finance Staff mendapat tambahan employees_directory
2. Spa & Event Staff mendapat tambahan guests_pii
3. F&B Manager, Housekeeping Manager, Finance Manager mendapat tambahan reservation
4. payroll dikonfirmasi termasuk cakupan domain financial tanpa pemecahan granular tersendiri
5. Corporate Finance Director mendapat tambahan reservation
6. Corporate Operations Director mendapat tambahan employees_directory dan reservation
7. Revenue Manager dan Spa & Event Manager mendapat tambahan guests_pii
8. Corporate Revenue Director mendapat tambahan guests_pii (revisi berantai dari poin 7)
9. Corporate Operations Director mendapat tambahan guests_pii (revisi berantai dari revisi Spa & Event Manager pada poin 7)
10. General Manager mendapat tambahan guests_pii dan guests_profile (revisi berantai dari poin 7, ditemukan lewat audit terprogram penuh)

---

*Dokumen ini merupakan hasil pemetaan kebutuhan AI Chatbot untuk layer Korporat, dengan format ringkas (kebutuhan tambahan saja, warisan via referensi) dan setiap klaim data terverifikasi terhadap DataSchema.md. Bersama dokumen layer Staff dan Manager, ketiganya menjadi basis lengkap untuk menentukan cakupan mart_aggregated bagi konsumen AI Chatbot.*
