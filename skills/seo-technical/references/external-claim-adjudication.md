# External audit claim adjudication

Do not turn a scanner warning, consultant claim, dashboard heuristic, or copied checklist into a mandatory change without testing the layer and product contract it refers to.

Assign one status:

- **Confirmed defect:** observed behavior violates the declared contract on the relevant layer; it can become a required finding.
- **Layer mismatch:** the claim inspects a different layer than the product contract, such as raw HTML when the accepted experience is hydrated; verify the owning layer before changing anything.
- **Supported opportunity:** current primary guidance and product value support an improvement, but the current state is not a defect.
- **False positive:** the claim conflicts with the actual contract or applicable standard.
- **Unverified:** evidence, scope, access, or a current source is missing.

Only a confirmed defect becomes required automatically. Examples that need adjudication include a missing link `title` attribute, `alt=""` on a decorative image, breadcrumb differences between raw and hydrated DOM, arbitrary meta-description length limits, URL-length thresholds, and generic click-depth scores. Accessibility, security, and usability improvements may still be worthwhile on their own merits; do not disguise them as ranking requirements.
