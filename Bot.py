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

REPORT_CATEGORY_ID = 1491264107364745216
BUY_CATEGORY_ID = 1491264209969872997
ADMINSHIP_CATEGORY_ID = 1491264151786360855

ALLOWED_CATEGORY_ID = 1487387217017045134

# =========================
# STORAGE
# =========================
active_tickets = {}

# =========================
# KEEP ALIVE
# =========================
app = Flask('')

@app.route('/')
def home():
    return "Bot is running."

def keep_alive():
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()

# =========================
# BOT
# =========================
class Bot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        self.add_view(TicketView())

    async def on_ready(self):
        print(f"✅ Logged in as {self.user}")

bot = Bot()

# =========================
# CALCULATOR
# =========================
class CalculatorModal(discord.ui.Modal, title="XP Calculator"):
    start_lvl = discord.ui.TextInput(label="Start Level")
    target_lvl = discord.ui.TextInput(label="Target Level")
    current_xp = discord.ui.TextInput(label="Current XP", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            start = int(self.start_lvl.value)
            target = int(self.target_lvl.value)
            xp = int(self.current_xp.value or 0)
        except:
            return await interaction.response.send_message("❌ Numbers only.", ephemeral=True)

        total = sum(50 * (lvl * lvl + 2) for lvl in range(start, target))
        total = max(0, total - xp)

        MINI, SMALL, MED, VAST = 125000, 250000, 500000, 1000000
        r = total

        vast = r // VAST; r %= VAST
        med = r // MED; r %= MED
        small = r // SMALL; r %= SMALL
        mini = r // MINI + (1 if r % MINI else 0)

        cost = mini*7 + small*12 + med*18 + vast*34
        time = mini*5 + small*10 + med*25 + vast*30
        h, m = divmod(time, 60)

        embed = discord.Embed(title="XP Calculator", color=discord.Color.blurple())
        embed.add_field(name="Levels", value=f"{start} → {target}", inline=False)
        embed.add_field(name="XP Needed", value=f"{total:,}", inline=False)
        embed.add_field(name="Cost", value=f"{cost} 💎", inline=False)
        embed.add_field(name="Time", value=f"{h}h {m}m", inline=False)

        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="calc")
async def calc(interaction: discord.Interaction):
    if not interaction.channel or not interaction.channel.category or interaction.channel.category.id != ALLOWED_CATEGORY_ID:
        return await interaction.response.send_message("❌ Wrong channel.", ephemeral=True)

    await interaction.response.send_modal(CalculatorModal())

# =========================
# TICKET SYSTEM
# =========================
async def create_ticket(interaction, category_id, t_type, msg, perms):
    uid = interaction.user.id

    if uid not in active_tickets:
        active_tickets[uid] = {}

    if t_type in active_tickets[uid]:
        return await interaction.response.send_message(
            f"❌ You already have a {t_type} ticket!",
            ephemeral=True
        )

    await interaction.response.defer(ephemeral=True)

    category = interaction.guild.get_channel(category_id)
    channel = await interaction.guild.create_text_channel(
        name=f"{t_type}-{interaction.user.name}",
        category=category,
        overwrites=perms
    )

    active_tickets[uid][t_type] = channel

    await channel.send(f"{interaction.user.mention} {msg}", view=CloseView(t_type))
    await interaction.followup.send(f"✅ {channel.mention}", ephemeral=True)

class CloseView(discord.ui.View):
    def __init__(self, t_type):
        super().__init__(timeout=None)
        self.t_type = t_type

    @discord.ui.button(
        label="🔒 Close",
        style=discord.ButtonStyle.red,
        custom_id="close_ticket"  # ✅ REQUIRED
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id

        if uid in active_tickets and self.t_type in active_tickets[uid]:
            del active_tickets[uid][self.t_type]
            if not active_tickets[uid]:
                del active_tickets[uid]

        await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def perms(self, i):
        return {
            i.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            i.user: discord.PermissionOverwrite(view_channel=True)
        }

    @discord.ui.button(
        label="💰 Buy",
        style=discord.ButtonStyle.green,
        custom_id="ticket_buy"
    )
    async def buy(self, i: discord.Interaction, b: discord.ui.Button):
        await create_ticket(i, BUY_CATEGORY_ID, "buy", "💰 Buy ticket created.", self.perms(i))

    @discord.ui.button(
        label="🚨 Report",
        style=discord.ButtonStyle.red,
        custom_id="ticket_report"
    )
    async def report(self, i: discord.Interaction, b: discord.ui.Button):

        owner = i.guild.get_member(OWNER_ID) or await i.guild.fetch_member(OWNER_ID)

        overwrites = {
            i.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            i.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            owner: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        await create_ticket(i, REPORT_CATEGORY_ID, "report", "🚨 Private report created.", overwrites)

    @discord.ui.button(
        label="💼 Admin",
        style=discord.ButtonStyle.blurple,
        custom_id="ticket_admin"
    )
    async def admin(self, i: discord.Interaction, b: discord.ui.Button):
        await create_ticket(i, ADMINSHIP_CATEGORY_ID, "admin", "💼 Admin request created.", self.perms(i))
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
            "🚨 Report – Private report "
        ),
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(embed=embed, view=TicketView())

# =========================
# RUN
# =========================
keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
