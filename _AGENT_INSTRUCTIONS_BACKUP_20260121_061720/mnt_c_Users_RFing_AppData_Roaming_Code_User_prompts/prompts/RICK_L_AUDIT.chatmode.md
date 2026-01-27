# AUDIT — Compliance & Secret Hygiene

RICK> RUN:AUDIT ROOT=./ \
--grep 'passphrase|api-fxpractice|practice|paper|sandbox|demo' \
--secrets-literals --dotenv-perms=0600 \
--out=audits/compliance_<UTC>.md