#!/bin/bash
# WSL X11 Setup Script
echo "🐧 Setting up WSL for X11..."

# Add X11 environment variables
echo "📝 Adding X11 variables to ~/.bashrc..."
grep -qF "export DISPLAY=" ~/.bashrc || echo 'export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk "{print $2}"):0.0' >> ~/.bashrc
grep -qF "export LIBGL_ALWAYS_INDIRECT=1" ~/.bashrc || echo 'export LIBGL_ALWAYS_INDIRECT=1' >> ~/.bashrc

# Source the changes
source ~/.bashrc

echo "✅ Environment variables added"
echo "💡 DISPLAY will be: $DISPLAY"

# Update package list
echo "📦 Updating package list..."
sudo apt update

# Install X11 apps for testing
echo "🧪 Installing X11 test applications..."
sudo apt install -y x11-apps

# Install Chrome if not present
if ! command -v google-chrome &> /dev/null; then
    echo "🌐 Installing Google Chrome..."
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
    sudo apt update
    sudo apt install -y google-chrome-stable
else
    echo "✅ Google Chrome already installed"
fi

echo ""
echo "🎯 SETUP COMPLETE!"
echo ""
echo "Next steps:"
echo "1. Download and install VcXsrv on Windows"
echo "2. Start VcXsrv with 'Disable access control' checked"  
echo "3. Test with: xeyes"
echo "4. Test browser: google-chrome https://google.com"
echo "5. Run AI browser: python3 hive_real/launch_browser_ai.py"
