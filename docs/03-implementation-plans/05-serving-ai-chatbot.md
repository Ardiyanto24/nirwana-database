# Rancangan Implementasi — Serving AI Chatbot

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Pemilik pekerjaan** | 1 orang (PIC AI Chatbot Serving) |
| **Dokumen induk** | `rancangan-arsitektur-data-platform-elt.md` (Bagian 8) |
| **Dokumen rujukan kebutuhan** | `pemetaan-kebutuhan-chatbot-layer-staff.md`, `pemetaan-kebutuhan-chatbot-layer-manager.md`, `pemetaan-kebutuhan-chatbot-layer-korporat.md` (20 persona), `rancangan-rbac-ai-chatbot.md` (dasar RBAC granular), `role_permissions_chatbot_v2.csv` (RBAC final, 77 baris) |
| **Cakupan pekerjaan** | Lapisan konsumsi di atas `mart_aggregated` (PostgreSQL) untuk AI Chatbot — query interface ter-RBAC per persona, kredensial, dan API sebagai jalur query dari sistem chatbot |
| **Tidak termasuk** | Membangun struktur/isi `mart_aggregated` itu sendiri (lihat `03-mart-aggregated-owner.md`); **RBAC lapis pertama** (validasi intent/prompt di application layer chatbot) — itu sepenuhnya domain sistem AI Chatbot sendiri, bukan cakupan data engineering |
| **Status dokumen** | Rancangan implementasi kerja — bukan dokumen arsitektur. **Skema API ditandai eksplisit sebagai masih bisa berubah** — lihat Bagian "Catatan Ketidakpastian" |

---

## Cara Membaca Dokumen Ini

Sama seperti dokumen lain di project ini: berisi **milestone**, bukan task list atomic. Urutan di bawah adalah urutan yang disarankan, bukan urutan kaku — temuan di satu milestone wajar memengaruhi milestone sesudahnya. Pekerjaan ini secara jujur ditandai sebagai **paling besar** dibanding pekerjaan serving lain, karena kompleksitas RBAC granular (77 kombinasi role × domain) dan jumlah persona (20) yang harus dilayani.

Rujuk ketiga dokumen layer chatbot (Staff/Manager/Korporat), `rancangan-rbac-ai-chatbot.md`, dan `role_permissions_chatbot_v2.csv` untuk detail lengkap — dokumen ini tidak mengutip ulang seluruh isinya.

---

## Batas Tanggung Jawab: RBAC Dua Lapis

Sistem RBAC AI Chatbot terdiri dari dua lapis dengan pemilik berbeda:

| Lapis | Lokasi | Fungsi | Pemilik |
|---|---|---|---|
| **Lapis 1** | Application layer (sistem chatbot) | Validasi intent/prompt terhadap role pengguna sebelum query dieksekusi | **Di luar cakupan pekerjaan ini** — domain sistem AI Chatbot |
| **Lapis 2** | Database/infrastructure layer | Kredensial chatbot secara teknis hanya memiliki privilese `SELECT` ke `mart_aggregated` — tidak ada jalur ke `mart_cleaned`, `raw_production`, atau production | **Cakupan pekerjaan ini** |

Prinsip *defense in depth* yang mendasari pembagian ini: jika Lapis 1 gagal (bug logika validasi, upaya prompt injection, dsb), Lapis 2 tetap berfungsi sebagai pengaman akhir yang murni teknis dan tidak bergantung pada benar-tidaknya application logic pihak chatbot. Karena itu, **pekerjaan ini tidak boleh mengasumsikan Lapis 1 selalu benar** — setiap desain akses di sini perlu tetap aman meskipun Lapis 1 diasumsikan bisa saja gagal.

Konsekuensi arsitektural yang menguntungkan: karena chatbot terhubung ke PostgreSQL (bukan BigQuery) dan `mart_aggregated` adalah satu-satunya data yang bisa dijangkau, chatbot **tidak akan pernah** bisa "nyasar" ke BigQuery atau ke `mart_cleaned` — secara arsitektural jalur itu memang tidak pernah ada, bukan sekadar diblokir oleh permission.

---

## Konteks: Skala RBAC yang Perlu Dilayani

