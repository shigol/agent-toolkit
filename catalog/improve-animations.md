# improve-animations

**Purpose:** Survey existing animation code and write prioritized findings and implementation plans.

**Invocation:** automatic

**Route:** Audit or improve existing motion

**Use when:** The requested deliverable is an app-wide motion audit or a roadmap of animation improvements.

**Do not use when:** Applying fixes during the audit, a single-diff approval, or discovering only new places to animate.

**Overlaps and default:** find-animation-opportunities looks for absent motion; animation-performance isolates jank; animate implements accepted fixes. review-animations is the manual-only focused review workflow.

**Requirements:** Read access to source and motion conventions. Use AUDIT.md and PLAN-TEMPLATE.md; write only permitted plan artifacts. No source edits, installs, commits or mutating builds during this workflow.

**Expected output:** Prioritized findings and self-contained plans, not an implemented fix.

**Positive example:** "Audit the existing animations and give us a prioritized improvement plan."

**Negative example:** "Implement this already-approved popover transition now."

**Source:** [Pinned SKILL.md](../vendor/emil/skills/improve-animations/SKILL.md)
