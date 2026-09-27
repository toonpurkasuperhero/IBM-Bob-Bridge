#!/usr/bin/env bash
# compile_and_run.sh
# Compiles both COBOL versions with GnuCOBOL, runs them against the same
# transactions.dat, then runs the verified impact comparison.
#
# Prereq: GnuCOBOL installed (e.g. `sudo apt install gnucobol` on Debian/
# Ubuntu, or `brew install gnu-cobol` on macOS).

set -e

echo "Compiling BEFORE-FIX version..."
cobc -x -free -o validate_before validate-transaction-before.cbl

echo "Compiling AFTER-FIX version..."
cobc -x -free -o validate_after validate-transaction-after.cbl

echo "Running BEFORE-FIX against transactions.dat..."
./validate_before

echo "Running AFTER-FIX against transactions.dat..."
./validate_after

echo ""
echo "Both runs complete. validated-output-before.dat and"
echo "validated-output-after.dat have been generated."
echo ""
echo "Running verified impact comparison..."
echo ""
python3 compare_impact.py
