# Skill selection catalogue

Selection guides for the 29 registered shared skills, reviewed against the pinned sources on 2026-10-27. These are toolkit-owned summaries; the original SKILL.md files and licenses remain unchanged. Local project procedures and unregistered supporting HyperFrames guides are outside this inventory.

## How to use it

Use the short index to locate a candidate, read its guide, then read its source SKILL.md and only the references needed for the task. Do not load all guides at thread startup. This catalogue documents choices; it does not implement search, guarantee activation or prove runtime availability.

User instructions and project requirements govern the work. A skill matching the subject does not automatically match the requested action. Prefer the most specific applicable workflow; use no skill when none adds value. Choose one primary design workflow and add supporting skills only for distinct work. Reassess when a task changes phase.

- `automatic`: eligible when the task fits; not a requirement to invoke it.
- `explicit-only`: the pinned source sets `disable-model-invocation: true`. Requires the user to invoke that skill; generic task wording or direct-file fallback does not bypass this restriction.
- `explicit-direction`: toolkit policy reserves Taste for an explicitly chosen alternative direction. Its source has no manual-only flag. General UI work defaults to Impeccable.

Claude hosted project threads may need to read source files directly. Codex and Claude Code can use their native skill mechanisms where available. A filesystem link does not prove discovery. See [USAGE.md](../USAGE.md) for host behavior and shared update/runtime rules.

For all HyperFrames entries, distinguish video output from live application motion. Read the selected supporting workflow directly from the bundled tree when it is not registered. Preserve toolkit versions instead of following upstream commands that refresh skills. Verify production prerequisites for the actual task; cloud rendering, publication and feedback uploads require an explicit user request. Existing user authorization takes precedence over redundant approval prompts.

## Index

| Skill | Choose for | Invocation |
| --- | --- | --- |
| [impeccable](impeccable.md) | Product UI design and refinement | automatic |
| [design-taste-frontend](design-taste-frontend.md) | Alternative visual direction | explicit-direction |
| [animate](animate.md) | Build web interaction motion | automatic |
| [animate-expo](animate-expo.md) | Build React Native and Expo motion | automatic |
| [animation-performance](animation-performance.md) | Diagnose web animation jank | automatic |
| [animation-vocabulary](animation-vocabulary.md) | Name a motion effect | automatic |
| [apple-design](apple-design.md) | Fluid Apple-style web interactions | automatic |
| [ask-sonner](ask-sonner.md) | Use or troubleshoot Sonner toasts | automatic |
| [break-ui](break-ui.md) | Stress-test UI content | automatic |
| [emil-design-eng](emil-design-eng.md) | Polish component behavior and craft | automatic |
| [find-animation-opportunities](find-animation-opportunities.md) | Find worthwhile places for motion | automatic |
| [improve-animations](improve-animations.md) | Audit existing motion and plan fixes | automatic |
| [mobile-native](mobile-native.md) | Fix mobile web platform behavior | automatic |
| [pick-ui-library](pick-ui-library.md) | Choose a frontend dependency | explicit-only |
| [prototype](prototype.md) | Compare interactive UI variants | explicit-only |
| [review-animations](review-animations.md) | Review a motion diff | explicit-only |
| [write-swift](write-swift.md) | Write and review Swift code | automatic |
| [humanizer](humanizer.md) | Edit prose without changing facts | automatic |
| [hyperframes](hyperframes.md) | Choose a video workflow | automatic |
| [hyperframes-core](hyperframes-core.md) | Build valid video compositions | automatic |
| [hyperframes-cli](hyperframes-cli.md) | Operate and verify HyperFrames | automatic |
| [motion-graphics](motion-graphics.md) | Produce a short motion graphic | automatic |
| [general-video](general-video.md) | Create a custom video composition | automatic |
| [create-prd](create-prd.md) | Write or review feature requirements | automatic |
| [prioritization-frameworks](prioritization-frameworks.md) | Choose and apply a prioritization method | automatic |
| [market-sizing](market-sizing.md) | Estimate a market opportunity | automatic |
| [north-star-metric](north-star-metric.md) | Define product success metrics | automatic |
| [product-strategy](product-strategy.md) | Set product direction and tradeoffs | automatic |
| [verification-before-completion](verification-before-completion.md) | Check fresh task evidence before claiming code, tests or a requested change is complete. | automatic |

## Before adding or changing a skill

1. Explain its distinct job and compare it with existing skills. Prefer updating an existing guide over adding a duplicate capability.
2. Add `catalog/<registered-name>.md` using the fields in any existing guide: purpose, invocation, positive/negative scope, overlaps/default, requirements, expected output, positive and negative request examples, and the exact pinned source link.
3. Read the source instructions and invocation restrictions; do not infer capabilities from the title. Document platform/version needs and whether the workflow plans, reviews or implements.
4. Register the skill and its source/license hashes as described in [README.md](../README.md). Add its row here and review the related guides when defaults overlap. Recheck the guide when updating its source.
5. Run `python3 -m unittest discover -s tests -v` and `python3 scripts/toolkit.py verify-sources`. Catalogue checks reject missing/extra guides, incomplete fields, wrong source links and incompatible manual-only labels. Those structural checks do not prove the descriptions are semantically correct or that an agent chooses well.

Examples in these guides are selection examples, not measured behavioral test results. Next, the automatic-selection work should evaluate these examples and paraphrases in both actual hosts, including tasks that need no skill and transitions between research, design and implementation.
