#!/usr/bin/env bash
# Idempotent: start broker-link + engine-paper and report status
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Starting broker-link and engine-paper (paper default)"
sudo systemctl enable --now rbotzilla-broker-link.service
sudo systemctl enable --now rbotzilla-engine-paper.service

echo "Status:"
systemctl is-active rbotzilla-broker-link rbotzilla-engine-paper || true
