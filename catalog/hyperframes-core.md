# hyperframes-core

**Purpose:** Define the technical structure of a renderable HyperFrames HTML composition.

**Invocation:** automatic

**Use when:** Writing or editing composition timing, clips, tracks, variables, media playback or sub-compositions.

**Do not use when:** Choosing a creative workflow from scratch, general website HTML or standalone UI animation.

**Overlaps and default:** Supporting contract used by video workflows. hyperframes owns routing; motion-graphics/general-video own their creative workflows; hyperframes-cli owns commands and verification.

**Requirements:** A chosen workflow and composition project. Read the specific references for timing/media/sub-compositions. Running validation/rendering needs the HyperFrames runtime; instructions alone do not install it.

**Expected output:** Deterministic composition structure/code consistent with framework timing and media ownership.

**Positive example:** "Fix the clip timing and nested scene structure in this HyperFrames composition."

**Negative example:** "Write semantic HTML for our website contact form."

**Source:** [Pinned SKILL.md](../vendor/hyperframes/skills/hyperframes-core/SKILL.md)
