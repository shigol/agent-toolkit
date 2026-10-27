# Shared agent toolkit

Read README.md and USAGE.md before using or modifying this toolkit.
Keep vendor files unchanged except documented portability patches. Record the upstream hash, patched hash, reason and patch file in toolkit.lock.json; retain the upstream commit ID and licenses.
Update upstream collections deliberately, preserving licenses and notice files, and regenerate their manifest hashes.
Never commit credentials, downloaded engines, browser profiles, or project data here.
Run `python3 -m unittest discover -s tests -v` and `python3 scripts/toolkit.py verify-sources` before committing.
Project PRODUCT.md, DESIGN.md and explicit user requirements govern design work. Installations expose skills; they do not authorize running all of them together.