- **20 persona**: 7 Staff, 8 Manager, 5 Korporat — masing-masing dengan kombinasi domain data dan cakupan properti (`own_property` vs `all_properties`) yang berbeda.
- **77 baris** kombinasi (role × domain) di `role_permissions_chatbot_v2` — sudah final dan teraudit penuh prinsip *superset*-nya (posisi lebih tinggi selalu mencakup akses granular bawahannya, di seluruh 4 jalur pemeriksaan: Staff→Manager, Manager→Corporate Director, Manager→General Manager, seluruh peran→CEO).
- **10 `data_domain`**: `reservation`, `fnb`, `facility`, `spa_event`, `hr`, `financial`, `properties_ref`, `employees_directory`, `guests_pii`, `guests_profile` — empat yang terakhir adalah hasil pemecahan granular dari `corporate_master` lama, karena satu izin gabungan sebelumnya mencampur data dengan sensitivitas sangat berbeda.
- **Pemecahan di level kolom, bukan tabel**: `guests_pii` (kontak: email, phone) dan `guests_profile` (loyalty_tier, nationality, dsb) adalah dua kelompok kolom berbeda di atas **tabel fisik `guests` yang sama** — bukan dua tabel terpisah. Implikasinya, akses granular ini butuh dua definisi terpisah (mis. dua view) di atas satu tabel fisik.
- **`role_permissions_chatbot_v2` sendiri tidak pernah menjadi target query chatbot** dalam skenario apa pun — ini bukan sesuatu yang otomatis aman hanya karena tidak ada baris izinnya; perlu ditegaskan eksplisit sebagai batasan teknis di lapis kita juga (defense in depth), bukan diserahkan sepenuhnya ke Lapis 1.

---

## Milestone 4.1 — Pemetaan RBAC ke Struktur Akses Teknis

### Lingkup
Menerjemahkan 77 baris `role_permissions_chatbot_v2` dan detail kebutuhan 20 persona menjadi struktur akses teknis konkret: domain data mana perlu view/kelompok kolom apa, bagaimana `own_property` vs `all_properties` diterapkan sebagai filter, dan bagaimana pemecahan `guests_pii`/`guests_profile` diwujudkan sebagai dua view berbeda di atas tabel `guests` yang sama.

### Kenapa Ini Jadi Milestone Terpisah
Ini fondasi seluruh desain akses berikutnya — mengingat skala (20 persona × 10 domain × 2 cakupan properti), kesalahan pemetaan di sini akan menjalar ke seluruh milestone berikutnya. Sifatnya murni analitis/desain, aman dihentikan sementara tanpa merusak apa pun karena belum menyentuh implementasi.

### Output
- Tabel pemetaan: 10 `data_domain` → view/kelompok kolom teknis yang mewakilinya di `mart_aggregated`.
- Definisi eksplisit mekanisme `own_property` vs `all_properties` sebagai pola filter yang akan diterapkan konsisten di seluruh view.
- Konfirmasi eksplisit bahwa `role_permissions_chatbot_v2` tidak termasuk dalam struktur akses apa pun yang bisa dijangkau chatbot.

### Kriteria Keberhasilan
- Setiap 10 `data_domain` punya pemetaan teknis yang jelas ke struktur `mart_aggregated`, termasuk kasus khusus `guests_pii`/`guests_profile` yang dipisah di level kolom.
- Pemetaan ini bisa dipakai langsung sebagai acuan Milestone 4.2 tanpa perlu menerka ulang dari `role_permissions_chatbot_v2`.

---

## Milestone 4.2 — View Akses Granular per Domain

### Lingkup
Membangun view di atas `mart_aggregated` sesuai pemetaan Milestone 4.1 — termasuk view terpisah untuk `guests_contact_view` dan `guests_profile_view` di atas tabel `guests` yang sama, dan penerapan filter `own_property`/`all_properties` secara konsisten di seluruh view domain lainnya.

### Kenapa Ini Jadi Milestone Terpisah
Ini implementasi inti dari RBAC lapis kedua — dipisah dari Milestone 4.1 (desain) agar view yang dibangun bisa diuji dan divalidasi secara independen sebelum dihubungkan ke mekanisme kredensial dan API.

### Output
- View akses per domain data, termasuk pemisahan kolom PII vs profile pada `guests`.
- Validasi bahwa tidak ada view yang secara tidak sengaja mengekspos kolom di luar cakupan domain yang dimaksud.

### Kriteria Keberhasilan
- Setiap domain data punya view yang mengembalikan hanya kolom yang relevan dengan domain tersebut.
- Percobaan mengakses kolom PII lewat view `guests_profile_view` (atau sebaliknya) gagal karena kolom tersebut memang tidak ada di view itu.
- Filter `own_property`/`all_properties` terbukti bekerja benar pada uji coba dengan beberapa `property_id` berbeda.

