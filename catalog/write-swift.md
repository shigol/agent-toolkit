# write-swift

**Purpose:** Apply modern Swift guidance to types, concurrency, memory management, APIs and tests.

**Invocation:** automatic

**Route:** Write Swift interface code

**Synonyms:** Swift; SwiftUI; UIKit; native Apple interface; iOS component

**Use when:** The affected code is Swift and the task involves implementation, migration, concurrency errors, hangs or ARC issues.

**Do not use when:** React/TypeScript work, a website that merely looks native, or choosing a product visual style.

**Overlaps and default:** Prefer this for Swift language/runtime issues. apple-design concerns physical web interactions; animate-expo concerns RN rather than Swift.

**Requirements:** Actual project toolchain and deployment targets. The pinned guide assumes Swift 6.3 and flags newer features; inspect compatibility before using its concurrency advice. Build/test with the appropriate Swift/Xcode environment.

**Expected output:** Compatible Swift code or review findings with relevant compilation/tests where available.

**Positive example:** "Fix this Swift actor-isolation error without introducing a data race."

**Negative example:** "Make a React settings page look like an iOS screen."

**Source:** [Pinned SKILL.md](../vendor/emil/skills/write-swift/SKILL.md)
