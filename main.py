import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import paramiko
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
ADMIN_IDS = []  # Add your Telegram user IDs here
DEPLOYED_BOTS = {}
VPS_CONNECTIONS = {}

class VPSManager:
    def __init__(self, host, port, username, password=None, key_file=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_file = key_file
        self.ssh = None
        
    def connect(self):
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.key_file:
                self.ssh.connect(
                    self.host, 
                    port=self.port, 
                    username=self.username, 
                    key_filename=self.key_file
                )
            else:
                self.ssh.connect(
                    self.host, 
                    port=self.port, 
                    username=self.username, 
                    password=self.password
                )
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def execute_command(self, command):
        try:
            if not self.ssh:
                if not self.connect():
                    return None, "Failed to connect to VPS"
            
            stdin, stdout, stderr = self.ssh.exec_command(command)
            output = stdout.read().decode()
            error = stderr.read().decode()
            
            return output, error
        except Exception as e:
            return None, str(e)
    
    def deploy_github_repo(self, repo_url, bot_name, deploy_type="auto"):
        commands = []
        
        # Create deployment directory
        commands.append(f"mkdir -p ~/yagami_deployments/{bot_name}")
        commands.append(f"cd ~/yagami_deployments/{bot_name}")
        
        # Clone repository
        commands.append(f"git clone {repo_url} .")
        
        # Detect and deploy based on type
        if deploy_type == "auto":
            # Check for deployment files
            commands.append("""
if [ -f "Dockerfile" ]; then
    echo "DOCKER_DETECTED"
elif [ -f "requirements.txt" ]; then
    echo "PYTHON_DETECTED"
elif [ -f "package.json" ]; then
    echo "NODE_DETECTED"
else
    echo "UNKNOWN_TYPE"
fi
            """)
        
        full_command = " && ".join(commands)
        output, error = self.execute_command(full_command)
        
        return output, error
    
    def deploy_docker(self, bot_name):
        commands = [
            f"cd ~/yagami_deployments/{bot_name}",
            f"docker build -t {bot_name} .",
            f"docker run -d --name {bot_name} --restart always {bot_name}"
        ]
        return self.execute_command(" && ".join(commands))
    
    def deploy_python(self, bot_name):
        commands = [
            f"cd ~/yagami_deployments/{bot_name}",
            "python3 -m venv venv",
            "source venv/bin/activate",
            "pip install -r requirements.txt",
            f"nohup python main.py > logs.txt 2>&1 & echo $! > {bot_name}.pid"
        ]
        return self.execute_command(" && ".join(commands))
    
    def deploy_nodejs(self, bot_name):
        commands = [
            f"cd ~/yagami_deployments/{bot_name}",
            "npm install",
            f"nohup npm start > logs.txt 2>&1 & echo $! > {bot_name}.pid"
        ]
        return self.execute_command(" && ".join(commands))
    
    def stop_bot(self, bot_name):
        commands = [
            f"cd ~/yagami_deployments/{bot_name}",
            f"if [ -f {bot_name}.pid ]; then kill $(cat {bot_name}.pid); fi",
            f"docker stop {bot_name} 2>/dev/null || true"
        ]
        return self.execute_command(" && ".join(commands))
    
    def remove_bot(self, bot_name):
        commands = [
            self.stop_bot(bot_name)[0],
            f"docker rm {bot_name} 2>/dev/null || true",
            f"docker rmi {bot_name} 2>/dev/null || true",
            f"rm -rf ~/yagami_deployments/{bot_name}"
        ]
        return self.execute_command(" && ".join(commands))
    
    def get_bot_status(self, bot_name):
        command = f"""
cd ~/yagami_deployments/{bot_name} 2>/dev/null
if [ -f {bot_name}.pid ]; then
    if ps -p $(cat {bot_name}.pid) > /dev/null; then
        echo "RUNNING"
    else
        echo "STOPPED"
    fi
else
    if docker ps | grep -q {bot_name}; then
        echo "RUNNING"
    else
        echo "STOPPED"
    fi
fi
        """
        output, _ = self.execute_command(command)
        return output.strip() if output else "UNKNOWN"
    
    def get_logs(self, bot_name, lines=50):
        command = f"cd ~/yagami_deployments/{bot_name} && tail -n {lines} logs.txt 2>/dev/null || docker logs --tail {lines} {bot_name} 2>/dev/null"
        return self.execute_command(command)
    
    def close(self):
        if self.ssh:
            self.ssh.close()

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
    
    keyboard = [
        [InlineKeyboardButton("🤖 Deployed Bots", callback_data="deployed_bots")],
        [InlineKeyboardButton("➕ Add New Bot", callback_data="add_new_bot")],
        [InlineKeyboardButton("🖥️ VPS Settings", callback_data="vps_settings")],
        [InlineKeyboardButton("📊 VPS Status", callback_data="vps_status")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎌 *Yagami VPS Bot Manager*\n\n"
        "Welcome! Manage your VPS deployments directly from Telegram.\n\n"
        "Choose an option below:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.edit_message_text("❌ Unauthorized access.")
        return
    
    data = query.data
    
    if data == "deployed_bots":
        await show_deployed_bots(query, context)
    elif data == "add_new_bot":
        await query.edit_message_text(
            "➕ *Add New Bot*\n\n"
            "Send the GitHub repository URL in this format:\n"
            "`/deploy <repo_url> <bot_name> [type]`\n\n"
            "Example:\n"
            "`/deploy https://github.com/user/repo mybot auto`\n\n"
            "Types: auto, docker, python, nodejs",
            parse_mode="Markdown"
        )
    elif data == "vps_settings":
        await show_vps_settings(query, context)
    elif data == "vps_status":
        await show_vps_status(query, context)
    elif data.startswith("bot_"):
        bot_name = data.replace("bot_", "")
        await show_bot_details(query, context, bot_name)
    elif data.startswith("stop_"):
        bot_name = data.replace("stop_", "")
        await stop_bot(query, context, bot_name)
    elif data.startswith("start_"):
        bot_name = data.replace("start_", "")
        await start_bot(query, context, bot_name)
    elif data.startswith("remove_"):
        bot_name = data.replace("remove_", "")
        await remove_bot(query, context, bot_name)
    elif data.startswith("logs_"):
        bot_name = data.replace("logs_", "")
        await show_logs(query, context, bot_name)
    elif data == "back_main":
        keyboard = [
            [InlineKeyboardButton("🤖 Deployed Bots", callback_data="deployed_bots")],
            [InlineKeyboardButton("➕ Add New Bot", callback_data="add_new_bot")],
            [InlineKeyboardButton("🖥️ VPS Settings", callback_data="vps_settings")],
            [InlineKeyboardButton("📊 VPS Status", callback_data="vps_status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🎌 *Yagami VPS Bot Manager*\n\nChoose an option:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

async def show_deployed_bots(query, context):
    if not DEPLOYED_BOTS:
        await query.edit_message_text(
            "📭 *No bots deployed yet*\n\n"
            "Use /deploy to add a new bot.",
            parse_mode="Markdown"
        )
        return
    
    keyboard = []
    status_text = "🤖 *DEPLOYED BOTS INFO*\n\n"
    
    running = sum(1 for bot in DEPLOYED_BOTS.values() if bot.get('status') == 'running')
    stopped = sum(1 for bot in DEPLOYED_BOTS.values() if bot.get('status') == 'stopped')
    
    status_text += f"🤖 {len(DEPLOYED_BOTS)} | 🟢 {running} | 🔴 {stopped}\n\n"
    
    for i, (bot_name, bot_info) in enumerate(DEPLOYED_BOTS.items(), 1):
        status = "🟢 RUNNING" if bot_info.get('status') == 'running' else "🔴 STOPPED"
        status_text += f"🤖 {i}. @{bot_name}\n{status}\n\n"
        keyboard.append([InlineKeyboardButton(f"🤖 {i}", callback_data=f"bot_{bot_name}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(status_text, parse_mode="Markdown", reply_markup=reply_markup)

async def show_bot_details(query, context, bot_name):
    if bot_name not in DEPLOYED_BOTS:
        await query.edit_message_text("❌ Bot not found.")
        return
    
    bot_info = DEPLOYED_BOTS[bot_name]
    
    # Get current status from VPS
    vps = VPSManager(**VPS_CONNECTIONS.get('default', {}))
    status = vps.get_bot_status(bot_name)
    DEPLOYED_BOTS[bot_name]['status'] = 'running' if 'RUNNING' in status else 'stopped'
    
    status_emoji = "🟢" if DEPLOYED_BOTS[bot_name]['status'] == 'running' else "🔴"
    
    text = (
        f"🤖 *Bot: @{bot_name}*\n\n"
        f"Status: {status_emoji} {DEPLOYED_BOTS[bot_name]['status'].upper()}\n"
        f"Type: {bot_info.get('type', 'auto')}\n"
        f"Repository: {bot_info.get('repo', 'N/A')}\n"
        f"Deployed: {bot_info.get('deployed_at', 'N/A')}\n"
    )
    
    keyboard = []
    if DEPLOYED_BOTS[bot_name]['status'] == 'running':
        keyboard.append([InlineKeyboardButton("⏹️ Stop Bot", callback_data=f"stop_{bot_name}")])
    else:
        keyboard.append([InlineKeyboardButton("▶️ Start Bot", callback_data=f"start_{bot_name}")])
    
    keyboard.extend([
        [InlineKeyboardButton("📋 View Logs", callback_data=f"logs_{bot_name}")],
        [InlineKeyboardButton("🗑️ Remove Bot", callback_data=f"remove_{bot_name}")],
        [InlineKeyboardButton("🔙 Back", callback_data="deployed_bots")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def deploy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /deploy <repo_url> <bot_name> [type]\n"
            "Example: /deploy https://github.com/user/repo mybot auto"
        )
        return
    
    repo_url = context.args[0]
    bot_name = context.args[1]
    deploy_type = context.args[2] if len(context.args) > 2 else "auto"
    
    if 'default' not in VPS_CONNECTIONS:
        await update.message.reply_text("❌ VPS not configured. Use /addvps first.")
        return
    
    msg = await update.message.reply_text("🔄 Deploying bot... Please wait.")
    
    vps = VPSManager(**VPS_CONNECTIONS['default'])
    
    # Clone repository
    output, error = vps.deploy_github_repo(repo_url, bot_name, deploy_type)
    
    if error and "DETECTED" not in output:
        await msg.edit_text(f"❌ Deployment failed:\n{error}")
        return
    
    # Deploy based on detected type
    if "DOCKER_DETECTED" in output or deploy_type == "docker":
        output, error = vps.deploy_docker(bot_name)
        deploy_type = "docker"
    elif "PYTHON_DETECTED" in output or deploy_type == "python":
        output, error = vps.deploy_python(bot_name)
        deploy_type = "python"
    elif "NODE_DETECTED" in output or deploy_type == "nodejs":
        output, error = vps.deploy_nodejs(bot_name)
        deploy_type = "nodejs"
    else:
        await msg.edit_text("❌ Could not detect project type. Specify type: docker, python, or nodejs")
        return
    
    if error:
        await msg.edit_text(f"❌ Deployment failed:\n{error}")
        return
    
    DEPLOYED_BOTS[bot_name] = {
        'repo': repo_url,
        'type': deploy_type,
        'status': 'running',
        'deployed_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    await msg.edit_text(
        f"✅ *Bot deployed successfully!*\n\n"
        f"🤖 Name: @{bot_name}\n"
        f"📦 Type: {deploy_type}\n"
        f"🔗 Repo: {repo_url}",
        parse_mode="Markdown"
    )

async def stop_bot(query, context, bot_name):
    vps = VPSManager(**VPS_CONNECTIONS.get('default', {}))
    output, error = vps.stop_bot(bot_name)
    
    if not error:
        DEPLOYED_BOTS[bot_name]['status'] = 'stopped'
        await query.edit_message_text(f"✅ Bot @{bot_name} stopped successfully.")
    else:
        await query.edit_message_text(f"❌ Failed to stop bot:\n{error}")

async def start_bot(query, context, bot_name):
    bot_info = DEPLOYED_BOTS.get(bot_name, {})
    bot_type = bot_info.get('type', 'auto')
    
    vps = VPSManager(**VPS_CONNECTIONS.get('default', {}))
    
    if bot_type == 'docker':
        output, error = vps.execute_command(f"docker start {bot_name}")
    elif bot_type == 'python':
        output, error = vps.deploy_python(bot_name)
    elif bot_type == 'nodejs':
        output, error = vps.deploy_nodejs(bot_name)
    
    if not error:
        DEPLOYED_BOTS[bot_name]['status'] = 'running'
        await query.edit_message_text(f"✅ Bot @{bot_name} started successfully.")
    else:
        await query.edit_message_text(f"❌ Failed to start bot:\n{error}")

async def remove_bot(query, context, bot_name):
    vps = VPSManager(**VPS_CONNECTIONS.get('default', {}))
    output, error = vps.remove_bot(bot_name)
    
    if not error:
        del DEPLOYED_BOTS[bot_name]
        await query.edit_message_text(f"✅ Bot @{bot_name} removed successfully.")
    else:
        await query.edit_message_text(f"❌ Failed to remove bot:\n{error}")

async def show_logs(query, context, bot_name):
    vps = VPSManager(**VPS_CONNECTIONS.get('default', {}))
    output, error = vps.get_logs(bot_name)
    
    if output:
        # Telegram message limit is 4096 characters
        logs = output[-4000:] if len(output) > 4000 else output
        await query.edit_message_text(
            f"📋 *Logs for @{bot_name}*\n\n```\n{logs}\n```",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text("❌ No logs found or failed to retrieve logs.")

async def show_vps_settings(query, context):
    if 'default' in VPS_CONNECTIONS:
        vps_info = VPS_CONNECTIONS['default']
        text = (
            "🖥️ *VPS Settings*\n\n"
            f"Host: {vps_info.get('host', 'N/A')}\n"
            f"Port: {vps_info.get('port', 22)}\n"
            f"Username: {vps_info.get('username', 'N/A')}\n"
            f"Auth: {'Key' if vps_info.get('key_file') else 'Password'}\n"
        )
    else:
        text = "🖥️ *VPS Settings*\n\nNo VPS configured. Use /addvps to add one."
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def show_vps_status(query, context):
    if 'default' not in VPS_CONNECTIONS:
        await query.edit_message_text("❌ VPS not configured.")
        return
    
    vps = VPSManager(**VPS_CONNECTIONS['default'])
    
    # Get system info
    commands = [
        ("💾 Disk Usage", "df -h / | tail -1"),
        ("🧠 Memory Usage", "free -h | grep Mem"),
        ("⚙️ CPU Load", "uptime"),
        ("🐳 Docker Status", "docker ps --format 'table {{.Names}}\t{{.Status}}'")
    ]
    
    text = "📊 *VPS Status*\n\n"
    
    for label, command in commands:
        output, _ = vps.execute_command(command)
        if output:
            text += f"{label}:\n`{output.strip()}`\n\n"
    
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="vps_status")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def addvps_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized.")
        return
    
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /addvps <host> <username> <password> [port]\n"
            "Or: /addvps <host> <username> key <key_file_path> [port]"
        )
        return
    
    host = context.args[0]
    username = context.args[1]
    
    if context.args[2] == "key":
        key_file = context.args[3] if len(context.args) > 3 else None
        password = None
        port = int(context.args[4]) if len(context.args) > 4 else 22
    else:
        password = context.args[2]
        key_file = None
        port = int(context.args[3]) if len(context.args) > 3 else 22
    
    vps = VPSManager(host, port, username, password, key_file)
    
    if vps.connect():
        VPS_CONNECTIONS['default'] = {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'key_file': key_file
        }
        await update.message.reply_text("✅ VPS connected successfully!")
    else:
        await update.message.reply_text("❌ Failed to connect to VPS.")

def main():
    # Get bot token from environment variable
    token = os.getenv('BOT_TOKEN')
    if not token:
        print("Error: BOT_TOKEN not set!")
        return
    
    # Get admin IDs from environment variable
    admin_ids_str = os.getenv('ADMIN_IDS', '')
    if admin_ids_str:
        ADMIN_IDS.extend([int(id.strip()) for id in admin_ids_str.split(',') if id.strip()])
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("deploy", deploy_command))
    application.add_handler(CommandHandler("addvps", addvps_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Start bot
    print("🎌 Yagami VPS Bot started!")
    application.run_polling()

if __name__ == '__main__':
    main()
