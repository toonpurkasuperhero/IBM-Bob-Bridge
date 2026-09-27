#!/usr/bin/env python3
"""
run_pipeline.py - Bob Bridge Cross-Platform Deterministic Execution Engine

This script runs the exact business logic of VALIDATE-TRANSACTION (both before and
after fix) against transactions.dat, generates validated-output-before.dat and
validated-output-after.dat, and performs deterministic downstream impact verification.

Can be run standalone or invoked with --json for web dashboard integration.
"""

import os
import sys
import json
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
BEFORE_CBL = BASE_DIR / "validate-transaction-before.cbl"
AFTER_CBL = BASE_DIR / "validate-transaction-after.cbl"
TXN_DATA = BASE_DIR / "transactions.dat"
MAPPING_FILE = BASE_DIR / "integration_mapping.json"
BEFORE_OUT = BASE_DIR / "validated-output-before.dat"
AFTER_OUT = BASE_DIR / "validated-output-after.dat"


def parse_raw_amount(amt_str):
    """
    Parses COBOL PIC S9(6)V99 SIGN LEADING SEPARATE format.
    Example: '-00015000' -> -150.00, '+00007550' -> 75.50
    """
    amt_str = amt_str.strip()
    sign = -1.0 if amt_str.startswith("-") else 1.0
    digits = amt_str.lstrip("+-").strip()
    if not digits:
        return 0.0
    val = float(digits) / 100.0
    return sign * val


def format_ws_display(amt_float):
    """
    Matches COBOL WS-AMT-DISPLAY PIC -(6)9.99
    Example: -150.00 -> '   -150.00', 75.50 -> '     75.50'
    """
    sign_str = "-" if amt_float < 0 else " "
    abs_val = abs(amt_float)
    num_str = f"{abs_val:.2f}"
    # PIC -(6)9.99 is 10 characters total
    formatted = f"{sign_str}{num_str}"
    return formatted.rjust(10)


def execute_cobol_logic(tran_id, tran_type, amt_float, version="before"):
    """
    Executes the exact procedure division logic of VALIDATE-RECORD.
    """
    ws_amt_display = format_ws_display(amt_float)
    
    if version == "before":
        if tran_type == "REFUND":
            ws_status = "VALID   "
            ws_reason = "REFUND: NEGATIVE AMOUNT ALLOWED BY DESIGN"
        else:
            if amt_float < 0:
                ws_status = "REJECTED"
                ws_reason = "NON-REFUND: NEGATIVE AMOUNT NOT ALLOWED "
            else:
                ws_status = "VALID   "
                ws_reason = "AMOUNT OK                               "
    else:  # after
        if amt_float < 0:
            ws_status = "REJECTED"
            ws_reason = "NEGATIVE AMOUNT NOT ALLOWED (NEW RULE)  "
        else:
            ws_status = "VALID   "
            ws_reason = "AMOUNT OK                               "

    record_line = f"{tran_id}|{tran_type.ljust(10)}|{ws_amt_display}|{ws_status}|{ws_reason}"
    return {
        "tran_id": tran_id,
        "tran_type": tran_type,
        "amount_raw": amt_float,
        "amount_display": ws_amt_display.strip(),
        "status": ws_status.strip(),
        "reason": ws_reason.strip(),
        "line": record_line
    }


def run_pipeline(custom_transactions=None):
    """
    Runs both versions and returns comprehensive impact telemetry.
    """
    records = []
    if custom_transactions:
        records = custom_transactions
    else:
        with open(TXN_DATA, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\r\n")
                if len(line) >= 17:
                    t_id = line[0:6].strip()
                    t_type = line[6:16].strip()
                    t_amt_raw = line[16:].strip()
                    amt = parse_raw_amount(t_amt_raw)
                    records.append((t_id, t_type, amt, line))

    before_results = []
    after_results = []
    before_lines = []
    after_lines = []

    for t_id, t_type, amt, _ in records:
        b_res = execute_cobol_logic(t_id, t_type, amt, version="before")
        a_res = execute_cobol_logic(t_id, t_type, amt, version="after")
        before_results.append(b_res)
        after_results.append(a_res)
        before_lines.append(b_res["line"])
        after_lines.append(a_res["line"])

    # Write .dat files
    with open(BEFORE_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(before_lines) + "\n")
    with open(AFTER_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(after_lines) + "\n")

    # Load mapping
    with open(MAPPING_FILE, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    # Downstream Salesforce simulation
    before_salesforce = [r for r in before_results if r["status"] == "VALID" and r["tran_type"] == "REFUND"]
    after_salesforce = [r for r in after_results if r["status"] == "VALID" and r["tran_type"] == "REFUND"]

    before_map = {r["tran_id"]: r for r in before_salesforce}
    after_map = {r["tran_id"]: r for r in after_salesforce}

    broken_ids = [tid for tid in before_map if tid not in after_map]
    broken_records = [before_map[tid] for tid in broken_ids]

    summary = {
        "status": "FAIL" if broken_ids else "PASS",
        "total_transactions": len(records),
        "before_valid_refunds": len(before_salesforce),
        "after_valid_refunds": len(after_salesforce),
        "broken_count": len(broken_ids),
        "broken_records": broken_records,
        "mapping_details": mapping,
        "before_results": before_results,
        "after_results": after_results,
        "plain_english_impact": (
            f"CRITICAL BREAKAGE DETECTED: This change silently breaks {len(broken_ids)} customer refund(s). "
            f"Transactions {', '.join(broken_ids)} were previously processed as valid negative-value refunds, "
            f"triggering Salesforce Refund__c record creation. Under the new rule, the core banking system marks them "
            f"as REJECTED. Because App Connect only forwards STATUS = 'VALID', these refunds vanish without "
            f"throwing any error on the Salesforce side. Customers will never receive their credits."
        ) if broken_ids else "PASS: No downstream Salesforce or ERP breaking impact detected."
    }
    return summary


def main():
    parser = argparse.ArgumentParser(description="Bob Bridge Deterministic Verification Engine")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    telemetry = run_pipeline()

    if args.json:
        print(json.dumps(telemetry, indent=2))
        return

    print("=" * 70)
    print("BOB BRIDGE -- VERIFIED DETERMINISTIC IMPACT REPORT")
    print("=" * 70)
    print(f"Status: {telemetry['status']}")
    print(f"Total Transactions Evaluated: {telemetry['total_transactions']}")
    print(f"Before Fix -> Salesforce Refund__c created: {telemetry['before_valid_refunds']}")
    print(f"After Fix  -> Salesforce Refund__c created: {telemetry['after_valid_refunds']}")
    print(f"Broken Count: {telemetry['broken_count']}")
    print("-" * 70)
    print(telemetry["plain_english_impact"])
    print("=" * 70)


if __name__ == "__main__":
    main()
