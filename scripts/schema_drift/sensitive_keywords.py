"""
Milestone 1.4 - Task 3: heuristik "kolom baru berpotensi memuat data sensitif".

Keyword matching (substring, case-insensitive) pada nama kolom -- BUKAN keputusan
approve/reject otomatis, hanya menaikkan severity notifikasi supaya diprioritaskan
saat review. Terinspirasi domain sensitif yang sudah ada di
corporate_master.role_permissions (guests_pii, financial, hr -- lihat Metadata.md).
"""

SENSITIVE_KEYWORDS = [
    # Kredensial / keamanan
    "password", "passwd", "secret", "token", "api_key", "apikey", "credential",
    # Identitas personal (PII)
    "nik", "ktp", "passport", "paspor", "ssn", "ssn_", "national_id",
    # Kontak personal
    "email", "phone", "telepon", "no_hp", "hp_number", "whatsapp",
    # Finansial
    "salary", "gaji", "credit_card", "kartu_kredit", "rekening", "bank_account",
    "account_number", "iban", "cvv", "pin",
    # Kesehatan
    "medical", "kesehatan", "diagnosis",
]


def classify_severity(column_name: str) -> str:
    lowered = column_name.lower()
    for keyword in SENSITIVE_KEYWORDS:
        if keyword in lowered:
            return "high"
    return "normal"
