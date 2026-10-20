---
title: Trusted-user local experiment and cooperative runtime workspace
created: 2026-10-06
updated: 2026-10-06
type: decision
status: accepted
tags: [architecture, rathena, ops, testing]
---

# ADR-018: Use the existing rootless engine; trust same-user project programs

Related: [[adr-010-worlds-volumes-e2e]],
[[adr-016-private-runtime-before-world-launch]], [[runtime-publication-contract]],
[[goals-ledger]].

## Decision and authority

The user explicitly selected the existing rootless Podman setup with programs
running under their Unix account trusted. Preserve isolated debug, test and named
production data, but **do not claim protection against hostile same-user programs**.
This is a trust-boundary decision, not proof that a manager or world is deployed.

Prefer the private-staging plus receipt-catalog architecture from the publication
proposal. Its workspace can now rely on a cooperating single-writer manager and
lifetime advisory lock under this explicit trust model; it need not introduce a
new NixOS service identity solely to exclude same-UID adversaries.

A manager must still issue scoped registrations before allocation, retain parent
handles, refuse existing/unknown candidate roots and destinations, verify private
metadata and binding, perform nonreplacing publication and required sync/readback,
and separate current-session acknowledgement from historical records. Caller
booleans, directory modes, labels and arbitrary destination paths are not admission.

## Still required

- Distinct debug/test/named-production storage and exact project-owned identities.
- Conservative uncertain/quarantined states, one-attempt cleanup and original
  exception preservation. No guaranteed marker restoration, rollback or FD release.
- Restart denial until explicit recovery; no automatic adoption of old directories
  or committed-looking journal rows. No deletion of foreign or existing targets.
- Scoped operation authorization and readback before database/world mutations.
  Trusted same-user programs must cooperate with the workspace lock. Operator
  interference can invalidate observations; detected changes revoke acknowledgement.
- Per-agent knowledge/memory isolation and all six native acceptance milestones.

## Explicit exclusions and unchanged evidence

This decision supersedes only the hostile same-UID exclusion prerequisite in the
**proposed** publication guide. It does not retrospectively close the original
pre-stat substitution or failure-marker findings, alter accepted ADRs, weaken input
validation, permit arbitrary filesystem writes, reset production/human accounts,
or authorize SQL, container/world startup or service changes.

An exclusive mkdir followed by stat/open is still not a kernel construction-FD
receipt under hostile mutation. New managed execution must state the cooperative
assumption rather than relabel that observation as adversarial provenance proof.

The engine responded to current read-only version queries. The stricter test-world
inventory route failed and remains nonauthorizing; existence/ownership of its
specific resources is presently unknown and must be diagnosed before live use.
