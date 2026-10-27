# animate-expo

**Purpose:** Implement mobile animations and gestures using the React Native/Expo execution model.

**Invocation:** automatic

**Use when:** An actual React Native or Expo app needs a sheet, gesture handoff, screen transition, haptic feedback or animation-thread fix.

**Do not use when:** A website viewed on a phone, Swift-only implementation, or rendered video production.

**Overlaps and default:** Prefer this over animate for React Native. Use mobile-native for browser/PWA touch and viewport issues, and write-swift for Swift code.

**Requirements:** An RN/Expo project and SDK-compatible dependencies such as Reanimated/Worklets and Gesture Handler as needed. Inspect project versions. Performance verification requires a release build on representative supported hardware.

**Expected output:** Mobile motion implementation with accessibility and thread considerations, plus a clear statement of device verification.

**Positive example:** "Build an interruptible swipe-to-dismiss sheet in our Expo app."

**Negative example:** "Our mobile Safari form zooms when an input receives focus."

**Source:** [Pinned SKILL.md](../vendor/emil/skills/animate-expo/SKILL.md)
