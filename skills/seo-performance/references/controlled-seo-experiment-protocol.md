# Controlled SEO experiment protocol

Use this protocol when a team wants to learn whether a bounded change caused a search or user outcome. Keep experiments separate from required security, accessibility, legal, correctness, or incident fixes; those changes do not need an uplift test to be valid.

## Design gate

1. State one decision, falsifiable hypothesis, treatment, eligible population, primary outcome, guardrail metrics, minimum worthwhile effect, and decision owner before assigning units.
2. Choose an assignment unit that matches the change: page, template, directory, market, or another stable cluster. Prevent one unit from appearing in both groups, document cross-linking or seasonality interference, and use a holdout where authorized and feasible.
3. Define inclusion/exclusion rules, sample size or power rationale, pre-period, planned duration or stopping rule, attribution window, data latency, and invalidation conditions before looking at results. Do not use a fixed universal test length.
4. Freeze a hash-pinned baseline and query/page cohort with `seo-performance`. Record known migrations, campaigns, algorithm/reporting changes, tracking changes, and demand shocks as confounders.
5. Route the treatment through `seo-action-plan`. Require implementation owner, release ID, exposure verification, approval, rollback, and user/search safety checks.

## Search-safe implementation

- Serve users and crawlers the same experiment logic; do not cloak a test. If variants use separate URLs, use current search-engine guidance for temporary redirects and canonical handling.
- Change only the declared treatment where practical. Validate raw/rendered output, directives, canonicals, structured data, links, analytics, performance, and assignment persistence.
- Start with a reversible cohort. Stop or roll back on declared user, availability, indexing, data-quality, or policy guardrails.
- End the experiment when the statistical/decision rule is reached, remove temporary variants or scripts, and preserve the final release state. Do not leave a test running indefinitely.

## Measurement and interpretation

1. Use the predeclared source, property, dimensions, windows, cohorts, and metric definitions. Recompute derived metrics and retain anonymization, row-limit, aggregation, and sampling limitations.
2. Check exposure and data quality before evaluating the outcome. A treatment label without verified delivery is not a valid assigned unit.
3. Report treatment and control observations, uncertainty, guardrail results, exclusions, missing data, and design violations. Do not switch the primary metric or subgroup after seeing results; label any post-result analysis exploratory.
4. Claim causation only when assignment, exposure, comparability, interference, and analysis assumptions support it. Otherwise report an observational association and the missing proof.
5. Record ship, iterate, stop, or inconclusive as the decision. A null or negative result is retained; it is not rewritten as a win. A positive test does not guarantee future rankings, traffic, revenue, citation, or conversion.

## Output

Return an experiment charter, assignment/cohort specification, frozen baseline, action-plan item, exposure and guardrail checks, validated comparison run, uncertainty/limitations, decision, rollback or cleanup status, and follow-up owner.

## Primary execution reference

- [Google Search Central: A/B testing best practices for Search](https://developers.google.com/search/docs/crawling-indexing/website-testing)
