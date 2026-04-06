import os
import discord
from discord import app_commands
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

load_dotenv()

# ==========================================
# 1. KEEP-ALIVE WEB SERVER
# ==========================================
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
        await self.tree.sync()

    async def on_ready(self):
        print(f"✅ Logged in as {self.user}")

# ==========================================
# 3. CALCULATOR MODAL
# ==========================================
class CalculatorModal(discord.ui.Modal, title='XP & Pack Calculator'):
    start_lvl = discord.ui.TextInput(label='Start Level', placeholder='e.g. 1')
    target_lvl = discord.ui.TextInput(label='Target Level', placeholder='e.g. 40')
    current_xp = discord.ui.TextInput(label='Current XP', required=False, default='0')

    async def on_submit(self, interaction: discord.Interaction):
        try:
            start = int(self.start_lvl.value)
            target = int(self.target_lvl.value)
            xp_owned = int(self.current_xp.value or 0)
        except ValueError:
            return await interaction.response.send_message(
                "❌ Please use numbers only.", ephemeral=True
            )

        # ==========================================
        # XP CALCULATION
        # ==========================================
        total_xp = 0
        for lvl in range(start, target):
            total_xp += 50 * (lvl * lvl + 2)

        total_xp = max(0, total_xp - xp_owned)

        # ==========================================
        # PACK CALCULATION
        # ==========================================
        MINI_XP = 125_000
        SMALL_XP = 250_000
        MEDIANT_XP = 500_000
        VAST_XP = 1_000_000

        remaining = total_xp

        vast = remaining // VAST_XP
        remaining %= VAST_XP

        mediant = remaining // MEDIANT_XP
        remaining %= MEDIANT_XP

        small = remaining // SMALL_XP
        remaining %= SMALL_XP

        mini = remaining // MINI_XP
        if remaining % MINI_XP > 0:
            mini += 1

        # ==========================================
        # COST CALCULATION
        # ==========================================
        total_dl = (mini * 7) + (small * 12) + (mediant * 17) + (vast * 30)

        # ==========================================
        # ⏱️ TIME PER PACK (minutes)
        # ==========================================
        MINI_TIME = 5
        SMALL_TIME = 10
        MEDIANT_TIME = 25
        VAST_TIME = 30

        total_time = (
            (mini * MINI_TIME) +
            (small * SMALL_TIME) +
            (mediant * MEDIANT_TIME) +
            (vast * VAST_TIME)
        )

        hours = total_time // 60
        minutes = total_time % 60

        # ==========================================
        # EMBED
        # ==========================================
        embed = discord.Embed(
            title="XP & Pack Calculator",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="📊 Levels",
            value=f"{start} ➜ {target}",
            inline=False
        )

        embed.add_field(
            name="📈 Total XP Needed",
            value=f"{total_xp:,}",
            inline=False
        )

        packs_text = ""
        if vast:
            packs_text += f"📦 {vast}x Vast Pack (30💎)\n"
        if mediant:
            packs_text += f"📦 {mediant}x Mediant Pack (17💎)\n"
        if small:
            packs_text += f"📦 {small}x Small Pack (12💎)\n"
        if mini:
            packs_text += f"📦 {mini}x Mini Pack (7💎)\n"

        embed.add_field(
            name="📦 Recommended Packs",
            value=packs_text or "None",
            inline=False
        )

        embed.add_field(
            name="💰 Total Cost",
            value=f"{total_dl} 💎 Diamond Locks",
            inline=False
        )

        # ⏱️ NEW TIME FIELD
        embed.add_field(
            name="⏱️ Estimated Time",
            value=f"{hours}h {minutes}m",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

# ==========================================
# 4. BOT + COMMAND
# ==========================================
bot = CalculatorBot()

@bot.tree.command(name="calc", description="Open XP Calculator")
async def calc(interaction: discord.Interaction):
    await interaction.response.send_modal(CalculatorModal())

# ==========================================
# 5. RUN
# ==========================================
keep_alive()
token = os.getenv("DISCORD_TOKEN")
bot.run(token)