---

## Milestone 4.3 — Kredensial Read-Only Per Kelompok Akses

### Lingkup
Mengonfigurasi kredensial database read-only untuk chatbot, dengan privilese `SELECT` yang **secara teknis terbatas hanya ke `mart_aggregated`** — tidak ada jalur apa pun ke `mart_cleaned`, `raw_production`, atau production database asli. Ini adalah implementasi konkret dari Lapis 2 RBAC yang menjadi tanggung jawab pekerjaan ini.

### Kenapa Ini Jadi Milestone Terpisah
Ini titik paling kritis dari seluruh pekerjaan — kegagalan di sini berarti kegagalan seluruh prinsip *defense in depth* yang mendasari desain RBAC dua lapis. Layak berdiri sebagai unit kerja tersendiri yang divalidasi secara eksplisit dan ketat, terpisah dari pembangunan view (Milestone 4.2).

### Output
- Kredensial/service account `chatbot-readonly` (atau setara) dengan privilese `SELECT` yang terbukti terbatas hanya ke `mart_aggregated`.
- Dokumentasi eksplisit batasan kredensial ini sebagai referensi audit keamanan.

### Kriteria Keberhasilan
- Kredensial chatbot terbukti **tidak bisa** mengakses `mart_cleaned`, `raw_production`, atau sistem production sama sekali saat diuji coba langsung (bukan diasumsikan aman).
- Kredensial terbukti hanya bisa membaca (`SELECT`), tidak bisa menulis/mengubah data di `mart_aggregated`.
- Kredensial terbukti tidak bisa mengakses tabel `role_permissions_chatbot_v2` itu sendiri.

---

## Milestone 4.4 — API Query Interface untuk AI Chatbot

### Lingkup
Membangun API yang menjadi jalur query dari sistem AI Chatbot ke `mart_aggregated` — menerima permintaan yang sudah lolos validasi intent di Lapis 1 (dari sistem chatbot), lalu mengeksekusi ke view yang sesuai dengan role dan domain yang diminta. Skema API ini **secara eksplisit ditandai masih bisa berubah** (lihat Bagian "Catatan Ketidakpastian" di bawah) — desain awal perlu cukup fleksibel untuk mengakomodasi perubahan tanpa mengubah keseluruhan fondasi.

### Kenapa Ini Jadi Milestone Terpisah
Ini titik integrasi dengan sistem eksternal (chatbot) yang berada di luar kendali langsung pekerjaan ini — baru bisa dibangun dengan baik setelah view (Milestone 4.2) dan kredensial (Milestone 4.3) stabil, karena API ini pada dasarnya adalah pintu masuk terkontrol ke keduanya.

### Output
- Endpoint API yang menerima permintaan query dari sistem chatbot (role/persona pengguna, domain yang diminta, parameter filter) dan mengembalikan hasil dari view yang sesuai.
- Mekanisme penolakan eksplisit untuk permintaan yang menyasar domain/kolom di luar cakupan role yang diminta (sebagai lapisan tambahan, bukan pengganti Lapis 1).
- Dokumentasi API untuk tim pengembang sistem chatbot, dengan penanda jelas bagian mana yang stabil dan bagian mana yang masih berpotensi berubah.

### Kriteria Keberhasilan
- Untuk sampel beberapa persona dari masing-masing tingkat (Staff, Manager, Korporat), permintaan API menghasilkan data yang sesuai dengan cakupan akses role tersebut menurut `role_permissions_chatbot_v2`.
- Permintaan yang mencoba mengakses domain di luar cakupan role (uji coba terkontrol) ditolak oleh API, bukan diteruskan ke database.
- API terbukti tidak bisa dipakai untuk menjangkau `role_permissions_chatbot_v2`, `mart_cleaned`, maupun raw data dalam skenario apa pun.

---

## Milestone 4.5 — Audit Log Query Chatbot

### Lingkup
Membangun mekanisme pencatatan setiap query yang dieksekusi lewat API ini — mencakup identitas/role pengguna yang meminta, domain/parameter yang diminta, waktu eksekusi, dan hasil (berhasil/ditolak). Ini menjadi dasar bagi kebutuhan monitoring performa query chatbot di Fase 2 pekerjaan monitoring (`06-monitoring-warehouse-serving-fase2.md`), sehingga perlu tersedia lebih dulu sebelum monitoring itu bisa dibangun di atasnya.

