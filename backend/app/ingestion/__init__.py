"""Ingestion clients. Each source: fetch -> bronze -> validate -> promote.

During unattended dev runs these use deterministic mocks (no live network),
per AUTORUN. Swapping in a real source means replacing the fetch step only.
"""
