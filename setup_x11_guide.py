#!/usr/bin/env python3
"""
WSL X11 SETUP GUIDE
Install X11 server for browser automation in WSL
"""

def show_wsl_x11_setup():
    print("🖥️  WSL X11 SETUP GUIDE")
    print("=" * 50)
    print("This will enable browser automation in WSL")
    print()
    
    print("📥 STEP 1: DOWNLOAD X11 SERVER")
    print("-" * 30)
    print("Choose ONE of these X11 servers:")
    print()
    print("Option A - VcXsrv (Recommended):")
    print("   🌐 Download: https://sourceforge.net/projects/vcxsrv/")
    print("   📦 File: vcxsrv-1.20.14.0.installer.exe")
    print("   💡 Most stable, widely used")
    print()
    print("Option B - Xming:")
    print("   🌐 Download: https://sourceforge.net/projects/xming/")
    print("   📦 File: Xming-6-9-0-31-setup.exe")
    print("   💡 Lighter weight alternative")
    print()
    print("Option C - Windows X410 (Paid):")
    print("   🌐 Microsoft Store: X410")
    print("   💰 ~$10, better performance")
    print()
    
    print("🚀 STEP 2: INSTALL X11 SERVER")
    print("-" * 30)
    print("For VcXsrv (recommended path):")
    print("   1. Run vcxsrv installer as Administrator")
    print("   2. Use default settings")
    print("   3. Allow through Windows Firewall")
    print("   4. Create desktop shortcut")
    print()
    
    print("⚙️  STEP 3: CONFIGURE X11 SERVER")
    print("-" * 30)
    print("VcXsrv Configuration:")
    print("   1. Launch 'XLaunch' from Start Menu")
    print("   2. Select 'Multiple windows'")
    print("   3. Display number: -1")
    print("   4. Check 'Disable access control'")
    print("   5. Save configuration to Desktop")
    print()
    
    print("🐧 STEP 4: CONFIGURE WSL")
    print("-" * 30)
    print("Add to your WSL ~/.bashrc:")
    print()
    print("   # X11 Display forwarding")
    print("   export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0.0")
    print("   export LIBGL_ALWAYS_INDIRECT=1")
    print()
    print("Or run these commands now:")
    print("   echo 'export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk \"{print $2}\"):0.0' >> ~/.bashrc")
    print("   echo 'export LIBGL_ALWAYS_INDIRECT=1' >> ~/.bashrc")
    print("   source ~/.bashrc")
    print()
    
    print("🔧 STEP 5: INSTALL LINUX GUI PACKAGES")
    print("-" * 30)
    print("Install required packages in WSL:")
    print("   sudo apt update")
    print("   sudo apt install -y x11-apps firefox")
    print()
    print("Test X11 with:")
    print("   xeyes")
    print("   (should show floating eyes following mouse)")
    print()
    
    print("🧪 STEP 6: TEST BROWSER AUTOMATION")
    print("-" * 30)
    print("Test Chrome launch:")
    print("   google-chrome --version  # Check if installed")
    print("   google-chrome https://google.com  # Test GUI")
    print()
    print("If Chrome not installed:")
    print("   wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -")
    print("   sudo sh -c 'echo \"deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main\" >> /etc/apt/sources.list.d/google-chrome.list'")
    print("   sudo apt update")
    print("   sudo apt install -y google-chrome-stable")
    print()
    
    print("🎯 STEP 7: LAUNCH AI BROWSER")
    print("-" * 30)
    print("Once X11 working:")
    print("   cd /home/ing/RICK/MULTI_BROKER_PHOENIX")
    print("   python3 hive_real/launch_browser_ai.py")
    print()
    print("You should see:")
    print("   ✅ Chrome window opens")
    print("   ✅ ChatGPT loads automatically")
    print("   ✅ Ready for AI browser automation")
    print()
    
    print("🐛 TROUBLESHOOTING")
    print("-" * 30)
    print("Common issues:")
    print()
    print("1. 'cannot connect to X server':")
    print("   - Start VcXsrv first")
    print("   - Check DISPLAY variable")
    print("   - Disable Windows Firewall temporarily")
    print()
    print("2. 'Permission denied':")
    print("   - Run VcXsrv as Administrator")
    print("   - Check 'Disable access control' in VcXsrv")
    print()
    print("3. Browser doesn't open:")
    print("   - Test with: firefox https://google.com")
    print("   - Install missing dependencies")
    print("   - Check WSL version (WSL2 recommended)")
    print()
    
    print("✅ SUCCESS INDICATORS")
    print("-" * 30)
    print("You'll know it's working when:")
    print("   🖥️  X11 server running (VcXsrv icon in taskbar)")
    print("   👁️  xeyes shows floating eyes")
    print("   🌐 Chrome opens from WSL command")
    print("   🤖 ChatGPT loads in browser")
    print("   📊 Trading system can send prompts to browser")

def create_wsl_setup_script():
    script_content = '''#!/bin/bash
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
'''
    
    with open("/home/ing/RICK/MULTI_BROKER_PHOENIX/setup_wsl_x11.sh", "w") as f:
        f.write(script_content)
    
    print("\n📄 WSL SETUP SCRIPT CREATED")
    print("-" * 30)
    print("Created: setup_wsl_x11.sh")
    print("Run with: bash setup_wsl_x11.sh")

if __name__ == "__main__":
    show_wsl_x11_setup()
    create_wsl_setup_script()
    
    print("\n🚀 QUICK START SUMMARY")
    print("=" * 50)
    print("1. Download VcXsrv: https://sourceforge.net/projects/vcxsrv/")
    print("2. Install and start VcXsrv with 'Disable access control'")
    print("3. Run: bash setup_wsl_x11.sh")
    print("4. Test: xeyes")
    print("5. Launch AI: python3 hive_real/launch_browser_ai.py")