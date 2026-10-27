# mobile-native

**Purpose:** Remove browser and touch behaviors that make a mobile website or PWA feel awkward.

**Invocation:** automatic

**Route:** Mobile web interactions and quirks

**Use when:** A web app has sticky hover, tap flashes, viewport/keyboard problems, input zoom, scroll conflicts or safe-area issues.

**Do not use when:** React Native development, Swift programming, motion-graphics export or general desktop visual direction.

**Overlaps and default:** Prefer this for mobile browser behavior before assuming an animation problem. animate handles motion; animate-expo handles actual RN/Expo apps.

**Requirements:** Web app code and target mobile browsers. Hardware testing matters; desktop device emulation does not prove phone behavior. Preserve zoom and accessibility.

**Expected output:** Targeted CSS/meta/interaction fixes with reasons and device-validation limits.

**Positive example:** "The PWA input zooms and the bottom bar hides behind the iPhone keyboard."

**Negative example:** "Build a native Expo gesture animation with Reanimated."

**Source:** [Pinned SKILL.md](../vendor/emil/skills/mobile-native/SKILL.md)
