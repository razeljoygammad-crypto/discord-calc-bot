import os
import discord
from discord import app_commands
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# ==========================================
# 1. KEEP-ALIVE WEB SERVER
# ==========================================
# This lightweight server runs in the background. 
# It prevents free cloud platforms from putting the bot to sleep.
app = Flask('')

@app.route('/')
def home():
    return "Bot is online and running."

def run_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    server_thread = Thread(target=run_server)
    server_thread.start()

# ==========================================
# 2. DISCORD BOT SETUP
# ==========================================
class CalculatorBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Synchronize slash commands with the Discord server
        await self.tree.sync()

# ==========================================
# 3. CALCULATOR UI & LOGIC
# ==========================================
class CalculatorModal(discord.ui.Modal, title='XP & Pack Calculator'):
    start_lvl = discord.ui.TextInput(label='Start Level', placeholder='e.g. 1', max_length=3)
    target_lvl = discord.ui.TextInput(label='Target Level', placeholder='e.g. 40', max_length=3)
    current_xp = discord.ui.TextInput(label='Current XP ', required=False, default='0')
    end_xp = discord.ui.TextInput(label='End XP ', required=False, default='0')

    async def on_submit(self, interaction: discord.Interaction):
        # Data validation: Ensure inputs are integer
        try:
            start = int(self.start_lvl.value)
            target = int(self.target_lvl.value)
            xp_owned = int(self.current_xp.value or 0)
            end_xp = int(self.end_xp.value or 0)
        except ValueError:
            return await interaction.response.send_message("Invalid input. Please use numbers only.", ephemeral=True)

        # XP Calculation
        total_xp = 0
        current = start
        
        while current < target:
            total_xp += 50 * (current * current + 2)
            current += 1
        
        # Deduct already owned XP, preventing negative values
        total_xp = max(0, total_xp - xp_owned)

        # Pack Calculation Logic
        mini = small = mediant = vast = 0
        
        if start == 1:
            if target <= 20: 
                mini = 1
            elif target <= 25: 
                small = 1
            elif target <= 30: 
                mediant = 1
            elif target <= 40: 
                vast = 1
            else:
                vast = total_xp // 1_100_000
                rem = total_xp % 1_100_000
                if rem > 500_000: vast += 1
                elif rem > 250_000: mediant = 1
                elif rem > 125_000: small = 1
                elif rem > 0: mini = 1
        else:
            vast = total_xp // 1_100_000
            rem = total_xp % 1_100_000
            
            if rem > 500_000: mediant = 1
            elif rem > 250_000: small = 1
            elif rem > 0: mini = 1

        # Calculate cost in Diamond Locks
        total_dl = (mini * 7) + (small * 12) + (mediant * 17) + (vast * 30)

        # Format and send the response message
        msg = f"💎 **Total XP Needed:** {total_xp:,}\n\n"
        msg += "**Recommended Packs:**\n"
        
        if vast > 0: msg += f"📦 {vast}x Vast Pack (30 DL each)\n"
        if mediant > 0: msg += f"📦 {mediant}x Mediant Pack (17 DL each)\n"
        if small > 0: msg += f"📦 {small}x Small Pack (12 DL each)\n"
        if mini > 0: msg += f"📦 {mini}x Mini Pack (7 DL each)\n"
        
        msg += f"\n🔒 **Total Cost:** {total_dl} Diamond Locks"

        await interaction.response.send_message(msg, ephemeral=True)

# ==========================================
# 4. COMMAND REGISTRATION & EXECUTION
# ==========================================
client = CalculatorBot()

@client.tree.command(name="calc", description="Open the XP calculator")
async def calc_command(interaction: discord.Interaction):
    await interaction.response.send_modal(CalculatorModal())

@client.event
async def on_ready():
    print(f'System Online: Logged in as {client.user}')

if __name__ == "__main__":
    # 1. Start the web server to keep the bot alive
    keep_alive()  
    
    # 2. Load the hidden token securely
    bot.run(TOKEN)
