# pick-ui-library

**Purpose:** Recommend a library from Emil's curated list for a specific frontend capability.

**Invocation:** explicit-only

**Route:** Choose a UI component library

**Synonyms:** UI library selection; component library comparison; headless primitives

**Use when:** The user explicitly invokes pick-ui-library to choose a dependency for a concrete UI task.

**Do not use when:** Automatically choosing dependencies during ordinary coding, replacing a working library without a request, or backend package selection.

**Overlaps and default:** Use ask-sonner for an existing Sonner task. This makes a dependency choice, whereas Impeccable and emil-design-eng guide UI quality. Check existing dependencies first.

**Requirements:** Explicit invocation, the requested capability and package.json. Install/wire a dependency only when included in the task. Do not churn a competitor already used by the project.

**Expected output:** One justified library recommendation, with integration only when requested.

**Positive example:** "Use pick-ui-library to choose a virtualization library for this React list."

**Negative example:** "Fix the scrolling bug in our existing virtualized list."

**Source:** [Pinned SKILL.md](../vendor/emil/skills/pick-ui-library/SKILL.md)
