import os
import discord
from discord import app_commands
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

load_dotenv()

# ==========================================
# 🔒 ALLOWED CATEGORY ID
# ==========================================
ALLOWED_CATEGORY_ID = 1487387217017045134  # ⬅️ REPLACE THIS

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
    server_thread.daemon = True
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

    start_lvl = discord.ui.TextInput(
        label='Start Level',
        placeholder='e.g. 1'
    )

    target_lvl = discord.ui.TextInput(
        label='Target Level',
        placeholder='e.g. 40'
    )

    current_xp = discord.ui.TextInput(
        label='Current XP',
        required=False,
        placeholder='0'
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            start = int(self.start_lvl.value)
            target = int(self.target_lvl.value)
            xp_owned = int(self.current_xp.value.strip() or 0)
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
        # COST
        # ==========================================
        total_dl = (mini * 7) + (small * 12) + (mediant * 18) + (vast * 34)

        # ==========================================
        # TIME
        # ==========================================
        total_time = (
            (mini * 5) +
            (small * 10) +
            (mediant * 25) +
            (vast * 30)
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

        embed.add_field(name="📊 Levels", value=f"{start} ➜ {target}", inline=False)
        embed.add_field(name="📈 Total XP Needed", value=f"{total_xp:,}", inline=False)

        packs_text = ""
        if vast:
            packs_text += f"📦 {vast}x Vast Pack (34💎)\n"
        if mediant:
            packs_text += f"📦 {mediant}x Mediant Pack (18💎)\n"
        if small:
            packs_text += f"📦 {small}x Small Pack (12💎)\n"
        if mini:
            packs_text += f"📦 {mini}x Mini Pack (7💎)\n"

        embed.add_field(name="📦 Recommended Packs", value=packs_text or "None", inline=False)
        embed.add_field(name="💰 Total Cost", value=f"{total_dl} 💎 Diamond Locks", inline=False)
        embed.add_field(name="⏱️ Estimated Time", value=f"{hours}h {minutes}m", inline=False)

        await interaction.response.send_message(embed=embed)

# ==========================================
# 4. BOT
# ==========================================
bot = CalculatorBot()

# 🔒 CATEGORY CHECK FOR COMMAND
@bot.tree.command(name="calc", description="Open XP Calculator")
async def calc(interaction: discord.Interaction):

    if (
        interaction.channel is None or
        interaction.channel.category is None or
        interaction.channel.category.id != ALLOWED_CATEGORY_ID
    ):
        return await interaction.response.send_message(
            "❌ This command can only be used in the allowed category.",
            ephemeral=True
        )

    await interaction.response.send_modal(CalculatorModal())

# ==========================================
# 🎫 TICKET SYSTEM
# ==========================================
OWNER_ID = 1409138196775702599  # ⬅️ YOUR ID

SUPPORT_CATEGORY_ID = 1466995318246609069
REPORT_CATEGORY_ID = 1491264107364745216
BUY_CATEGORY_ID = 1491264209969872997
ADMINSHIP_CATEGORY_ID = 1491264151786360855

# =========================
# STORAGE
# =========================
active_tickets = {}

# =========================
# CLOSE BUTTON
# =========================
class CloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

# =========================
# TICKET SYSTEM
# =========================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_ticket(self, interaction, category_id, prefix, message, overwrites):
        global ticket_counter

        user_id = interaction.user.id
        guild = interaction.guild
        category = guild.get_channel(category_id)

        # ❌ prevent duplicate
        if user_id in active_tickets:
            ch = guild.get_channel(active_tickets[user_id])
            if ch:
                return await interaction.response.send_message(
                    f"❌ You already have a ticket: {ch.mention}",
                    ephemeral=True
                )

        # 🔢 PERMANENT NUMBER
        ticket_counter += 1
        save_counter(ticket_counter)

        ticket_number = str(ticket_counter).zfill(3)
        channel_name = f"{prefix}-{ticket_number}"

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        active_tickets[user_id] = channel.id

        await channel.send(
            f"{interaction.user.mention}\n{message}\n\n🎫 Ticket Number: #{ticket_number}",
            view=CloseView()
        )

        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention} (#{ticket_number})",
            ephemeral=True
        )

    # 💰 BUY
    @discord.ui.button(label="💰 Buy", style=discord.ButtonStyle.blurple)
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        staff_role = discord.utils.get(interaction.guild.roles, name="Staff")
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        await self.create_ticket(
            interaction,
            BUY_CATEGORY_ID,
            "buy",
            "💰 Buy ticket created. Our team will assist you.",
            overwrites
        )

    # 🚨 REPORT (OWNER ONLY)
    @discord.ui.button(label="🚨 Report", style=discord.ButtonStyle.red)
    async def report(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message(
                "❌ Only the owner can use this.",
                ephemeral=True
            )

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.guild.get_member(OWNER_ID): discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True
            )
        }

        await self.create_ticket(
            interaction,
            REPORT_CATEGORY_ID,
            "report",
            "🚨 Private report (owner only).",
            overwrites
        )

    # 💼 ADMINSHIP (OWNER ONLY)
    @discord.ui.button(label="💼 Buy Adminship", style=discord.ButtonStyle.green)
    async def adminship(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message(
                "❌ Only the owner can use this.",
                ephemeral=True
            )

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.guild.get_member(OWNER_ID): discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True
            )
        }

        await self.create_ticket(
            interaction,
            ADMINSHIP_CATEGORY_ID,
            "adminship",
            "💼 Adminship request (owner only).",
            overwrites
        )

# =========================
# PANEL COMMAND
# =========================
@bot.tree.command(name="ticket_panel", description="Send ticket panel")
async def ticket_panel(interaction: discord.Interaction):

    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message(
            "❌ Owner only.",
            ephemeral=True
        )

    embed = discord.Embed(
        title="🎫 SUPPORT CENTER",
        description=(
            "Click a button below to create a ticket:\n\n"
            "💼 Buy Adminship – Apply for admin\n"
            "💰 Buy – Purchase help\n"
            "🚨 Report – Private report (owner only can see)"
        ),
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(embed=embed, view=TicketView())

# ==========================================
# 5. RUN
# ==========================================
keep_alive()

token = os.getenv("DISCORD_TOKEN")
bot.run(token)
