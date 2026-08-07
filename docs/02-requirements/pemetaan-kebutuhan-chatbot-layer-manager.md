# Pemetaan Kebutuhan AI Chatbot — Layer Manager

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dokumen induk** | `rancangan-arsitektur-data-platform-elt.md` |
| **Dokumen terkait** | `rancangan-rbac-ai-chatbot.md`, `role_permissions_chatbot_v2.csv`, `pemetaan-kebutuhan-chatbot-layer-staff.md` |
| **Tujuan dokumen** | Memetakan kebutuhan tanya-jawab AI Chatbot untuk 8 posisi Manager, sebagai masukan cakupan `mart_aggregated` |
| **Metodologi** | Role-play per posisi → audit kebutuhan → verifikasi ke `DataSchema.md` → audit superset terhadap Staff di bawahnya |
| **Status** | Layer Manager selesai, termasuk seluruh revisi RBAC yang muncul dari proses pemetaan |

---

## Cara Membaca Dokumen Ini — Prinsip Superset

Setiap posisi Manager mewarisi seluruh kebutuhan dari Staff yang berada dalam cakupan domainnya (dinyatakan sebagai satu kalimat referensi di awal tiap posisi, bukan disalin ulang). Badan tiap posisi hanya memuat kebutuhan tambahan yang khas di level Manager — biasanya berupa: performa seluruh tim (bukan cuma individu), tren antar periode, dan metrik yang butuh data lintas domain.

Perbedaan karakter dari Staff: Manager mengakses domainnya secara own_property penuh (bukan own_subject/data dirinya sendiri seperti sebagian besar Staff). Ini konsisten dengan prinsip AI Chatbot sebagai pengganti rantai eskalasi manual — Manager harus bisa menjawab sendiri apa pun yang bisa dijawab Staff-nya, ditambah kemampuan yang memang khas perannya.

---

## 1. Revenue Manager

RBAC: reservation + properties_ref + guests_profile + guests_pii (direvisi, own_property)

Mewarisi seluruh kebutuhan Front Office Staff (lihat dokumen layer Staff). Berikut kebutuhan tambahan khusus Revenue Manager:

### Role-Play (Tambahan)

Bertanggung jawab atas harga dan okupansi propertinya — kebutuhan tambahan melibatkan tren, perbandingan, dan strategi harga (harian s.d. bulanan), berbeda dari Front Office Staff yang murni lookup real-time.

Pertanyaan tambahan yang mungkin diajukan: okupansi/ADR/RevPAR dan trennya, channel penyumbang revenue terbesar, breakdown penyesuaian harga (manual/promo/dynamic-pricing), cancellation rate per channel, jumlah booking tamu loyalty tier tinggi, room type paling menguntungkan, rata-rata lead time booking, pace booking untuk 2 minggu ke depan.

### Audit dan Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| Okupansi/ADR/RevPAR + tren | daily_occupancy.occupancy_rate, adr, revpar, terverifikasi ada | Dalam cakupan |
| Revenue per channel | bookings.booking_channel, total_amount, terverifikasi ada | Dalam cakupan |
| Breakdown pricing manual/promo/dynamic-AI | pricing_history.reason, base_rate, applied_rate, terverifikasi ada | Dalam cakupan |
| Cancellation rate per channel | bookings.status='cancelled', booking_channel, terverifikasi ada | Dalam cakupan |
| Room type paling menguntungkan | bookings.room_type, total_amount, terverifikasi ada | Dalam cakupan |
| Lead time booking | bookings.booking_date, check_in_date, terverifikasi ada | Dalam cakupan |
| Pace booking (snapshot "as of hari ini") | Data pendukung ada, tapi sifatnya snapshot harian yang berubah, bukan fakta historis biasa | Dikeluarkan dari cakupan reguler, butuh mekanisme snapshot terpisah |
| Komisi OTA / target okupansi | Tidak ada kolom komisi di bookings; tidak ada tabel target di skema manapun | Gap data sumber |
| Kontak tamu untuk retensi langsung | guests.email, guests.phone. Audit superset menemukan Front Office Staff sudah memiliki guests_pii, Manager domain sama awalnya tidak | Revisi RBAC: ditambahkan guests_pii, agar dapat menindaklanjuti langsung (mis. tawaran retensi tamu loyalty tinggi) tanpa lewat Staff |

### Kebutuhan Data Tambahan

