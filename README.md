# Bob Bridge — Sample Project Starter Files

These are the Phase 0 artifacts described in the execution plan: a small,
self-contained "legacy core system + downstream CRM integration" stand-in
you can point Bob Bridge at, with zero dependency on real IBM i/mainframe
access.

## What's here

| File | Role |
|---|---|
| `validate-transaction-before.cbl` | The "working" COBOL program. REFUND transactions are correctly allowed a negative amount. |
| `validate-transaction-after.cbl` | The "broken" version, after a well-intentioned but incomplete fix rejects all negative amounts. |
| `the-fix.diff` | The exact commit diff — this is what you'd feed to Bob's Plan mode as the triggering change. |
| `transactions.dat` | Fixed-width sample transaction data (25 chars/record: 6-char ID, 10-char type, 9-char signed amount). Mix of REFUND and PURCHASE records, including one edge case. |
| `integration_mapping.json` | Mock App Connect / Salesforce field mapping, including the business note explaining the sign convention that the "fix" breaks. This is the document you'd feed to Bob's document-understanding step. |
| `compare_impact.py` | Starter code for the deterministic verification step — actually simulates which records would land in Salesforce before vs. after, no guessing. |
| `compile_and_run.sh` | One command to compile both COBOL versions with GnuCOBOL, run them, and print the impact report. |

## Quick start

```bash
# 1. Install GnuCOBOL if you don't have it
sudo apt install gnucobol      # Debian/Ubuntu
brew install gnu-cobol         # macOS

# 2. Run everything
chmod +x compile_and_run.sh
./compile_and_run.sh
```

Expected output ends with something like:

```
RESULT: FAIL -- this change silently breaks 3 refund(s).
  * TXN001 (-150.00) used to create a Refund__c record. After this
    change, the core system rejects it...
```

That's your "before/after, proven not guessed" moment — the core of the
Bob Bridge demo.

## How this plugs into the full Bob Bridge build

1. `the-fix.diff` is the input to Bob's **Plan mode** (Section 4a of the
   execution plan) — this is the change being analyzed.
2. `validate-transaction-before.cbl` (and the copybook layout inside it)
   plus `integration_mapping.json` are what you feed Bob for
   **document understanding**.
3. The legacy-side, integration-side, business-translation, test-data,
   and compliance subagents (spawned in parallel via `spawn_subagent`)
   each do a piece of what `compare_impact.py` currently does by hand —
   the script is your reference implementation to build the Bob workflow
   against, and your fallback if a subagent isn't ready in time.
4. `compile_and_run.sh`'s logic is what becomes the **Bob workflow**
   (deterministic script + AI hybrid) described in Section 4a — wrap
   this exact pass/fail check so Bob's report is backed by a real
   executed result.

## Notes / things to double check once you're in Bob

- Confirm Bob's actual current custom-mode config syntax against its
  live docs before writing `.bob/modes/bob-bridge.md` — file formats
  change between versions and this wasn't verified against the current
  release.
- Feel free to swap the transaction data or add more edge cases (e.g. a
  zero-amount record, a record with an unrecognized TRAN-TYPE) once the
  core demo works, to make the subagents' reasoning more visibly robust.
