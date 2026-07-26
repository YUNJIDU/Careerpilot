# Tracker Reconciliation Design

Date: 2026-07-26

Status: Approved design, pending written-spec review

## Goal

Preserve the user's current local Tracker, fill only values supported by stored
or new email evidence, and make later mail synchronization safe for manually
added applications.

## Reconciliation order

Each synchronization follows this order:

1. Import the current `data/tracker.xlsx`.
2. Preserve its non-empty user values and assign an Application ID to rows that
   do not have one.
3. Match stored and newly fetched emails to applications.
4. Apply field-level precedence rules.
5. Export all applications back to the same workbook without deleting manual
   rows or changing the existing workbook layout.

If import validation fails, synchronization stops before changing the database
or workbook.

## Application identity

- Match on normalized company name plus normalized role.
- Normalization removes surrounding whitespace, normalizes case for Latin
  letters, and treats common Chinese and ASCII bracket forms equivalently.
- Do not use broad fuzzy matching.
- `NIO蔚来` and `蔚来NIO` remain separate until an explicit company-alias rule
  is approved.
- A manual row without matching mail remains an ordinary application and is not
  otherwise processed.

## Field precedence

- Non-empty user values for company, role, notes, and stage-result columns are
  protected from mail-derived overwrites.
- Empty fields may be filled from explicit mail evidence.
- `投递时间`, `截止时间`, and `最近更新时间` are mail-authoritative when the
  email states or supplies the corresponding time.
- `当前阶段` follows the newest accepted email event. Without a newer email,
  the current user value remains unchanged.
- `测评`, `笔试`, and interview columns change only when the email explicitly
  states the corresponding arrangement or result.
- Every mail-derived change retains provenance and remains idempotent.

## Existing-mail backfill

Previously linked email records with a valid `sent_at` participate in
reconciliation even when their messages do not need to be fetched again.

- The earliest application-receipt email supplies `投递时间`.
- The newest accepted application event supplies `最近更新时间`.
- Existing non-time user values remain protected.
- A stored email that cannot be matched remains unlinked and does not mutate a
  manual row.

## Local acceptance

The first reconciliation must:

- retain the manually edited 北方华创, 宁德时代, NIO/蔚来, 贵州金融控股,
  ArcSoft, and 拼多多 rows;
- keep the Guizhou role `投资业务岗位3` and written-test value `笔试挂`;
- assign an Application ID to the manual Pinduoduo row;
- fill available blank timestamps from linked email records;
- leave unsupported blank fields empty;
- preserve the workbook's current sheets, columns, filters, hidden metadata,
  date formats, and visible layout.

## Validation

Automated checks cover:

- ID assignment for a manual row;
- preservation of non-empty user fields;
- filling an empty field from mail;
- mail-authoritative timestamps;
- newest-mail stage selection;
- exact normalized identity matching;
- unmatched manual-row preservation;
- repeated synchronization without duplicate rows or events;
- workbook round-trip and formula-injection protection.

Final verification compares the reconciled workbook with its pre-sync values,
scans for formula errors, and renders the Tracker sheet for visual inspection.

## Deferred

- Fuzzy company or role matching.
- Automatic company aliases.
- Automatic merging of existing duplicate applications.
- LLM-based reconciliation.