1. Okupansi, ADR, RevPAR harian s.d. bulanan, dengan pembanding MoM
2. Revenue dan jumlah booking per channel, per periode
3. Breakdown pricing (reason), rata-rata deviasi applied_rate dari base_rate
4. Cancellation rate dan no-show rate per channel, per periode
5. Jumlah booking per loyalty_tier, per periode (agregat, beda dari lookup satu tamu di Staff)
6. Revenue per room_type, per periode
7. Rata-rata/median lead time booking

Dikeluarkan dari cakupan reguler: pace booking

Gap data sumber: komisi OTA, target/budget okupansi

---

## 2. F&B Manager

RBAC: fnb + reservation (direvisi) + properties_ref + employees_directory (own_property)

Mewarisi seluruh kebutuhan F&B Staff. Berikut kebutuhan tambahan khusus F&B Manager:

### Role-Play (Tambahan)

Mengelola outlet, menu, resep, dan stok F&B propertinya — kebutuhan tambahan berupa analisis margin, tren, dan kesehatan operasional lintas outlet, berbeda dari F&B Staff yang lookup real-time per shift.

Pertanyaan tambahan yang mungkin diajukan: revenue tiap outlet dan trennya, food cost ratio realisasi vs target, waste ratio per outlet, capture rate tamu inhouse, walk-in ratio dan trennya, item menu paling untung/rugi, daftar staf outlet, tren harga bahan baku.

### Audit dan Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| Revenue per outlet + tren | fnb_transactions.total_price, outlet_id, terverifikasi ada | Dalam cakupan |
| Food cost ratio vs target | fnb_transactions x recipe_bom x ingredient_price_history, cross-table dalam domain fnb | Dalam cakupan |
| Waste ratio dan breakdown alasan | fnb_waste_log.quantity_wasted, reason, terverifikasi ada | Dalam cakupan |
| Capture rate tamu inhouse | fnb_transactions.customer_type='inhouse' x populasi tamu menginap (domain reservation), awalnya tidak dimiliki | Revisi RBAC: ditambahkan reservation, khusus untuk metrik lintas domain ini |
| Walk-in ratio dan tren | fnb_transactions.customer_type='walk-in', terverifikasi ada, murni domain fnb | Dalam cakupan |
| Item paling untung/rugi | Revenue dari fnb_transactions, cost dari recipe_bom x ingredient_price_history | Dalam cakupan |
| Daftar staf outlet | employees.full_name, department='F&B', dalam cakupan employees_directory | Dalam cakupan |
| Tren harga bahan baku | ingredient_price_history.unit_cost, date, terverifikasi ada | Dalam cakupan |

### Kebutuhan Data Tambahan

1. Revenue per outlet, MoM dan YoY
2. Food cost ratio realisasi vs target, per kategori/outlet, cross-table fnb_transactions x recipe_bom x ingredient_price_history
3. Waste ratio dan breakdown reason, per outlet
4. Walk-in ratio dan tren, per outlet (agregat, beda dari lookup transaksi per shift di Staff)
5. Capture rate tamu inhouse, cross-table fnb_transactions x daily_occupancy/bookings
6. Revenue dan margin per item menu, per outlet
7. Daftar staf F&B propertinya
8. Tren harga bahan baku
9. Inventory di bawah threshold, agregat lintas outlet

---

## 3. Housekeeping Manager

RBAC: facility + reservation (direvisi) + properties_ref + employees_directory (own_property)

Mewarisi seluruh kebutuhan Housekeeping Staff. Berikut kebutuhan tambahan khusus Housekeeping Manager:

### Role-Play (Tambahan)

Mengelola kamar, kebersihan, dan tim housekeeping propertinya — kebutuhan tambahan berupa performa seluruh tim (bukan cuma dirinya seperti Staff) dan tren efisiensi operasional.

Pertanyaan tambahan yang mungkin diajukan: distribusi status kamar saat ini, durasi rata-rata pembersihan per tipe kamar, delayed rate dan siapa yang paling sering delayed, performa staff dibanding rata-rata tim, jumlah staff aktif di tim, housekeeping efficiency dibanding bulan lalu, delayed rate terkait okupansi.

### Audit dan Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| Distribusi status kamar | rooms.status, terverifikasi ada | Dalam cakupan |
| Durasi pembersihan per tipe kamar (agregat tim) | housekeeping_log.cleaning_start_time/cleaning_end_time, join rooms.room_type | Dalam cakupan |
| Delayed rate dan performa seluruh staff (bukan cuma dirinya) | housekeeping_log.status='delayed', staff_id. Manager boleh lihat semua staff timnya, beda dari Staff yang hanya dirinya sendiri | Dalam cakupan |
| Jumlah staff aktif di tim | employees.department='Housekeeping', status, dalam cakupan employees_directory | Dalam cakupan |
| Housekeeping efficiency vs bulan lalu | Agregasi housekeeping_log per bulan | Dalam cakupan |
| Delayed rate terkait okupansi | Butuh daily_occupancy (domain reservation), awalnya tidak dimiliki | Revisi RBAC: ditambahkan reservation |

