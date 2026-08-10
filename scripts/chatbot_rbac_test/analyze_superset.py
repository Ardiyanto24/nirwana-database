"""
Milestone 4.6 Layer C -- re-verifies the 4 superset chains (KK2) as a pure
set-containment analysis over Layer A's ACTUAL observed HTTP results
(milestones/4.6-.../hasil-layer-a-matriks-akses.txt), not over
mart_cleaned.role_permissions directly -- the whole point of KK2 is proving
the superset property holds in the implementation, not just in the ground
truth table it's supposed to implement (decisions.md M4.6 Keputusan #5). No
new HTTP calls are made here.

Usage:
  python analyze_superset.py [path/to/hasil-layer-a-matriks-akses.txt]
"""
import sys

# Column widths from run_access_matrix.py's print format:
# f"{role:<32}{domain:<22}{expected:<18}{status:<8}{verdict}"
_ROLE_END = 32
_DOMAIN_END = _ROLE_END + 22
_EXPECTED_END = _DOMAIN_END + 18
_STATUS_END = _EXPECTED_END + 8

CHAINS = {
    "Staff -> Manager": [
        ("F&B Staff", "F&B Manager"),
        ("Finance Staff", "Finance Manager"),
        ("Housekeeping Staff", "Housekeeping Manager"),
        ("HR Staff", "HR Manager"),
        ("Maintenance Staff", "Maintenance Manager"),
        ("Spa & Event Staff", "Spa & Event Manager"),
        ("Front Office Staff", "Revenue Manager"),
    ],
    "Manager -> Corporate Director": [
        ("F&B Manager", "Corporate Operations Director"),
        ("Housekeeping Manager", "Corporate Operations Director"),
        ("Maintenance Manager", "Corporate Operations Director"),
        ("Spa & Event Manager", "Corporate Operations Director"),
        ("Finance Manager", "Corporate Finance Director"),
        ("HR Manager", "Corporate HR Director"),
        ("Revenue Manager", "Corporate Revenue Director"),
    ],
    "Manager -> General Manager": [
        ("F&B Manager", "General Manager"),
        ("Finance Manager", "General Manager"),
        ("Housekeeping Manager", "General Manager"),
        ("HR Manager", "General Manager"),
        ("Maintenance Manager", "General Manager"),
        ("Revenue Manager", "General Manager"),
        ("Spa & Event Manager", "General Manager"),
    ],
}

ALL_ROLES_MINUS_CEO = [
    "Corporate Finance Director", "Corporate HR Director", "Corporate Operations Director",
    "Corporate Revenue Director", "General Manager", "Revenue Manager", "F&B Manager",
    "Finance Manager", "Housekeeping Manager", "HR Manager", "Maintenance Manager",
    "Spa & Event Manager", "Front Office Staff", "F&B Staff", "Finance Staff",
    "Housekeeping Staff", "HR Staff", "Maintenance Staff", "Spa & Event Staff",
]
CHAINS["Seluruh peran -> CEO"] = [(role, "CEO") for role in ALL_ROLES_MINUS_CEO]


def parse_results(path):
    """Returns {role: set(domain)} -- domains where status == 200."""
    allowed = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if len(line) < _STATUS_END or line.startswith("role") or line.startswith("-"):
                continue
            role = line[:_ROLE_END].strip()
            domain = line[_ROLE_END:_DOMAIN_END].strip()
            status = line[_EXPECTED_END:_STATUS_END].strip()
            if not role or not domain or not status.isdigit():
                continue
            if status == "200":
                allowed.setdefault(role, set()).add(domain)
    return allowed


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "hasil-layer-a-matriks-akses.txt"
    allowed = parse_results(path)

    total_pairs = 0
    failures = []
    for chain_name, pairs in CHAINS.items():
        print(f"--- {chain_name} ({len(pairs)} pasang) ---")
        for lower, higher in pairs:
            total_pairs += 1
            lower_domains = allowed.get(lower, set())
            higher_domains = allowed.get(higher, set())
            ok = lower_domains.issubset(higher_domains)
            print(f"  [{'OK' if ok else 'FAIL'}] {lower} {lower_domains} subset-of {higher} {higher_domains}")
            if not ok:
                failures.append((chain_name, lower, higher, lower_domains, higher_domains))

    print(f"\n{total_pairs - len(failures)}/{total_pairs} pasang superset valid.")
    if failures:
        print("\nFAILURES:")
        for chain_name, lower, higher, lo, hi in failures:
            print(f"  [{chain_name}] {lower} {lo} NOT subset-of {higher} {hi} -- extra: {lo - hi}")
        sys.exit(1)


if __name__ == "__main__":
    main()
