# DRIFT CHECK COMMANDS

## Quick Verify - No Modifications Allowed
```bash
# Check all files are still locked
find . -type f -name "*.py" ! -perm 444 -ls 2>/dev/null
# Should return NOTHING if all files are locked
```

## MD5 Hash Manifest (run once after lockdown, compare later)
```bash
# Generate manifest
find . -type f -name "*.py" -exec md5sum {} \; | sort > MANIFEST.md5

# Compare later
find . -type f -name "*.py" -exec md5sum {} \; | sort > /tmp/current.md5
diff MANIFEST.md5 /tmp/current.md5
# Should return NOTHING if no drift
```

## File Count Check
```bash
# Original count (document this after lockdown)
find . -type f -name "*.py" | wc -l

# Current count should match
```

## If Drift Detected - DO NOT MODIFY - RE-EXTRACT FROM SOURCE