### Kebutuhan Data Tambahan

1. Distribusi status kamar saat ini, seluruh properti
2. Durasi rata-rata pembersihan per tipe kamar, dibanding baseline, agregat tim
3. Delayed rate, per periode, agregat tim
4. Durasi pembersihan per staff (untuk seluruh staff timnya, bukan cuma dirinya), dibanding rata-rata tim
5. Jumlah staff aktif departemen Housekeeping
6. Tren housekeeping efficiency (durasi dan delayed rate) MoM
7. Delayed rate terkait okupansi, cross-table housekeeping_log x daily_occupancy

---

## 4. Maintenance Manager

RBAC: facility + properties_ref + employees_directory (own_property)

Mewarisi seluruh kebutuhan Maintenance Staff. Berikut kebutuhan tambahan khusus Maintenance Manager:

### Role-Play (Tambahan)

Mengelola tiket, kamar, dan jadwal perawatan propertinya — kebutuhan tambahan berupa SLA compliance, cost, dan pola kerusakan berulang untuk keputusan prioritas dan anggaran.

Pertanyaan tambahan yang mungkin diajukan: jumlah tiket baru per area/jenis masalah, SLA breach rate per prioritas, total cost maintenance dan breakdown part, kamar dengan tiket berulang, teknisi paling banyak menangani tiket, jumlah teknisi aktif.

### Audit dan Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| Jumlah tiket per area/jenis (agregat properti) | maintenance_tickets.facility_area, issue_type, terverifikasi ada | Dalam cakupan |
| SLA breach rate | reported_date, resolved_date, priority, terverifikasi ada | Dalam cakupan, threshold SLA menunggu keputusan (gap parameter) |
| Total cost dan breakdown part | maintenance_tickets.cost, terverifikasi ada (kolom v0.4) | Dalam cakupan |
| Kamar tiket berulang | maintenance_tickets.room_id, agregasi per kamar | Dalam cakupan |
| Workload seluruh teknisi (bukan cuma dirinya) | assigned_staff_id, labor_hours, dalam cakupan karena Manager, beda dari Staff yang hanya dirinya | Dalam cakupan |
| Benchmark antar properti | Butuh access_scope=all_properties, Manager hanya own_property | Di luar cakupan RBAC, levelnya Corporate Operations Director |
| Jumlah teknisi aktif | employees.department, status | Dalam cakupan |

### Kebutuhan Data Tambahan

1. Jumlah tiket baru per facility_area/issue_type, per periode, agregat properti
2. SLA breach rate per priority, per periode
3. Total cost maintenance, breakdown dengan/tanpa parts_replaced, per periode
4. Kamar dengan tiket berulang (recurring issue), per periode
5. Jumlah tiket dan total labor_hours per teknisi, untuk seluruh timnya
6. Jumlah teknisi aktif di departemen Facility/Maintenance

Di luar cakupan (ditolak RBAC): benchmarking antar properti

Menunggu keputusan lanjutan: threshold SLA per priority

---

## 5. Spa & Event Manager

RBAC: spa_event + properties_ref + employees_directory + guests_pii (direvisi, own_property)

Mewarisi seluruh kebutuhan Spa & Event Staff. Berikut kebutuhan tambahan khusus Spa & Event Manager:

### Role-Play (Tambahan)

Mengelola operasional spa dan event propertinya — kebutuhan tambahan berupa revenue, utilisasi venue, dan tren layanan untuk keputusan taktis dan strategi kapasitas.

Pertanyaan tambahan yang mungkin diajukan: revenue spa dan event dan trennya, utilisasi venue, cancellation rate event, tren layanan spa, walk-in ratio dan revenue per kunjungan, jumlah staff aktif di tim, kontak tamu untuk kasus yang dieskalasi.

