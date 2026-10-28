# Shared agent toolkit

Read README.md and USAGE.md before using or modifying this toolkit.
Keep vendor files unchanged except documented portability patches. Record the upstream hash, patched hash, reason and patch file in toolkit.lock.json; retain the upstream commit ID and licenses.
Update upstream collections deliberately, preserving licenses and notice files, and regenerate their manifest hashes.
Never commit credentials, downloaded engines, browser profiles, or project data here.
Run `python3 -m unittest discover -s tests -v` and `python3 scripts/toolkit.py verify-sources` before committing.
Every registered skill requires a selection guide and index row under catalog/. Follow catalog/README.md for admission and update its guide when the source changes. Follow WORKING-PLAN.md for the automatic-selection rollout and record evidence honestly.
Project PRODUCT.md, DESIGN.md and explicit user requirements govern design work. Installations expose skills; they do not authorize running all of them together.

For agent collaboration, follow CONTINUITY.md "Proactive agent collaboration": own timely acknowledgement, follow-up and the final outcome; a posted handoff alone is not progress.
