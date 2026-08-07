"""23 tabel production yang dipantau schema drift-nya. Reuse daftar dari Milestone 1.2
(scripts/monitoring/tables_config.py) supaya tidak ada 3 sumber kebenaran berbeda untuk
daftar tabel yang sama."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from tables_config import TABLES as _M12_TABLES  # noqa: E402

TABLES = [(schema, table) for schema, table, *_ in _M12_TABLES]
