# Plan — coding domain

## Goal

Push aggregate throughput beyond 7.82M rows/sec without breaking the
sort contract (qty desc, id asc tie-break).

## Current State

Best = 7,824,726 rows/sec (a009, strategy=caching). Knowledge says nested
dict beats tuple-key dict; wall-clock noise is ~1% so only trust >2% deltas.

## Hypotheses

- Batch key construction: precompute (id, region) pairs once per unique
  key instead of hashing tuples for every row.
- Sort optimization: sort (qty, -id) integer tuples instead of dicts,
  building output dicts only after ordering.
- Memory locality: process rows grouped by id to keep inner dicts hot.

## Next Action

Try tuple-sort variant first (largest expected delta, easiest rollback).
- sneaky extra line
