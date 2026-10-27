# review-animations

**Purpose:** Review animation code against the skill's motion craft standards.

**Invocation:** explicit-only

**Route:** Review motion in a supplied recording

**Use when:** The user explicitly invokes review-animations for a focused animation change or diff.

**Do not use when:** General code review, feature implementation, backend defects or silently inserting a mandatory review into every task.

**Overlaps and default:** improve-animations handles a codebase-wide audit; animation-performance handles jank diagnosis. This is the manual-only focused review, not a construction workflow.

**Requirements:** Explicit invocation and a motion diff/target. Read STANDARDS.md for exact values and citations. Inspect rendered behavior when available and distinguish it from code evidence.

**Expected output:** Findings table and review verdict; no unrelated implementation.

**Positive example:** "Use review-animations to review the drawer transitions in this diff."

**Negative example:** "Review this database migration for correctness."

**Source:** [Pinned SKILL.md](../vendor/emil/skills/review-animations/SKILL.md)
