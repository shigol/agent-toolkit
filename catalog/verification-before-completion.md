# verification-before-completion

**Purpose:** Check fresh task evidence before claiming code, tests or a requested change is complete.

**Invocation:** automatic

**Route:** Write/run tests; verify code; technical completion claims

**Synonyms:** verify; verification; fresh evidence; test results; passing; completion; done; ready to ship

**Use when:** A development task reaches its verification or completion-report phase, or the user asks whether existing results justify a success claim.

**Do not use when:** General prose editing, initial feature design, choosing a product strategy, or treating a statement by another agent as proof.

**Overlaps and default:** Adds a development verification workflow absent from the existing UI, video, writing and PM collections. Supports the selected implementation skill after its work; does not replace project-specific checks. Run verification appropriate to the actual claim and follow explicit user/project constraints.

**Requirements:** Access to the changed work, the relevant verification command and its fresh complete output/exit code. No additional CLI beyond the project's actual checks. Instructions are readable by Claude and Codex; live host execution is not yet verified. Do not claim a full build from a linter or invent runtime access. Source references to delegation do not authorize spawning agents.

**Expected output:** A completion report grounded in observed checks, or an accurate failure/unverified status with the specific remaining gap.

**Positive example:** "Check these test results and the changed behavior before telling me the fix is complete."

**Negative example:** "Explore visual directions for our pricing page."

**Source:** [Pinned SKILL.md](../vendor/verification-before-completion/skills/SKILL.md)