### Kenapa Ini Jadi Milestone Terpisah
Audit log adalah kebutuhan keamanan sekaligus kebutuhan operasional (dasar monitoring pihak lain) — layak berdiri sendiri agar desainnya tidak jadi tambahan terburu-buru di akhir Milestone 4.4.

### Output
- Mekanisme pencatatan log query: identitas pengguna, role, domain diminta, waktu, status (berhasil/ditolak), jumlah baris hasil.
- Log tersimpan di lokasi yang bisa diakses pekerjaan monitoring Fase 2 tanpa perlu integrasi tambahan yang rumit.

### Kriteria Keberhasilan
- Setiap panggilan API (baik berhasil maupun ditolak) tercatat di log dengan detail yang cukup untuk ditelusuri.
- Log bisa diquery/diakses secara terpisah dari sistem chatbot itu sendiri (tidak terkubur di dalam log aplikasi chatbot yang tidak bisa diakses tim data).

---

## Milestone 4.6 — Uji Ketahanan RBAC Lintas Persona

### Lingkup
Melakukan pengujian menyeluruh dan sistematis terhadap seluruh 20 persona untuk memastikan tidak ada kebocoran akses — baik akses yang seharusnya diberikan tapi tidak muncul, maupun akses yang seharusnya tidak diberikan tapi ternyata bisa dijangkau. Ini termasuk memverifikasi ulang prinsip *superset* yang sudah diaudit di level dokumen kebutuhan, kali ini di level implementasi teknis nyata.

### Kenapa Ini Jadi Milestone Terpisah
Mengingat skala (20 persona × 10 domain × 2 cakupan properti = ratusan kombinasi yang mungkin), verifikasi ini tidak bisa dianggap "otomatis benar" hanya karena Milestone 4.1–4.5 sudah selesai dikerjakan dengan hati-hati — butuh siklus pengujian eksplisit tersendiri sebelum dianggap siap dipakai produksi.

### Output
- Hasil pengujian sistematis untuk seluruh 20 persona: akses yang didapat vs akses yang seharusnya menurut `role_permissions_chatbot_v2`.
- Daftar temuan (jika ada) dan status perbaikannya.

### Kriteria Keberhasilan
- Seluruh 20 persona, saat diuji lewat API ini, menghasilkan cakupan akses yang **persis cocok** dengan `role_permissions_chatbot_v2` — tidak lebih (kebocoran), tidak kurang (akses yang seharusnya ada tapi hilang).
- Prinsip superset (Director superset Manager, Manager superset Staff, CEO superset semua) terverifikasi ulang di level implementasi, bukan hanya dipercaya dari hasil audit dokumen.

---

## Catatan Ketidakpastian: Skema API Masih Bisa Berubah

Berbeda dari pekerjaan serving lain, skema API untuk AI Chatbot **belum final** dan ditandai secara eksplisit sebagai area yang bisa berubah — kemungkinan karena bentuk integrasi dengan sistem chatbot (bagaimana Lapis 1 mengirimkan permintaan ke Lapis 2) masih dalam pengembangan di pihak lain. Implikasi untuk pekerjaan ini:

- Milestone 4.1–4.3 (pemetaan, view, kredensial) relatif stabil karena berbasis `role_permissions_chatbot_v2` yang sudah final dan teraudit — ini sebaiknya diselesaikan lebih dulu dan dianggap fondasi yang jarang berubah.
- Milestone 4.4 (API) adalah titik yang paling mungkin perlu direvisi mengikuti perkembangan kebutuhan integrasi dari sistem chatbot. Desain di sini sebaiknya menjaga pemisahan yang jelas antara "logic akses" (view + kredensial, di Milestone 4.2–4.3) dan "bentuk request/response API" (Milestone 4.4), sehingga saat skema API berubah, perubahan itu tidak memaksa desain akses granular dibongkar ulang.
- Milestone 4.5 dan 4.6 perlu disesuaikan kembali setiap kali skema API di Milestone 4.4 berubah signifikan.

---

## Catatan Serah Terima

Pekerjaan ini bergantung penuh pada `mart_aggregated` yang disediakan `03-mart-aggregated-owner.md`. Audit log dari Milestone 4.5 menjadi salah satu masukan penting bagi `06-monitoring-warehouse-serving-fase2.md` (monitoring performa query chatbot) — pastikan format dan lokasi log dikomunikasikan ke pemilik pekerjaan tersebut sebelum Fase 2 dimulai.
