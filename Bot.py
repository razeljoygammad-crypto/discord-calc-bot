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
# CALCULATOR MODAL
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
        # PACK CALCULATION (GREEDY)
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
        # EMBED RESPONSE
        # ==========================================
        embed = discord.Embed(
            title="XP & Pack Calculator",
            color=discord.Color.blurple()
        )

        # 📊 Levels
        embed.add_field(
            name="📊 Levels",
            value=f"{start} ➜ {target}",
            inline=False
        )

        # 📈 XP Needed
        embed.add_field(
            name="📈 Total XP Needed",
            value=f"{total_xp:,}",
            inline=False
        )

        # 📦 Packs
        packs_text = ""
        if vast > 0:
            packs_text += f"📦 {vast}x Vast Pack (30💎)\n"
        if mediant > 0:
            packs_text += f"📦 {mediant}x Mediant Pack (17💎)\n"
        if small > 0:
            packs_text += f"📦 {small}x Small Pack (12💎)\n"
        if mini > 0:
            packs_text += f"📦 {mini}x Mini Pack (7💎)\n"

        embed.add_field(
            name="📦 Recommended Packs",
            value=packs_text or "None",
            inline=False
        )

        # 💰 Cost
        embed.add_field(
            name="💰 Total Cost",
            value=f"{total_dl} 💎 Diamond Locks",
            inline=False
        )

        embed.set_footer(text="XP Calculator System")

        await interaction.response.send_message(embed=embed)

# ==========================================
# SLASH COMMAND
# ==========================================
bot = CalculatorBot()

@bot.tree.command(name="calc", description="Open XP Calculator")
async def calc(interaction: discord.Interaction):
    await interaction.response.send_modal(CalculatorModal())

# ---------------- START ----------------
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

keep_alive()
token = os.getenv('DISCORD_TOKEN')
client.run(token)
