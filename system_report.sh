#!/bin/bash
# Example batch script, runnable from the GUI's Batch Scripts panel.
echo "=== MAGGIE System Report ==="
date
echo "--- CPU/Memory ---"
free -h
echo "--- Disk ---"
df -h ~
