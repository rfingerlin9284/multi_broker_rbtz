# PURGE & CLOUD RECOVERY 🔐

**Dry-run summary**

RICK> SHOW:PURGE

**Execute purge (requires PIN)**

RICK> RUN:PURGE --all --confirm --no-backup

CHANGE PROPOSAL → requires APPROVE 841921

**Cloud restore**

RICK> RUN:RECOVER SOURCE=<cloud_url> AUTH=ENV:CLOUD_KEY
RICK> RUN:RECOVER VERIFY --checksum=sha256
RICK> RUN:RECOVER REBUILD_ENV --from-frozen --no-cache
RICK> RUN:RECOVER VALIDATE --from-csv-sources --no-cache --clean-room \
--spec=/config/validation/validation_spec.csv \
--out=audits/post_recovery_audit_<UTC>.json

**Targets**: Data 100%, Env 100%, Strategy coverage 100%, Performance ≥95% of baseline Institutional.