### Audit dan Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| Revenue spa dan event + tren (agregat properti) | spa_bookings.price, event_bookings.total_revenue, terverifikasi ada | Dalam cakupan |
| Utilisasi venue | event_bookings.capacity_booked, venues.max_capacity, terverifikasi ada | Dalam cakupan |
| Cancellation rate event | event_bookings.status, terverifikasi ada | Dalam cakupan |
| Tren layanan spa | spa_bookings.service_name, agregasi per periode | Dalam cakupan |
| Jumlah staff di tim | employees.department='Spa&Event', dalam cakupan employees_directory | Dalam cakupan |
| Kontak tamu untuk kasus eskalasi | guests.email, guests.phone via spa_bookings/event_bookings. Audit superset menemukan Spa & Event Staff sudah memiliki guests_pii, Manager domain sama awalnya tidak | Revisi RBAC: ditambahkan guests_pii, agar dapat menangani langsung kasus yang dieskalasi dari staff (mis. komplain booking VIP) |

### Kebutuhan Data Tambahan

1. Revenue spa dan event, MoM, agregat properti
2. Utilisasi venue rata-rata dan venue dengan utilisasi rendah berulang
3. Cancellation rate event, per periode
4. Tren popularitas layanan spa, per periode (agregat, beda dari snapshot mingguan di Staff)
5. Walk-in ratio dan revenue per kunjungan (inhouse vs walk-in), per periode
6. Jumlah staff aktif departemen Spa & Event
7. Kontak tamu untuk penanganan langsung kasus yang dieskalasi dari staff

---

## 6. HR Manager

RBAC: hr + properties_ref + employees_directory (own_property)

Mewarisi seluruh kebutuhan HR Staff. Berikut kebutuhan tambahan khusus HR Manager:

### Role-Play (Tambahan)

Mengelola kepegawaian propertinya — kebutuhan tambahan berupa watchlist turnover, tren performa tim, dan overtime cost dalam jam untuk level intervensi SDM strategis (beda dari HR Staff yang administratif harian).

Pertanyaan tambahan yang mungkin diajukan: attendance rate per departemen, watchlist gejala pra-resign, turnover rate per departemen, skor performa rata-rata departemen, siapa yang lembur berlebihan (jam), siapa yang konsisten telat, payroll seluruh karyawan propertinya.

### Audit dan Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| Attendance rate per departemen (agregat) | staff_shifts.status, join employees.department | Dalam cakupan |
| Watchlist gejala pra-resign | staff_shifts (rate absen/telat individu vs baseline historisnya sendiri), metrik within-entity over time | Dalam cakupan, sifat metrik khusus |
| Turnover rate per departemen | employees.status, department | Dalam cakupan |
| Skor performa rata-rata departemen | employee_performance.score, join employees.department | Dalam cakupan |
| Overtime dalam jam (agregat dan per individu vs rata-rata) | staff_shifts.clock_in/clock_out | Dalam cakupan |
| Payroll seluruh karyawan propertinya | payroll, HR Manager tidak memiliki domain financial | Di luar cakupan RBAC, murni domain Finance Manager |

### Kebutuhan Data Tambahan

1. Attendance rate per departemen, per periode, agregat properti
2. Rasio perubahan pola individu (rate absen dan telat vs baseline historis individu), metrik inti watchlist
3. Skor performa terakhir per karyawan, tren antar periode review
4. Turnover rate per departemen, MoM dan YoY
5. Distribusi status karyawan per departemen
6. Jam lembur per individu dibanding rata-rata departemen
7. Rate keterlambatan per individu dibanding rata-rata departemen

Di luar cakupan (ditolak RBAC): payroll seluruh karyawan propertinya

---

## 7. Finance Manager

RBAC: financial (mencakup payroll) + reservation (direvisi) + properties_ref + employees_directory (own_property)

Mewarisi seluruh kebutuhan Finance Staff. Berikut kebutuhan tambahan khusus Finance Manager:

### Role-Play (Tambahan)

Mengelola keuangan propertinya — satu-satunya Manager yang menyentuh payroll secara detail, dan pemegang laporan USALI di level properti (beda dari Finance Staff yang administratif harian).

Pertanyaan tambahan yang mungkin diajukan: GOP margin dan trennya, total payroll (base_salary, service_charge, overtime_pay, THR, deduction, net_salary), service charge pool vs okupansi, labor cost sebagai persen revenue.

### Audit dan Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| GOP dan margin | financial_summary.gop, filter department='Overall' | Dalam cakupan |
| Total payroll seluruh karyawan propertinya | payroll.base_salary, service_charge, overtime_pay, thr, deduction, net_salary | Dikonfirmasi dalam cakupan, payroll termasuk domain financial |
| Service charge vs okupansi | payroll.service_charge x daily_occupancy.occupancy_rate, butuh domain reservation | Revisi RBAC: ditambahkan reservation |
| Labor cost persen revenue | payroll dibagi financial_summary.departmental_revenue, dalam domain financial | Dalam cakupan |

