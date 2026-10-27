# animation-performance

**Purpose:** Find why web animation misses its frame budget and identify targeted fixes.

**Invocation:** automatic

**Use when:** Motion stutters, drops frames, triggers expensive layout/paint work, or competes with React/main-thread work.

**Do not use when:** Choosing a visual direction, selecting a pleasant easing curve without a performance issue, or diagnosing native RN threads.

**Overlaps and default:** Prefer this over general design guidance for frame-rate symptoms. animate handles motion construction and timing; animate-expo handles RN-specific performance.

**Requirements:** Affected animation code and a reproducible symptom. Browser performance recordings and representative devices are needed to verify runtime claims; distinguish code findings from measurements.

**Expected output:** A cause-linked diagnosis and targeted recommendations or fixes within the requested scope.

**Positive example:** "This drawer drops frames while the dashboard updates; find the cause."

**Negative example:** "What is the name for a sequence of items appearing one after another?"

**Source:** [Pinned SKILL.md](../vendor/emil/skills/animation-performance/SKILL.md)
