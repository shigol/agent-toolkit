# Shared agent toolkit

Read README.md and USAGE.md before using or modifying this toolkit.
Keep vendor files unchanged. Their SHA-256 hashes and upstream commit IDs live in toolkit.lock.json.
Update upstream collections deliberately, preserving licenses and notice files, and regenerate their manifest hashes.
Never commit credentials, downloaded engines, browser profiles, or project data here.
Run `python3 -m unittest discover -s tests -v` and `python3 scripts/toolkit.py verify-sources` before committing.
Project PRODUCT.md, DESIGN.md and explicit user requirements govern design work. Installations expose skills; they do not authorize running all of them together.