### Kebutuhan Data Tambahan

1. GOP dan GOP margin, MoM
2. Total komponen payroll (base_salary, service_charge, overtime_pay, THR, deduction, net_salary), per departemen
3. Labor cost sebagai persen revenue
4. Service charge pool dan korelasinya dengan occupancy rate, cross-table payroll x daily_occupancy

---

## 8. General Manager

RBAC: Semua 7 domain + properties_ref + employees_directory + guests_pii + guests_profile (direvisi, own_property)

Mewarisi seluruh kebutuhan 7 Manager lain (Revenue, F&B, Housekeeping, Maintenance, Spa & Event, HR, Finance Manager) — lihat kebutuhan tambahan masing-masing di atas. Berikut kemampuan tambahan yang khas General Manager:

### Role-Play (Tambahan)

Bertanggung jawab atas seluruh divisi propertinya — akses terluas di level properti. Berbeda secara fundamental dari 7 Manager lain: mereka masing-masing satu domain, GM lintas semua domain untuk satu properti. Pertanyaan tambahan cenderung ringkasan lintas fungsi.

Pertanyaan tambahan yang mungkin diajukan: ringkasan performa properti hari ini/minggu ini (okupansi, revenue F&B, isu maintenance kritis sekaligus), departemen yang butuh perhatian, kontak langsung tamu untuk kasus lintas domain (mis. komplain yang menyentuh F&B sekaligus housekeeping).

### Audit dan Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| Ringkasan lintas domain sekaligus | GM memiliki akses ke semua 7 domain sejak awal RBAC | Dalam cakupan, kekuatan struktural unik GM |
| guests_pii dan guests_profile | Audit superset menemukan Revenue Manager dan Spa/Event Manager memiliki guests_pii (dan Revenue Manager juga guests_profile), GM sebagai atasan seluruh Manager tersebut awalnya tidak memilikinya, meski secara logis lebih berwenang | Revisi RBAC: GM ditambahkan guests_pii + guests_profile, menutup rantai superset dari kedua Manager tersebut |

### Kebutuhan Data Tambahan

1. Ringkasan performa lintas domain dalam satu jawaban (okupansi + revenue F&B + isu maintenance + turnover, dsb)
2. Kontak tamu untuk kasus lintas domain yang dieskalasi ke level properti

Catatan struktural: GM adalah satu-satunya peran level Manager yang mewarisi dari 7 Manager sekaligus (bukan 1 Staff), karena akses lintas domainnya sudah diberikan sejak awal sesuai prinsip segregation of duties — akses seluas apa pun tetap read-only dan own_property.

---

## Ringkasan Seluruh Revisi RBAC dari Layer Manager

| Revisi | Peran terdampak | Alasan |
|---|---|---|
| Tambahan reservation (own_property) | F&B Manager, Housekeeping Manager, Finance Manager | Metrik lintas domain konkret: capture rate, delayed rate vs okupansi, service charge vs okupansi |
| payroll dikonfirmasi termasuk domain financial | Semua peran dengan akses financial | Tidak perlu dipecah granular tersendiri |
| Tambahan guests_pii (own_property) | Revenue Manager, Spa & Event Manager | Audit superset Manager-Staff: Staff di domain sama sudah memilikinya |
| Tambahan guests_pii + guests_profile (own_property) | General Manager | Audit superset GM terhadap Revenue Manager dan Spa/Event Manager (efek berantai dari revisi sebelumnya) |

## Catatan Metodologi: Audit Superset Diperiksa Berlapis, Bukan Sekali Jalan

Ditemukan bahwa revisi pada satu tingkat (mis. Revenue Manager mendapat guests_pii) dapat memicu pelanggaran baru di tingkat atasannya (General Manager, Corporate Revenue Director) yang tidak terlihat kalau audit berhenti di satu pasangan level saja. Metodologi yang diterapkan: setiap kali RBAC direvisi, seluruh rantai ke atas (Manager ke GM, Manager ke Director, Director ke CEO) diperiksa ulang secara terprogram untuk memastikan tidak ada mata rantai yang bocor.

---

*Dokumen ini merupakan hasil pemetaan kebutuhan AI Chatbot untuk layer Manager, dengan format ringkas (kebutuhan tambahan saja, warisan via referensi) dan setiap klaim data terverifikasi terhadap DataSchema.md.*
