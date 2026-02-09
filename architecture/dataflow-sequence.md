# Dataflow Sequence

This document describes the event lifecycle and the intended SLA checks at each hop.

## Event Lifecycle

1. Source file record (LANL): `time,user,computer`
2. Producer: adds `event_id`, normalizes fields, emits to Kinesis
3. Stream processor:
   - parse + validate
   - deduplicate
   - compute rolling aggregates
   - apply risk rules
4. Sink:
   - curated `auth_events_curated`
   - aggregate tables

## SLAs

- Freshness: curated data < 5 minutes behind
- Completeness: < 0.1% invalid records per hour
