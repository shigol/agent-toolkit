# break-ui

**Purpose:** Expose layout and presentation failures using realistic worst-case data.

**Invocation:** automatic

**Use when:** A component needs testing with long or short names, missing values, large counts, translated text or empty collections.

**Do not use when:** Backend load tests, security fuzzing, art-direction exploration or animation-only review.

**Overlaps and default:** Use after the intended UI exists. Impeccable handles overall refinement; break-ui specifically tests content robustness. It does not replace data validation or backend tests.

**Requirements:** Component code and a runnable preview/test surface. Use plausible fixtures and keep demo/worst-case data isolated from real production records.

**Expected output:** A comparison harness, findings tied to realistic inputs, and fixes or recommendations within scope.

**Positive example:** "Check this member card with long names, missing avatars and zero activity."

**Negative example:** "Load-test the database with ten thousand concurrent requests."

**Source:** [Pinned SKILL.md](../vendor/emil/skills/break-ui/SKILL.md)
