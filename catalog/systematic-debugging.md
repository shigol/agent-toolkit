# systematic-debugging

**Purpose:** Find the root cause of a bug, test failure or unexpected behavior before proposing or applying a fix.

**Invocation:** automatic

**Route:** Diagnose a bug, failed run or wrong result

**Synonyms:** debug; debugging; diagnose; troubleshoot; failure; failed; bug; bugs; regression; root cause; incorrect

**Use when:** A test fails, a build, run or pipeline step breaks, output is wrong or missing, or behavior is unexpected, and the task is to diagnose or fix it. Also when an earlier fix did not work.

**Do not use when:** Writing new features with no failure involved, UI or motion design, prose editing, product strategy, or only judging whether supplied results prove completion (use verification-before-completion).

**Overlaps and default:** Distinct from verification-before-completion, which checks evidence before a success claim; this skill investigates causes before a fix. Use it first when something is broken, then verification-before-completion before reporting the fix done. Complements the project's "five whys" and root-cause rules; project instructions still govern.

**Requirements:** Access to the failing code, logs or command and permission to run the project's own checks. The bundled `find-polluter.sh` is an optional bash helper for finding a test that leaves files behind; it runs only the project's tests and is never run automatically. Instructions are readable by Claude and Codex; live host selection is not yet verified. Source references to delegating to other agents do not authorize spawning agents.

**Expected output:** A stated root cause backed by reproduced evidence, then a minimal fix with a test or check that failed before and passes after, or an accurate report of what is still unknown.

**Positive example:** "The nightly crawl dropped half the jobs from one source since Tuesday. Find out why and fix it."

**Negative example:** "Write a PRD for a new saved-search feature."

**Source:** [Pinned SKILL.md](../vendor/systematic-debugging/skills/SKILL.md)
