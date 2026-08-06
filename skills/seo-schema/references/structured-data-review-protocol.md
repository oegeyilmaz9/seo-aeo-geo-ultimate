# Structured-data review protocol

## Field ledger

For every emitted property record the schema path, value, source location or approved system of record, locale/date scope, and reviewer if material. A property without a source is omitted or marked as a placeholder.

## Three-part validation

1. Parse and validate the delivered structured-data graph.
2. Check current primary platform documentation for the specific feature/type and its eligibility conditions.
3. Compare markup with rendered visible content and canonical page/entity identity.

Report each result separately. “Valid JSON-LD” is not synonymous with “eligible,” and “eligible” is not a display guarantee.

## Release safety

Use an approved template/data owner, deployment scope, test URL, rendering check, monitoring window, and rollback. Treat reviews, prices, availability, identity, regulated data, and personalization as high-scrutiny fields.
