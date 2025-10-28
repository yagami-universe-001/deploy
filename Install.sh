#!/bin/bash

# Yagami VPS Bot - Quick Installation Script
# This script automates the installation process

set -e

echo "🎌 Yagami VPS Bot - Installation Script"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${YELLOW}Warning: Running as root. Consider using a non-root user.${NC}"
   sleep 2
fi

# Check OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo -e "${GREEN}✓ Linux OS detected${NC}"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${GREEN}✓ macOS detected${NC}"
else
    echo -e "${RED}✗ Unsupported OS${NC}"
    exit 1
fi

# Check Python
echo ""
echo "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓ Python $PYTHON_VERSION installed${NC}"
else
    echo -e "${RED}✗ Python 3 not found${NC}"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Check pip
if command -v pip3 &> /dev/null; then
    echo -e "${GREEN}✓ pip3 installed${NC}"
else
    echo -e "${RED}✗ pip3 not found${NC}"
    echo "Installing pip3..."
    sudo apt-get install python3-pip -y || brew install python3
fi

# Check Git
echo ""
echo "Checking Git installation..."
if command -v git &> /dev/null; then
    echo -e "${GREEN}✓ Git installed${NC}"
else
    echo -e "${YELLOW}Installing Git...${NC}"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update
        sudo apt-get install git -y
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install git
    fi
fi

# Create virtual environment
echo ""
echo "Setting up virtual environment..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists${NC}"
else
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate || . venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create .env file
echo ""
if [ -f ".env" ]; then
    echo -e "${YELLOW}.env file already exists${NC}"
    read -p "Do you want to overwrite it? (y/N): " overwrite
    if [[ $overwrite != "y" && $overwrite != "Y" ]]; then
        echo "Keeping existing .env file"
    else
        create_env=true
    fi
else
    create_env=true
fi

if [ "$create_env" = true ]; then
    echo "Creating .env file..."
    cp .env.example .env
    
    echo ""
    echo "Please enter your bot configuration:"
    echo ""
    
    read -p "Bot Token (from @BotFather): " bot_token
    read -p "Your Telegram User ID (from @userinfobot): " user_id
    
    # Update .env file
    sed -i.bak "s/your_bot_token_here/$bot_token/" .env
    sed -i.bak "s/123456789,987654321/$user_id/" .env
    rm .env.bak 2>/dev/null || true
    
    echo -e "${GREEN}✓ .env file configured${NC}"
fi

# Optional: Install Docker
echo ""
read -p "Do you want to install Docker? (recommended for Docker deployments) (y/N): " install_docker
if [[ $install_docker == "y" || $install_docker == "Y" ]]; then
    if command -v docker &> /dev/null; then
        echo -e "${GREEN}✓ Docker already installed${NC}"
    else
        echo "Installing Docker..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            curl -fsSL https://get.docker.com -o get-docker.sh
            sudo sh get-docker.sh
            sudo usermod -aG docker $USER
            rm get-docker.sh
            echo -e "${GREEN}✓ Docker installed${NC}"
            echo -e "${YELLOW}Note: You may need to log out and log back in for Docker permissions${NC}"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            echo -e "${YELLOW}Please install Docker Desktop from: https://www.docker.com/products/docker-desktop${NC}"
        fi
    fi
fi

# Optional: Install Node.js
echo ""
read -p "Do you want to install Node.js? (for Node.js deployments) (y/N): " install_node
if [[ $install_node == "y" || $install_node == "Y" ]]; then
    if command -v node &> /dev/null; then
        echo -e "${GREEN}✓ Node.js already installed${NC}"
    else
        echo "Installing Node.js..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
            sudo apt-get install nodejs -y
            echo -e "${GREEN}✓ Node.js installed${NC}"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            brew install node
            echo -e "${GREEN}✓ Node.js installed${NC}"
        fi
    fi
fi

# Create systemd service (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo ""
    read -p "Do you want to create a systemd service? (runs bot in background) (y/N): " create_service
    if [[ $create_service == "y" || $create_service == "Y" ]]; then
        CURRENT_DIR=$(pwd)
        VENV_PYTHON="$CURRENT_DIR/venv/bin/python"
        SERVICE_FILE="/etc/systemd/system/yagami-bot.service"
        
        echo "Creating systemd service..."
        sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=Yagami VPS Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$CURRENT_DIR
Environment="PATH=$CURRENT_DIR/venv/bin"
ExecStart=$VENV_PYTHON bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        sudo systemctl daemon-reload
        sudo systemctl enable yagami-bot
        
        echo -e "${GREEN}✓ Systemd service created${NC}"
        echo ""
        echo "Service commands:"
        echo "  Start:   sudo systemctl start yagami-bot"
        echo "  Stop:    sudo systemctl stop yagami-bot"
        echo "  Status:  sudo systemctl status yagami-bot"
        echo "  Logs:    sudo journalctl -u yagami-bot -f"
    fi
fi

# Summary
echo ""
echo "========================================"
echo -e "${GREEN}✓ Installation Complete!${NC}"
echo "========================================"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Make sure your .env file has correct BOT_TOKEN and ADMIN_IDS"
echo "   Edit with: nano .env"
echo ""
echo "2. Start the bot:"
if [[ "$OSTYPE" == "linux-gnu"* ]] && [[ $create_service == "y" || $create_service == "Y" ]]; then
    echo "   sudo systemctl start yagami-bot"
else
    echo "   source venv/bin/activate"
    echo "   python bot.py"
fi
echo ""
echo "3. Open your bot in Telegram and send /start"
echo ""
echo "4. Connect your VPS with:"
echo "   /addvps YOUR_VPS_IP username password"
echo ""
echo "5. Deploy your first bot with:"
echo "   /deploy https://github.com/user/repo botname auto"
echo ""
echo "📚 For detailed documentation, see:"
echo "   - README.md"
echo "   - SETUP_GUIDE.md"
echo ""
echo "🎌 Happy deploying!"
echo ""
