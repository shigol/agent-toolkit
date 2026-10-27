# hyperframes-cli

**Purpose:** Use HyperFrames commands to scaffold, inspect, preview, validate and render a composition.

**Invocation:** automatic

**Route:** Render or inspect HyperFrames output

**Synonyms:** HyperFrames render; preview; validate composition; export MP4; render diagnostics

**Use when:** A HyperFrames task requires command syntax, build/render diagnostics, timeline inspection or output verification.

**Do not use when:** Generic Node CLI problems, assuming a successful encode proves visual quality, or initiating cloud publication without the user requesting it.

**Overlaps and default:** Supports the selected video workflow and hyperframes-core; it does not replace creative direction. Preserve project wrappers and pinned versions.

**Requirements:** Node 22+, FFmpeg and a working HyperFrames CLI/browser environment. Verify per task. Preview/render and provider requirements depend on the workflow and existing authorization. Toolkit installation alone does not provide this runtime.

**Expected output:** Verified command results, preview or rendered artifact, with duration/media and visual checks as applicable.

**Positive example:** "Diagnose why this HyperFrames render fails and validate the output after fixing it."

**Negative example:** "Deploy our React application to a web host."

**Source:** [Pinned SKILL.md](../vendor/hyperframes/skills/hyperframes-cli/SKILL.md)
