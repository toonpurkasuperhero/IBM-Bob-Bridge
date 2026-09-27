#!/usr/bin/env python3
"""
compare_impact.py

This is the starter code for the "deterministic verification" step in the
Bob Bridge architecture: it does NOT ask an LLM whether the change is safe,
it actually runs both versions of the validation output through the
integration mapping and shows the real difference.

In the full Bob Bridge build, this logic gets wrapped as a Bob workflow
(deterministic script + AI reasoning hybrid) so the AI-generated report
is backed by an executed, provable result -- not a guess.

Usage:
    python3 compile_and_run.sh          # produces both .dat files first
    python3 compare_impact.py
"""

import json
import sys
from pathlib import Path

BEFORE_FILE = "validated-output-before.dat"
AFTER_FILE = "validated-output-after.dat"
MAPPING_FILE = "integration_mapping.json"


def parse_output_file(path):
    """Parse the pipe-delimited COBOL output into a list of dict records."""
    records = []
    with open(path) as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split("|")]
            tran_id, tran_type, amt, status, reason = parts
            records.append(
                {
                    "tran_id": tran_id,
                    "tran_type": tran_type,
                    "amount": amt,
                    "status": status,
                    "reason": reason,
                }
            )
    return records


def simulate_salesforce_landing(records):
    """
    Mimics the App Connect trigger condition from integration_mapping.json:
    only STATUS = VALID records ever reach Salesforce and create a
    Refund__c record.
    """
    landed = {}
    for r in records:
        if r["status"] == "VALID" and r["tran_type"] == "REFUND":
            landed[r["tran_id"]] = r
    return landed


def main():
    for f in (BEFORE_FILE, AFTER_FILE, MAPPING_FILE):
        if not Path(f).exists():
            print(f"ERROR: {f} not found. Compile and run both COBOL "
                  f"programs first (see README.md).")
            sys.exit(1)

    with open(MAPPING_FILE) as f:
        mapping = json.load(f)

    before_records = parse_output_file(BEFORE_FILE)
    after_records = parse_output_file(AFTER_FILE)

    before_refunds = simulate_salesforce_landing(before_records)
    after_refunds = simulate_salesforce_landing(after_records)

    broken = set(before_refunds) - set(after_refunds)

    print("=" * 70)
    print("BOB BRIDGE -- VERIFIED IMPACT REPORT")
    print("=" * 70)
    print(f"Business note from mapping: "
          f"{mapping['field_mappings'][1]['business_note']}\n")

    print(f"BEFORE fix -> Refund__c records that would be created in "
          f"Salesforce: {len(before_refunds)}")
    for tid, r in before_refunds.items():
        print(f"    {tid}  amount={r['amount']}  -> Refund__c CREATED")

    print(f"\nAFTER fix  -> Refund__c records that would be created in "
          f"Salesforce: {len(after_refunds)}")
    for tid, r in after_refunds.items():
        print(f"    {tid}  amount={r['amount']}  -> Refund__c CREATED")

    print("\n" + "-" * 70)
    if broken:
        print(f"RESULT: FAIL -- this change silently breaks {len(broken)} "
              f"refund(s).\n")
        for tid in broken:
            r = before_refunds[tid]
            print(f"  * {tid} ({r['amount']}) used to create a Refund__c "
                  f"record. After this change, the core system rejects "
                  f"it (status REJECTED) and it never reaches Salesforce "
                  f"at all -- the customer's refund silently never "
                  f"happens, with no error on the Salesforce side.")
        print("\nPlain-English impact statement (what the business-"
              "translation agent would produce for a Salesforce admin):")
        print('  "This change will stop all customer refunds from '
              'reaching Salesforce. Nothing will error -- refund '
              'requests will simply disappear before they reach your '
              'system."')
        sys.exit(1)
    else:
        print("RESULT: PASS -- no downstream Salesforce impact detected.")
        sys.exit(0)


if __name__ == "__main__":
    main()
