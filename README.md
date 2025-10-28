# 🎌 Yagami VPS Bot

A powerful Telegram bot that turns your VPS into a deployment platform. Deploy GitHub repositories (Docker, Python, Node.js, etc.) directly through Telegram commands!

## ✨ Features

- 🚀 **One-Click Deployment** - Deploy GitHub repos with a single command
- 🐳 **Multi-Language Support** - Auto-detects Docker, Python, and Node.js projects
- 📊 **Real-time Monitoring** - Check bot status, logs, and VPS resources
- 🔄 **Bot Management** - Start, stop, and remove deployed bots
- 🔒 **Admin-Only Access** - Secure with admin user ID whitelist
- 📋 **Log Viewer** - View bot logs directly in Telegram
- 💾 **VPS Integration** - SSH connection to your VPS for full control

## 🎯 Use Cases

- Deploy and manage multiple Telegram bots
- Host Discord bots, web scrapers, or APIs
- Run automated tasks and cron jobs
- Test projects in a production environment
- Manage services without SSH terminal access

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/yagami-vps-bot.git
cd yagami-vps-bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add:
- Your bot token from [@BotFather](https://t.me/BotFather)
- Your Telegram user ID (get from [@userinfobot](https://t.me/userinfobot))

```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_IDS=123456789,987654321
```

### 4. Run the Bot

```bash
python bot.py
```

Or use Docker:

```bash
docker build -t yagami-bot .
docker run -d --env-file .env yagami-bot
```

## 🚀 Usage

### Setup VPS Connection

First, connect your VPS to the bot:

```
/addvps <host> <username> <password> [port]
```

Example:
```
/addvps 192.168.1.100 root mypassword 22
```

Or using SSH key:
```
/addvps <host> <username> key <key_path> [port]
```

### Deploy a Bot

Deploy any GitHub repository:

```
/deploy <repo_url> <bot_name> [type]
```

Examples:

```bash
# Auto-detect project type
/deploy https://github.com/user/telegram-bot mybot auto

# Force Docker deployment
/deploy https://github.com/user/app myapp docker

# Force Python deployment
/deploy https://github.com/user/script myscript python

# Force Node.js deployment
/deploy https://github.com/user/nodejs-bot nodebot nodejs
```

### Bot Commands

- `/start` - Open main menu
- `/deploy <repo> <name> [type]` - Deploy a GitHub repository
- `/addvps <host> <user> <pass>` - Connect to VPS

### Interactive Menu

Use the inline buttons to:
- 🤖 View all deployed bots
- ➕ Add new bots
- ⏹️ Stop/▶️ Start bots
- 📋 View logs
- 🗑️ Remove bots
- 🖥️ Check VPS settings
- 📊 Monitor VPS status

## 🔧 Supported Project Types

### 🐳 Docker Projects
- Automatically detects `Dockerfile`
- Builds and runs containers
- Supports Docker Compose projects

### 🐍 Python Projects
- Detects `requirements.txt`
- Creates virtual environment
- Installs dependencies and runs `main.py`

### 📦 Node.js Projects
- Detects `package.json`
- Runs `npm install`
- Starts with `npm start`

## 📋 Requirements

- Python 3.8+
- VPS with SSH access
- Git installed on VPS
- Docker (optional, for Docker deployments)

## 🔐 Security

- **Admin-only access**: Only whitelisted user IDs can use the bot
- **SSH encryption**: Secure connection to your VPS
- **Environment variables**: Sensitive data stored in `.env`
- **No data logging**: Bot doesn't store credentials permanently

## 📸 Screenshots

### Main Menu
```
🎌 Yagami VPS Bot Manager

Welcome! Manage your VPS deployments directly from Telegram.

[🤖 Deployed Bots] [➕ Add New Bot]
[🖥️ VPS Settings] [📊 VPS Status]
```

### Deployed Bots
```
🤖 DEPLOYED BOTS INFO

🤖 3 | 🟢 2 | 🔴 1

🤖 1. @tgfilexbot
🟢 RUNNING

🤖 2. @tgfilex2bot
🟢 RUNNING

🤖 3. @fayefilebot
🔴 STOPPED
```

## 🛠️ Advanced Configuration

### Multiple VPS Support (Coming Soon)

```python
# Add multiple VPS connections
VPS_CONNECTIONS = {
    'default': {...},
    'backup': {...},
    'production': {...}
}
```

### Custom Deployment Scripts

Create a `deploy.sh` in your repository for custom deployment:

```bash
#!/bin/bash
# Custom deployment script
echo "Starting custom deployment..."
# Your custom commands here
```

## 🐛 Troubleshooting

### Bot not connecting to VPS
- Check SSH credentials
- Verify VPS firewall allows SSH (port 22)
- Ensure SSH service is running on VPS

### Deployment fails
- Check if Git is installed on VPS: `git --version`
- Verify repository URL is correct
- Check VPS has enough disk space: `df -h`

### Bot shows "STOPPED" but it's running
- Check deployment logs: Use "📋 View Logs" button
- Verify PID file exists in deployment directory
- For Docker: Check `docker ps`

## 📚 Examples

### Example 1: Deploy a Telegram Bot

```bash
/deploy https://github.com/python-telegram-bot/python-telegram-bot-raw mytelegrambot python
```

### Example 2: Deploy a Discord Bot

```bash
/deploy https://github.com/user/discord-bot mydiscordbot auto
```

### Example 3: Deploy a Web API

```bash
/deploy https://github.com/user/fastapi-app myapi docker
```

### Example 4: Deploy a Node.js Application

```bash
/deploy https://github.com/user/express-app expressapp nodejs
```

## 🔄 Auto-Restart on Failure

The bot uses different restart mechanisms:

- **Docker**: `--restart always` flag ensures containers restart
- **Python/Node.js**: Use `nohup` for persistence across SSH sessions
- **Systemd** (recommended): Create systemd services for production

### Create Systemd Service

```bash
sudo nano /etc/systemd/system/mybot.service
```

```ini
[Unit]
Description=My Telegram Bot
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/home/yourusername/yagami_deployments/mybot
ExecStart=/home/yourusername/yagami_deployments/mybot/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable mybot
sudo systemctl start mybot
```

## 📊 VPS Status Information

The bot displays:
- 💾 **Disk Usage**: Available storage space
- 🧠 **Memory Usage**: RAM consumption
- ⚙️ **CPU Load**: System load averages
- 🐳 **Docker Status**: Running containers

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest new features
- Submit pull requests
- Improve documentation

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This bot provides SSH access to your VPS. Use it responsibly and only share access with trusted admins. Always use strong passwords and SSH keys.

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [Paramiko](https://github.com/paramiko/paramiko) - SSH implementation for Python

## 💬 Support

- Create an issue for bug reports
- Star ⭐ this repo if you find it useful
- Share with others who might benefit

## 🔮 Roadmap

- [ ] Multiple VPS support
- [ ] Scheduled deployments
- [ ] Automatic updates from GitHub
- [ ] Database backup integration
- [ ] Web dashboard
- [ ] Deployment rollback feature
- [ ] Resource usage alerts
- [ ] GitHub Actions integration

## 📞 Contact

Created with ❤️ by Yagami Team

---

**⚡ Quick Start:**
```bash
git clone https://github.com/yourusername/yagami-vps-bot.git
cd yagami-vps-bot
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
python bot.py
```

Happy Deploying! 🚀
