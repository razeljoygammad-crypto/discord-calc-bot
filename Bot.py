import os
import discord
from discord import app_commands
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

load_dotenv()
# =========================
# 🔒 CONFIG
# =========================
OWNER_ID = 923096413934616596  # ⬅️ YOUR ID

SUPPORT_CATEGORY_ID = 1466995318246609069
REPORT_CATEGORY_ID = 1491264107364745216
BUY_CATEGORY_ID = 1491264209969872997
ADMINSHIP_CATEGORY_ID = 1491264151786360855

# ==========================================
# 🔒 ALLOWED CATEGORY ID
# ==========================================
ALLOWED_CATEGORY_ID = 1487387217017045134  # ⬅️ REPLACE THIS

# =========================
# STORAGE
# =========================
active_tickets = {}
ticket_counter = 0

def save_counter(value):
    global ticket_counter
    ticket_counter = value

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
    self.add_view(CloseView())  # 🔥 IMPORTANT
    self.add_view(TicketView()) # 🔥 for ticket buttons
   
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


# =========================
# SETUP
# =========================
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

# =========================
# CLOSE BUTTON
# =========================
class CloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.channel:
            return

        await interaction.response.send_message("🔒 Closing ticket...", ephemeral=True)
        await interaction.channel.delete()


# =========================
# TICKET SYSTEM
# =========================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_ticket(self, interaction, category_id, prefix, message, overwrites):
        global ticket_counter

        user = interaction.user
        guild = interaction.guild

        # prevent duplicate tickets
        if user.id in active_tickets:
            ch = guild.get_channel(active_tickets[user.id])
            if ch:
                return await interaction.response.send_message(
                    f"❌ You already have a ticket: {ch.mention}",
                    ephemeral=True
                )

        # get category properly
        category = discord.utils.get(guild.categories, id=category_id)
        if category is None:
            return await interaction.response.send_message(
                "❌ Category not found. Check your IDs.",
                ephemeral=True
            )

        # ticket number
        ticket_counter += 1
        save_counter(ticket_counter)

        ticket_number = str(ticket_counter).zfill(3)
        channel_name = f"{prefix}-{ticket_number}"

        # create channel
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        active_tickets[user.id] = channel.id

        # send inside ticket
        await channel.send(
            f"{user.mention}\n{message}\n\n🎫 Ticket #{ticket_number}",
            view=CloseView()
        )

        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )

    # 💰 BUY
    @discord.ui.button(label="💰 Buy", style=discord.ButtonStyle.green)
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        await self.create_ticket(
            interaction,
            BUY_CATEGORY_ID,
            "buy",
            "💰 Buy ticket created. Staff will assist you.",
            overwrites
        )

    # 🚨 REPORT
    @discord.ui.button(label="🚨 Report", style=discord.ButtonStyle.red)
    async def report(self, interaction: discord.Interaction, button: discord.ui.Button):

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        await self.create_ticket(
            interaction,
            REPORT_CATEGORY_ID,
            "report",
            "🚨 Report ticket created.",
            overwrites
        )

    # 💼 ADMINSHIP
    @discord.ui.button(label="💼 Adminship", style=discord.ButtonStyle.blurple)
    async def adminship(self, interaction: discord.Interaction, button: discord.ui.Button):

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        await self.create_ticket(
            interaction,
            ADMINSHIP_CATEGORY_ID,
            "adminship",
            "💼 Adminship request created.",
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
            "Click a button below:\n\n"
            "💰 Buy – Purchase help\n"
            "🚨 Report – Report something\n"
            "💼 Adminship – Apply for admin"
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
