# animate

**Purpose:** Implement purposeful web UI motion, including timing, interruption, exit behavior and reduced motion.

**Invocation:** automatic

**Use when:** A specific component needs a transition, entrance, feedback animation or gesture-related motion implemented.

**Do not use when:** Video export, React Native animation, naming an effect, or a request only to audit an entire codebase.

**Overlaps and default:** Default for building web motion. Use animate-expo for React Native, animation-performance for jank, and find-animation-opportunities to decide where motion is worthwhile before building.

**Requirements:** Target web component, its interaction frequency, existing motion tokens and browser verification. Use the simplest supported mechanism; a new animation dependency is not automatically required.

**Expected output:** Working animation code with interruption, pointer and reduced-motion behavior; sometimes a reason to leave an interaction unanimated.

**Positive example:** "Animate this popover opening from its trigger and closing smoothly."

**Negative example:** "Export a 10-second animated logo as an MP4."

**Source:** [Pinned SKILL.md](../vendor/emil/skills/animate/SKILL.md)
