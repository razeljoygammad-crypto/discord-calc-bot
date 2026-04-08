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
        total_dl = (mini * 7) + (small * 12) + (mediant * 17) + (vast * 30)

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
            packs_text += f"📦 {vast}x Vast Pack (30💎)\n"
        if mediant:
            packs_text += f"📦 {mediant}x Mediant Pack (17💎)\n"
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
