# Hive Agent Chrome Setup - All-in-One
# Run this with: Right-click > Run with PowerShell (as Administrator)

Write-Host "=== Hive Agent Chrome Setup ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Add Firewall Rule
Write-Host "Step 1: Adding Windows Firewall rule for port 9222..." -ForegroundColor Yellow

try {
    $existingRule = Get-NetFirewallRule -DisplayName "Chrome Remote Debugging (Hive)" -ErrorAction SilentlyContinue
    if ($existingRule) {
        Write-Host "  Firewall rule already exists - skipping" -ForegroundColor Green
    } else {
        New-NetFirewallRule -DisplayName "Chrome Remote Debugging (Hive)" `
            -Direction Inbound `
            -LocalPort 9222 `
            -Protocol TCP `
            -Action Allow `
            -Profile Private,Domain | Out-Null
        Write-Host "  Firewall rule added successfully!" -ForegroundColor Green
    }
} catch {
    Write-Host "  Warning: Could not add firewall rule" -ForegroundColor Red
    Write-Host "  You may need to run this script as Administrator" -ForegroundColor Red
    Write-Host "  Right-click this file > Run as Administrator" -ForegroundColor Yellow
}

Write-Host ""

# Step 2: Kill existing Chrome instances
Write-Host "Step 2: Closing existing Chrome instances..." -ForegroundColor Yellow
Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Write-Host "  Done" -ForegroundColor Green

Write-Host ""

# Step 3: Launch Chrome with Remote Debugging
Write-Host "Step 3: Launching Chrome with Remote Debugging..." -ForegroundColor Yellow

$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$userDataDir = "$env:LOCALAPPDATA\Google\Chrome-Hive"
$chromeArgs = @(
    "--remote-debugging-port=9222",
    "--user-data-dir=$userDataDir",
    "https://chatgpt.com/"
)

if (Test-Path $chromePath) {
    Start-Process -FilePath $chromePath -ArgumentList $chromeArgs
    Write-Host "  Chrome launched!" -ForegroundColor Green
} else {
    Write-Host "  Error: Chrome not found at $chromePath" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Setup Complete! ===" -ForegroundColor Green
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "  1. Login to ChatGPT in the Chrome window that just opened" -ForegroundColor White
Write-Host "  2. Keep Chrome running in the background" -ForegroundColor White
Write-Host "  3. In WSL terminal, run:" -ForegroundColor White
Write-Host "     systemctl --user restart hive_worker.service" -ForegroundColor Yellow
Write-Host ""
Write-Host "The Hive worker will connect to this Chrome session automatically!" -ForegroundColor Green
Write-Host ""

# Keep window open
Write-Host "Press any key to close this window..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
