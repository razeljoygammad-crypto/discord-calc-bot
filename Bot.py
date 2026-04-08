import os
import discord
from discord import app_commands
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

load_dotenv()

# =========================
# CONFIG
# =========================
OWNER_ID = 923096413934616596

SUPPORT_CATEGORY_ID = 1466995318246609069
REPORT_CATEGORY_ID = 1491264107364745216
BUY_CATEGORY_ID = 1491264209969872997
ADMINSHIP_CATEGORY_ID = 1491264151786360855

ALLOWED_CATEGORY_ID = 1487387217017045134

# =========================
# STORAGE
# =========================
active_tickets = {}  
# format:
# { user_id: { "buy": channel, "report": channel, "adminship": channel } }

# =========================
# KEEP ALIVE
# =========================
app = Flask('')

@app.route('/')
def home():
    return "Bot is running."

def run_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run_server, daemon=True).start()

# =========================
# BOT CLASS
# =========================
class CalculatorBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.message_content = True

        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        self.add_view(TicketView())  # persistent buttons

    async def on_ready(self):
        print(f"✅ Logged in as {self.user}")

bot = CalculatorBot()

# =========================
# CALCULATOR MODAL
# =========================
class CalculatorModal(discord.ui.Modal, title='XP & Pack Calculator'):

    start_lvl = discord.ui.TextInput(label='Start Level')
    target_lvl = discord.ui.TextInput(label='Target Level')
    current_xp = discord.ui.TextInput(label='Current XP', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            start = int(self.start_lvl.value)
            target = int(self.target_lvl.value)
            xp_owned = int(self.current_xp.value or 0)
        except:
            return await interaction.response.send_message("❌ Numbers only.", ephemeral=True)

        total_xp = sum(50 * (lvl * lvl + 2) for lvl in range(start, target))
        total_xp = max(0, total_xp - xp_owned)

        MINI = 125_000
        SMALL = 250_000
        MED = 500_000
        VAST = 1_000_000

        remaining = total_xp

        vast = remaining // VAST
        remaining %= VAST

        med = remaining // MED
        remaining %= MED

        small = remaining // SMALL
        remaining %= SMALL

        mini = remaining // MINI
        if remaining % MINI:
            mini += 1

        total_dl = (mini*7)+(small*12)+(med*18)+(vast*34)

        time = (mini*5)+(small*10)+(med*25)+(vast*30)
        h, m = divmod(time, 60)

        embed = discord.Embed(title="XP Calculator", color=discord.Color.blurple())
        embed.add_field(name="Levels", value=f"{start} → {target}", inline=False)
        embed.add_field(name="XP Needed", value=f"{total_xp:,}", inline=False)

        packs = []
        if vast: packs.append(f"{vast}x Vast")
        if med: packs.append(f"{med}x Mediant")
        if small: packs.append(f"{small}x Small")
        if mini: packs.append(f"{mini}x Mini")

        embed.add_field(name="Packs", value="\n".join(packs) or "None", inline=False)
        embed.add_field(name="Cost", value=f"{total_dl} 💎", inline=False)
        embed.add_field(name="Time", value=f"{h}h {m}m", inline=False)

        await interaction.response.send_message(embed=embed)

# =========================
# CALC COMMAND
# =========================
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
# CREATE TICKET
# =========================
async def create_ticket(interaction, category_id, ticket_type, message, overwrites):

    user_id = interaction.user.id

    if user_id not in active_tickets:
        active_tickets[user_id] = {}

    # ❌ prevent duplicate SAME TYPE
    if ticket_type in active_tickets[user_id]:
        existing_channel = active_tickets[user_id][ticket_type]
        return await interaction.response.send_message(
            f"❌ You already have an open {ticket_type} ticket: {existing_channel.mention}",
            ephemeral=True
        )

    await interaction.response.defer(ephemeral=True)

    category = interaction.guild.get_channel(category_id)

    if category is None:
        return await interaction.followup.send("❌ Category not found.", ephemeral=True)

    channel = await interaction.guild.create_text_channel(
        name=f"{ticket_type}-{interaction.user.name}",
        category=category,
        overwrites=overwrites
    )

    active_tickets[user_id][ticket_type] = channel

    await channel.send(
        f"{interaction.user.mention} {message}",
        view=CloseView(ticket_type)
    )

    await interaction.followup.send(
        f"✅ Ticket created: {channel.mention}",
        ephemeral=True
    )

# =========================
# CLOSE BUTTON
# =========================
class CloseView(discord.ui.View):
    def __init__(self, ticket_type):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        user_id = interaction.user.id

        if user_id in active_tickets:
            if self.ticket_type in active_tickets[user_id]:
                del active_tickets[user_id][self.ticket_type]

            if not active_tickets[user_id]:
                del active_tickets[user_id]

        await interaction.channel.delete()

# =========================
# TICKET BUTTONS
# =========================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def perms(self, interaction):
        return {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

    @discord.ui.button(label="💰 Buy", style=discord.ButtonStyle.green)
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, BUY_CATEGORY_ID, "buy", "💰 Buy ticket created.", self.perms(interaction))

    @discord.ui.button(label="🚨 Report", style=discord.ButtonStyle.red)
    async def report(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, REPORT_CATEGORY_ID, "report", "🚨 Report ticket created.", self.perms(interaction))

    @discord.ui.button(label="💼 Adminship", style=discord.ButtonStyle.blurple)
    async def adminship(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, ADMINSHIP_CATEGORY_ID, "adminship", "💼 Adminship request created.", self.perms(interaction))

# =========================
# PANEL COMMAND
# =========================
@bot.tree.command(name="ticket_panel", description="Send ticket panel")
async def ticket_panel(interaction: discord.Interaction):

    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ Owner only.", ephemeral=True)

    embed = discord.Embed(
        title="🎫 SUPPORT CENTER",
        description=(
            "💰 Buy – Purchase help\n"
            "🚨 Report – Report issue\n"
            "💼 Adminship – Apply for admin"
        ),
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(embed=embed, view=TicketView())

# =========================
# RUN
# =========================
keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
