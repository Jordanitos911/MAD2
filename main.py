import discord
from discord.ext import commands
import asyncio
import os
import random
from datetime import datetime, timedelta
from discord import ui
import json
from discord.ext import commands

import asyncio
from discord.ui import Button, button, View

import time
import os
from discord.ext import commands, tasks
import time
client = commands.Bot(command_prefix=".", intents=discord.Intents.all())
client.remove_command("help")

# Global dictionary for anti-link warning rate-limiting
last_antilink_warning = {}

import re
import unicodedata

# List of TOS-violating words/phrases (add more as needed)
TOS_WORDS = [
    'nigger', 'nger', 'faggot', 'fag', 'nigr',
]

# --- Global buffer for TOS multi-message detection ---
global_user_message_buffers = {}
MAX_TOS_BUFFER = max(len(word) for word in TOS_WORDS)

# Map for common letter-like emojis and regional indicators to letters
EMOJI_LETTER_MAP = {
    # Regional indicator symbols
    '🇦': 'a', '🇧': 'b', '🇨': 'c', '🇩': 'd', '🇪': 'e', '🇫': 'f', '🇬': 'g', '🇭': 'h', '🇮': 'i', '🇯': 'j',
    '🇰': 'k', '🇱': 'l', '🇲': 'm', '🇳': 'n', '🇴': 'o', '🇵': 'p', '🇶': 'q', '🇷': 'r', '🇸': 's', '🇹': 't',
    '🇺': 'u', '🇻': 'v', '🇼': 'w', '🇽': 'x', '🇾': 'y', '🇿': 'z',
    # Keycap emojis
    '🅰️': 'a', '🅱️': 'b', '🆎': 'ab', '🆑': 'cl', '🆒': 'cool', '🆓': 'free', '🆔': 'id', '🆕': 'new', '🆖': 'ng', '🆗': 'ok', '🆘': 'sos', '🆙': 'up', '🆚': 'vs',
    # Enclosed alphanumerics
    'ⓐ': 'a', 'ⓑ': 'b', 'ⓒ': 'c', 'ⓓ': 'd', 'ⓔ': 'e', 'ⓕ': 'f', 'ⓖ': 'g', 'ⓗ': 'h', 'ⓘ': 'i', 'ⓙ': 'j',
    'ⓚ': 'k', 'ⓛ': 'l', 'ⓜ': 'm', 'ⓝ': 'n', 'ⓞ': 'o', 'ⓟ': 'p', 'ⓠ': 'q', 'ⓡ': 'r', 'ⓢ': 's', 'ⓣ': 't',
    'ⓤ': 'u', 'ⓥ': 'v', 'ⓦ': 'w', 'ⓧ': 'x', 'ⓨ': 'y', 'ⓩ': 'z',
    # Add more as needed
}

# Map for leetspeak numbers to letters
LEET_MAP = {
    '1': 'i',
    '3': 'e',
    '4': 'a',
    '5': 's',
    '6': 'g',
    '7': 't',
    '0': 'o',
    '8': 'b',
}

def demojify_and_normalize(text):
    # Replace mapped emojis with their letter equivalents
    for emoji, letter in EMOJI_LETTER_MAP.items():
        text = text.replace(emoji, letter)
    # Remove all other emojis and non-spacing marks
    text = ''.join(c for c in text if c.isascii() or unicodedata.category(c)[0] != 'So')
    # Now apply the existing normalization
    return normalize(text)

def normalize(text):
    # Replace leetspeak numbers with their letter equivalents
    for leet, letter in LEET_MAP.items():
        text.replace(leet, letter)
    # Remove non-letters
    text = re.sub(r'[^a-zA-Z]', '', text)
    # Collapse all repeated letters to a single letter (e.g. niiiiggggger -> niger)
    text = re.sub(r'(.)\1+', r'\1', text)
    return text.lower()

def is_subsequence(word, text):
    """Return True if all letters of word appear in order in text (subsequence match)."""
    it = iter(text)
    return all(char in it for char in word)

def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

whitelist = []

def is_whitelisted():
    async def predicate(ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            return True
        guild_id = ctx.guild.id
        for entry in whitelist:
            if entry[0] == guild_id and entry[1] > time.time():
                return True
        await ctx.send("You are not whitelisted to use this command in this server.")
        return False
    return commands.check(predicate)



import random
from discord import ButtonStyle
from discord.ext import commands
from discord.ui import View, Button

balances = {}

# Generate a hidden minefield board with one bomb
def generate_board(size=5):
    bomb_position = random.randint(0, size * size - 1)
    return bomb_position

# View for interactive buttons (the minefield)
class MineGameView(View):
    def __init__(self, ctx, bomb_position, amount):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bomb_position = bomb_position
        self.amount = amount
        self.revealed_tiles = 0
        self.size = 5  # 5x5 grid
        self.multiplier = 1.0  # Start with a base multiplier of 1.0
        self.base_multiplier = 1.24  # Starting multiplier after the first safe click
        self.active = True  # To track if the game is active (not cashed out or bomb hit)

        # Create a 5x5 grid of buttons
        for i in range(self.size * self.size):  # 25 buttons for the grid
            button = MineButton(i, bomb_position, self)
            self.add_item(button)

# Button for each tile
class MineButton(Button):
    def __init__(self, position, bomb_position, game_view):
        super().__init__(style=ButtonStyle.secondary, label="❓", row=position // 5)
        self.position = position
        self.bomb_position = bomb_position
        self.game_view = game_view

    # What happens when a button is clicked
    async def callback(self, interaction):
        if not self.game_view.active:
            return  # Game is over, do nothing

        # Ensure that only the player who started the game can click the buttons
        if interaction.user != self.game_view.ctx.author:
            await interaction.response.send_message("❌ You cannot click on this tile. It's not your game!", ephemeral=True)
            return

        if self.position == self.bomb_position:
            # User hit the bomb
            self.style = ButtonStyle.danger
            self.label = '💣'
            self.disabled = True
            await interaction.response.edit_message(content=f"💣 You hit the bomb! You lost {self.game_view.amount} coins.", view=self.game_view)

            # Deduct balance
            user_id = str(self.game_view.ctx.author.id)
            balances[user_id] -= self.game_view.amount

            # End game
            self.game_view.active = False
            # Disable all buttons
            for child in self.game_view.children:
                child.disabled = True
            await interaction.message.edit(view=self.game_view)
        else:
            # Safe click
            self.style = ButtonStyle.success
            self.label = '💎'
            self.disabled = True
            self.game_view.revealed_tiles += 1

            # Increase multiplier
            self.game_view.multiplier = round(self.game_view.base_multiplier + (self.game_view.revealed_tiles * 0.06), 2)

            # Check if user has revealed all safe tiles
            if self.game_view.revealed_tiles == (self.game_view.size * self.game_view.size - 1):
                winnings = int(self.game_view.amount * self.game_view.multiplier)
                user_id = str(self.game_view.ctx.author.id)
                balances[user_id] += winnings
                await interaction.response.edit_message(content=f"🎉 You avoided the bomb and won {winnings} coins!", view=self.game_view)

                # End game
                self.game_view.active = False
                # Disable all buttons
                for child in self.game_view.children:
                    child.disabled = True
                await interaction.message.edit(view=self.game_view)
            else:
                # Update the button in the message without completing the interaction
                await interaction.response.edit_message(view=self.game_view)

# Gamble command
@client.command()
async def gamble(ctx, amount: int):
    user = ctx.author
    user_id = str(user.id)

    # Check if user has enough balance
    if user_id not in balances:
        balances[user_id] = 1000  # Initial balance for new users

    if amount > balances[user_id]:
        await ctx.send(f"💰 You don't have enough balance to gamble {amount}. Your balance is {balances[user_id]}.")
        return

    # Generate the minefield with one bomb
    bomb_position = generate_board()

    # Create the clickable minefield using buttons
    view = MineGameView(ctx, bomb_position, amount)

    await ctx.send("💣 Mine Game Click the tiles to reveal. Avoid the bomb or use `.cashout` to claim your win!", view=view)

    # Register the active game for the user
    client.active_games[ctx.author] = view

# Cashout command
@client.command()
async def cashout(ctx):
    user_id = str(ctx.author.id)

    # Check if the user has an active game
    if ctx.author not in client.active_games:
        await ctx.send("❌ You don't have an active game to cash out!")
        return

    # Retrieve the active game
    game_view = client.active_games[ctx.author]

    # Ensure the game is still active
    if not game_view.active:
        await ctx.send("❌ Your game is over, you can't cash out now!")
        return

    # Calculate winnings
    winnings = int(game_view.amount * game_view.multiplier)
    balances[user_id] += winnings

    # Mark the game as finished
    game_view.active = False

    # Disable all buttons
    for child in game_view.children:
        child.disabled = True

    # Edit the original game message
    await game_view.ctx.send(f"💸 You cashed out and won {winnings} coins at a {game_view.multiplier}x multiplier!", view=game_view)

    # Remove the game from active games
    del client.active_games[ctx.author]

# Command to check balance
@client.command()
async def balance(ctx):
    user_id = str(ctx.author.id)
    if user_id not in balances:
        balances[user_id] = 1000  # Initial balance for new users
    await ctx.send(f"💰 Your balance is {balances[user_id]} coins.")

# Command to give coins to another user
@client.command()
async def give(ctx, member: commands.MemberConverter, amount: int):
    giver_id = str(ctx.author.id)
    receiver_id = str(member.id)

    # Check if the giver has enough balance
    if giver_id not in balances:
        balances[giver_id] = 1000  # Initial balance for new users

    if amount <= 0:
        await ctx.send("❌ You must give a positive amount!")
        return

    if amount > balances[giver_id]:
        await ctx.send(f"💰 You don't have enough balance to give {amount}. Your balance is {balances[giver_id]}.")
        return

    # Add the amount to the receiver's balance
    if receiver_id not in balances:
        balances[receiver_id] = 1000  # Initial balance for new users
    balances[giver_id] -= amount
    balances[receiver_id] += amount

    await ctx.send(f"✅ You have given {amount} coins to {member.mention}!")

# Track active games
client.active_games = {}


# Add this line to enable the command when the bot is ready
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')




@tasks.loop(seconds=60)
async def check_whitelist_expiry():
    current_time = time.time()
    expired_entries = [entry for entry in whitelist if entry[1] <= current_time]
    for entry in expired_entries:
        whitelist.remove(entry)
        guild_id = entry[0]
        guild = client.get_guild(guild_id)
        if guild:
            owner = guild.owner
            if owner:
                try:
                    await owner.send("Your subscription to the bot whitelist has expired. Please resubscribe to continue access.")
                except discord.Forbidden:
                    print(f"Failed to send a DM to the owner of guild {guild_id}.")
        print(f"Bot removed from whitelist for guild {guild_id} due to expiration.")

class TicTacToeButton(discord.ui.Button):
    def __init__(self, x, y):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        # Check if it's the right player's turn
        game = self.view  # Reference to the TicTacToe view
        if interaction.user != game.current_player:
            await interaction.response.send_message(f"It's not your turn!", ephemeral=True)
            return

        # Update the button label and disable it
        self.label = game.current_symbol
        self.style = discord.ButtonStyle.success if game.current_symbol == "X" else discord.ButtonStyle.danger
        self.disabled = True
        game.board[self.x][self.y] = game.current_symbol

        # Check if there's a winner
        if game.check_winner(game.current_symbol):
            for button in game.children:
                button.disabled = True  # Disable all buttons when game is over
            await interaction.response.edit_message(content=f"{game.current_player.mention} wins!", view=game)
            return

        # Check if it's a draw
        if game.is_draw():
            await interaction.response.edit_message(content="It's a draw!", view=game)
            return

        # Switch turns
        game.switch_turn()
        await interaction.response.edit_message(content=f"It's {game.current_player.mention}'s turn!", view=game)

class TicTacToe(discord.ui.View):
    def __init__(self, player1, player2):
        super().__init__()
        self.player1 = player1
        self.player2 = player2
        self.current_player = player1
        self.current_symbol = "X"
        self.board = [["" for _ in range(3)] for _ in range(3)]

        # Create 3x3 grid of buttons
        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y))

    def switch_turn(self):
        # Switch player and symbol
        self.current_player = self.player2 if self.current_player == self.player1 else self.player1
        self.current_symbol = "O" if self.current_symbol == "X" else "X"

    def check_winner(self, symbol):
        # Check rows, columns, and diagonals for a win
        for line in self.board:
            if all(cell == symbol for cell in line):
                return True
        for col in range(3):
            if all(self.board[row][col] == symbol for row in range(3)):
                return True
        if all(self.board[i][i] == symbol for i in range(3)) or all(self.board[i][2-i] == symbol for i in range(3)):
            return True
        return False

    def is_draw(self):
        # If no empty cell remains, it's a draw
        return all(cell for row in self.board for cell in row)

@client.command()
async def knock(ctx, opponent: discord.Member):
    """Start a Tic-Tac-Toe game between two players."""
    if opponent == ctx.author:
        await ctx.send("You cannot play against yourself!")
        return

    await ctx.send(f"Tic-Tac-Toe: {ctx.author.mention} vs {opponent.mention}", view=TicTacToe(ctx.author, opponent))



@client.command()
@is_whitelisted()
async def members(ctx):
    member_count = ctx.guild.member_count
    bot_count = sum(1 for member in ctx.guild.members if member.bot)
    
    non_bot_member_count = member_count - bot_count
    
    embed = discord.Embed(title="", color=0x2a2d30)
    embed.add_field(name="Humans", value=f"**Amount: {non_bot_member_count}**", inline=True)
    embed.add_field(name="Bots", value=f"**Amount: {bot_count}**", inline=True)
    embed.add_field(name="Overall", value=f"**Amount: {member_count}**", inline=True)
    
    await ctx.send(embed=embed)

@client.command()
@is_whitelisted()
async def afk(ctx, *, reason=None):
    embed = discord.Embed(color=0x2a2d30)
    now = datetime.datetime.now(datetime.timezone.utc)
    afk = True 
    start_time = int(now.timestamp())

    while afk:
        if reason is not None:
            embed.description = f'💤 {ctx.author.mention} is AFK: **{reason}** - <t:{start_time}:R>'
        else:
            embed.description = f'💤 {ctx.author.mention} is AFK: **AFK** - <t:{start_time}:R>'
        
        if "msg" not in locals():
            msg = await ctx.reply(embed=embed)
        else:
            await msg.edit(embed=embed)
        
        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel
        
        try:
            user_msg = await client.wait_for('message', timeout=60, check=check)
            afk = False

            # Calculate how long the user was AFK
            end_time = datetime.datetime.now(datetime.timezone.utc)
            time_diff = end_time - now
            seconds = time_diff.total_seconds()

            # Format the time difference
            if seconds < 60:
                time_away = f"{int(seconds)} seconds"
            elif seconds < 3600:
                minutes = seconds // 60
                time_away = f"{int(minutes)} minutes"
            else:
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                time_away = f"{int(hours)} hours and {int(minutes)} minutes"

            # Final update to the AFK message
            final_embed = discord.Embed(color=0x2a2d30)
            if reason is not None:
                final_embed.description = f'💤 {ctx.author.mention} was AFK: **{reason}** - **{time_away}**'
            else:
                final_embed.description = f'💤 {ctx.author.mention} was AFK: **AFK** - **{time_away}**'
            await msg.edit(embed=final_embed)

            # Send welcome back message
            welcome_embed = discord.Embed(color=0x2a2d30)
            welcome_embed.description = f"👋 {user_msg.author.mention} Welcome back, you were away for **{time_away}**."
            await user_msg.reply(embed=welcome_embed)
        
        except asyncio.TimeoutError:
            pass
        
        await asyncio.sleep(1)

import json
alias_file_path = "guild_aliases.json"

def load_aliases():
    try:
        with open(alias_file_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

guild_aliases = load_aliases()


def save_aliases():
    with open(alias_file_path, "w") as f:
        json.dump(guild_aliases, f)


@client.command()
async def roll(ctx):
    # Generate a random number between 1 and 100
    roll_result = random.randint(1, 100)
    
    # Create an embed to show the result
    embed = discord.Embed(
        title="🎲 Dice Roll 🎲",
        description=f"{ctx.author.mention} rolled a **{roll_result}**!",
        color=0x2a2d30  # Updated color
    )
    
    # Send the embed as a response
    await ctx.send(embed=embed)



@client.command()
@commands.has_permissions(administrator=True)
async def reactions(ctx):
    """Creates a reaction roles message for Stock Robux roles"""
    
    # Create the embed
    embed = discord.Embed(
        title="💸 Reaction Roles! 💸",
        description="💰 ｜Stock\n💵 ｜Paypal\n💶 ｜Cashapp\n💴 ｜Crypto",
        color=0x2a2d30
    )
    
    # Send the message and add reactions
    message = await ctx.send(embed=embed)
    
    # Add reactions
    reactions = ['💰', '💵', '💶', '💴']
    for reaction in reactions:
        await message.add_reaction(reaction)
    
    # Store the message info for reaction handling
    guild_id = str(ctx.guild.id)
    if guild_id not in settings:
        settings[guild_id] = {}
    
    settings[guild_id]['reaction_message'] = {
        'message_id': message.id,
        'channel_id': ctx.channel.id,
        'roles': {
            '💰': 1388439272318701688,  # Stock
            '💵': 1388439272318701688,  # Paypal
            '💶': 1388439272318701688,  # Cashapp
            '💴': 1388439272318701688   # Crypto
        }
    }
    save_settings()

@client.event
async def on_raw_reaction_add(payload):
    if payload.user_id == client.user.id:
        return
        
    guild_id = str(payload.guild_id)
    if guild_id not in settings:
        return
        
    guild_settings = settings[guild_id]
    if 'reaction_message' not in guild_settings:
        return
        
    reaction_settings = guild_settings['reaction_message']
    if payload.message_id != reaction_settings['message_id']:
        return
        
    emoji = str(payload.emoji)
    if emoji not in reaction_settings['roles']:
        return
        
    role_id = reaction_settings['roles'][emoji]
    guild = client.get_guild(payload.guild_id)
    role = guild.get_role(role_id)
    
    if role:
        member = guild.get_member(payload.user_id)
        if member:
            await member.add_roles(role)

@client.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == client.user.id:
        return
        
    guild_id = str(payload.guild_id)
    if guild_id not in settings:
        return
        
    guild_settings = settings[guild_id]
    if 'reaction_message' not in guild_settings:
        return
        
    reaction_settings = guild_settings['reaction_message']
    if payload.message_id != reaction_settings['message_id']:
        return
        
    emoji = str(payload.emoji)
    if emoji not in reaction_settings['roles']:
        return
        
    role_id = reaction_settings['roles'][emoji]
    guild = client.get_guild(payload.guild_id)
    role = guild.get_role(role_id)
    
    if role:
        member = guild.get_member(payload.user_id)
        if member:
            await member.remove_roles(role)

@client.command()
@is_whitelisted()
async def react(ctx, *, message_content: str):
    title = None
    description = None
    if "(" in message_content and ")" in message_content:
        start_index = message_content.index("(")
        end_index = message_content.index(")")
        title = message_content[start_index + 1: end_index]
        description = message_content[:start_index] + message_content[end_index + 1:]
    else:
        description = message_content

    message_parts = description.split(" ")
    emoji_input = message_parts[-2]
    role_id = int(message_parts[-1])
    message_text = " ".join(message_parts[:-2])
    role = ctx.guild.get_role(role_id)
    if role is None:
        await ctx.send("Invalid role ID.")
        return

    custom_emoji = None
    if emoji_input.startswith("<") and emoji_input.endswith(">"):
        emoji_id = int(emoji_input.split(":")[-1][:-1])
        custom_emoji = discord.utils.get(ctx.guild.emojis, id=emoji_id)
    else:
        custom_emoji = discord.utils.get(ctx.guild.emojis, name=emoji_input.strip(':'))

    if custom_emoji is None:
        await ctx.send("Invalid emoji.")
        return

    embed = discord.Embed(description=message_text, color=0x2a2d30)
    if title:
        embed.title = title

    # Send the embed
    embed_message = await ctx.send(embed=embed)

    # Add reaction to the embed message
    await embed_message.add_reaction(custom_emoji)

    while True:
        # Define reaction check function
        def check(reaction, user):
            return str(reaction.emoji) == str(custom_emoji) and reaction.message.id == embed_message.id

        # Wait for reaction
        reaction, user = await client.wait_for('reaction_add', check=check)

        # Assign role to the user
        await user.add_roles(role)

        # Define unreaction check function
        def uncheck(reaction, user):
            return str(reaction.emoji) == str(custom_emoji) and reaction.message.id == embed_message.id

        # Wait for unreaction
        reaction, user = await client.wait_for('reaction_remove', check=uncheck)

        # Remove role from the user
        await user.remove_roles(role)


@client.event
async def on_interaction(interaction):
    if isinstance(interaction, discord.Interaction):
        if interaction.type == discord.InteractionType.application_command:
            await client.process_commands(interaction)
        elif interaction.type == discord.InteractionType.component:
            await client.dispatch('dropdown', interaction)

class LockButton(View):
    def __init__(self, channel=None):
        super().__init__(timeout=None)
        self.channel = channel
    
    lock_button_style = discord.ButtonStyle.secondary
    unlock_button_style = discord.ButtonStyle.secondary
    ghost_button_style = discord.ButtonStyle.secondary
    reveal_button_style = discord.ButtonStyle.secondary
    claim_button_style = discord.ButtonStyle.secondary
    view_button_style = discord.ButtonStyle.secondary
    plus_button_style = discord.ButtonStyle.secondary
    minus_button_style = discord.ButtonStyle.secondary
    disconnect_button_style = discord.ButtonStyle.secondary
    
    @button(label="🔒", style=lock_button_style, custom_id="lock_vc")
    async def lock_vc(self, interaction: discord.Interaction, button: Button):
        await self._check_and_execute(interaction, self._lock_action)

    @button(label="🔓", style=unlock_button_style, custom_id="unlock_vc")
    async def unlock_vc(self, interaction: discord.Interaction, button: Button):
        await self._check_and_execute(interaction, self._unlock_action)

    @button(label="👻", style=ghost_button_style, custom_id="ghost_vc")
    async def ghost_vc(self, interaction: discord.Interaction, button: Button):
        await self._check_and_execute(interaction, self._ghost_action)
    
    @button(label="🔍", style=reveal_button_style, custom_id="reveal_vc")
    async def reveal_vc(self, interaction: discord.Interaction, button: Button):
        await self._check_and_execute(interaction, self._reveal_action)
    
    @button(label="🔑", style=claim_button_style, custom_id="claim_vc")
    async def claim_vc(self, interaction: discord.Interaction, button: Button):
        await self._claim_action(interaction, interaction.user.voice.channel)
    
    @button(label="👢", style=disconnect_button_style, custom_id="disconnect_button")
    async def disconnect_button(self, interaction: discord.Interaction, button: Button):
        await self._check_and_execute(interaction, self._disconnect_action)
    
    @button(label="ℹ️", style=view_button_style, custom_id="view_vc")
    async def view_vc(self, interaction: discord.Interaction, button: Button):
        voice_channel = interaction.user.voice.channel
        await self._view_action(interaction, voice_channel)

    @button(label="➕", style=plus_button_style, custom_id="increase_limit_vc")
    async def increase_limit_vc(self, interaction: discord.Interaction, button: Button):
        await self._check_and_execute(interaction, self._increase_limit_action)
        
    @button(label="➖", style=minus_button_style, custom_id="decrease_limit_vc")
    async def decrease_limit_vc(self, interaction: discord.Interaction, button: Button):
        await self._check_and_execute(interaction, self._decrease_limit_action)
        
    async def _check_and_execute(self, interaction, action):
        if interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        
        if interaction.user.voice is None or interaction.user.voice.channel is None:
            await interaction.response.send_message(embed=discord.Embed(description="You are not in a voice channel."), ephemeral=True)
            return
        
        voice_channel = interaction.user.voice.channel
        
        if not voice_channel.name.startswith(interaction.user.name) and action != self._claim_action:
            await interaction.response.send_message(embed=discord.Embed(description="You do not own this voice channel."), ephemeral=True)
            return
        
        await action(interaction, voice_channel)
    
    async def _lock_action(self, interaction, voice_channel):
        await voice_channel.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message(embed=discord.Embed(description=f"{voice_channel.name} has been locked."), ephemeral=True)
    
    async def _unlock_action(self, interaction, voice_channel):
        await voice_channel.set_permissions(interaction.guild.default_role, connect=True)
        await interaction.response.send_message(embed=discord.Embed(description=f"{voice_channel.name} has been unlocked."), ephemeral=True)
    
    async def _ghost_action(self, interaction, voice_channel):
        await voice_channel.set_permissions(interaction.guild.default_role, view_channel=False)
        await interaction.response.send_message(embed=discord.Embed(description=f"{voice_channel.name} is now hidden."), ephemeral=True)
    
    async def _reveal_action(self, interaction, voice_channel):
        await voice_channel.set_permissions(interaction.guild.default_role, view_channel=True)
        await interaction.response.send_message(embed=discord.Embed(description=f"{voice_channel.name} is now revealed to everyone."), ephemeral=True)
    
    async def _claim_action(self, interaction, voice_channel):
        current_owner = await self._get_owner(voice_channel)
        if current_owner and current_owner in voice_channel.members:
            await interaction.response.send_message(embed=discord.Embed(description=f"{voice_channel.name} is already claimed by {current_owner.display_name}."), ephemeral=True)
            return
        
        await voice_channel.edit(name=f"{interaction.user.name}'s Channel")
        await interaction.response.send_message(embed=discord.Embed(description=f"{voice_channel.name} has been claimed by {interaction.user.display_name}."), ephemeral=True)
    
    async def _view_action(self, interaction, voice_channel):
        owner = await self._get_owner(voice_channel)
        owner_info = f"**Owner:** `{owner.display_name} ({owner.id})`" if owner else "**Owner:** `No owner found.`"
        
        locked_emoji = "❌"
        unlocked_emoji = "✅"
        
        lock_status = locked_emoji if voice_channel.overwrites_for(interaction.guild.default_role).connect else unlocked_emoji
        locked_info = f"**Locked:** {lock_status}"
        
        limit_info = f"**Limit:** `{voice_channel.user_limit}`" if voice_channel.user_limit else "**Limit:** `0`"
        
        bitrate_info = f"**Bitrate:** `{voice_channel.bitrate / 1000} kbps`"
        
        connected_info = f"**Connected:** `{len(voice_channel.members)}`"
        
        
        embed = discord.Embed(title=f"{voice_channel.name} Details")
        embed.add_field(name="Voice Channel Information", value=f"{owner_info}\n{locked_info}\n{limit_info}\n{bitrate_info}\n{connected_info}", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _increase_limit_action(self, interaction, voice_channel):
        if voice_channel.user_limit is None:
            await interaction.response.send_message(embed=discord.Embed(description=f"{voice_channel.name} does not have a limit set."), ephemeral=True)
            return
        
        await voice_channel.edit(user_limit=voice_channel.user_limit + 1)
        await interaction.response.send_message(embed=discord.Embed(description=f"Limit for {voice_channel.name} increased to {voice_channel.user_limit + 1}."), ephemeral=True)
    
    async def _decrease_limit_action(self, interaction, voice_channel):
        if voice_channel.user_limit is None:
            await interaction.response.send_message(embed=discord.Embed(description=f"{voice_channel.name} does not have a limit set."), ephemeral=True)
            return
        
        await voice_channel.edit(user_limit=max(0, voice_channel.user_limit - 1))
        await interaction.response.send_message(embed=discord.Embed(description=f"Limit for {voice_channel.name} decreased to {max(0, voice_channel.user_limit - 1)}."), ephemeral=True)
    
    async def _disconnect_action(self, interaction, voice_channel):
        if not voice_channel.name.startswith(interaction.user.name):
            embed = discord.Embed(description="You do not own this voice channel.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        options = [discord.SelectOption(label=f"{member.display_name} ({member.id})", value=str(member.id)) for member in voice_channel.members]
        select = discord.ui.Select(placeholder="Choose a user to disconnect", options=options, custom_id="disconnect_dropdown")
        view = discord.ui.View()
        view.add_item(select)
        
        mention = interaction.user.mention
        embed = discord.Embed(description=f"{mention}, select a user to disconnect:")
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def _get_owner(self, voice_channel):
        for member in voice_channel.members:
            if voice_channel.name.startswith(member.name):
                return member
        return None

@client.command(name="reject", aliases=["vc reject"])
@is_whitelisted()
async def vc_reject(ctx, *, user_input):
    try:
        user_id = int(user_input)
        user = ctx.guild.get_member(user_id)
    except ValueError:
        if ctx.message.mentions:
            user = ctx.message.mentions[0]
        else:
            user = discord.utils.get(ctx.guild.members, name=user_input)
    
    if user is None:
        await ctx.send(embed=discord.Embed(description="User not found."), ephemeral=True)
        return
    
    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send(embed=discord.Embed(description="You are not in a voice channel."), ephemeral=True)
        return
    
    voice_channel = ctx.author.voice.channel
    
    if not voice_channel.name.startswith(ctx.author.name):
        await ctx.send(embed=discord.Embed(description="You do not own this voice channel."), ephemeral=True)
        return
    
    await voice_channel.set_permissions(user, connect=False)
    await ctx.send(embed=discord.Embed(description=f"{user.display_name} has been rejected from {voice_channel.name}."), ephemeral=True)
    
@client.command(name="permit")
@is_whitelisted()
async def permit(ctx, *, user_input):
    try:
        user_id = int(user_input)
        user = ctx.guild.get_member(user_id)
    except ValueError:
        if ctx.message.mentions:
            user = ctx.message.mentions[0]
        else:
            user = discord.utils.get(ctx.guild.members, name=user_input)
    
    if user is None:
        await ctx.send(embed=discord.Embed(description="User not found."), ephemeral=True)
        return
    
    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send(embed=discord.Embed(description="You are not in a voice channel."), ephemeral=True)
        return
    
    voice_channel = ctx.author.voice.channel
    
    if not voice_channel.name.startswith(ctx.author.name):
        await ctx.send(embed=discord.Embed(description="You do not own this voice channel."), ephemeral=True)
        return
    
    await voice_channel.set_permissions(user, connect=True)
    await ctx.send(embed=discord.Embed(description=f"{user.display_name} has been permitted to join {voice_channel.name}."), ephemeral=True)

@client.command()
@is_whitelisted()
@commands.has_permissions(manage_channels=True)
async def mute(ctx, *, user_input):
    try:
        # Try parsing user_input as an integer (user ID)
        user_id = int(user_input)
        user = ctx.guild.get_member(user_id)
    except ValueError:
        # If parsing fails, user_input is not an integer, try mentioning a user or searching by username
        if ctx.message.mentions:
            user = ctx.message.mentions[0]
        else:
            # Try finding user by username
            user = discord.utils.get(ctx.guild.members, name=user_input)
    
    if user is None:
        await ctx.send(embed=discord.Embed(description="User not found."), ephemeral=True)
        return
    
    # Loop through all channels in the guild
    for channel in ctx.guild.channels:
        if isinstance(channel, discord.TextChannel):
            await channel.set_permissions(user, send_messages=False)
    
    await ctx.send(embed=discord.Embed(description=f"{user.display_name} has been muted in all channels."), ephemeral=True)


@client.command()
@is_whitelisted()
@commands.has_permissions(manage_channels=True)
async def unmute(ctx, *, user_input):
    try:
        # Try parsing user_input as an integer (user ID)
        user_id = int(user_input)
        user = ctx.guild.get_member(user_id)
    except ValueError:
        # If parsing fails, user_input is not an integer, try mentioning a user or searching by username
        if ctx.message.mentions:
            user = ctx.message.mentions[0]
        else:
            # Try finding user by username
            user = discord.utils.get(ctx.guild.members, name=user_input)
    
    if user is None:
        await ctx.send(embed=discord.Embed(description="User not found."), ephemeral=True)
        return
    
    # Loop through all channels in the guild
    for channel in ctx.guild.channels:
        if isinstance(channel, discord.TextChannel):
            # Remove user-specific permissions for the channel
            await channel.set_permissions(user, overwrite=None)
    
    await ctx.send(embed=discord.Embed(description=f"{user.display_name} has been unmuted in all channels."), ephemeral=True)

@client.command()
@is_whitelisted()
@commands.has_permissions(manage_channels=True)
async def lock(ctx, *, whitelist_role_id=None):
    await ctx.message.delete()
    channel = ctx.channel
    
    whitelist_role = None
    
    if whitelist_role_id:
        try:
            role_id = int(whitelist_role_id)
            whitelist_role = discord.utils.get(ctx.guild.roles, id=role_id)
        except ValueError:
            whitelist_role = discord.utils.get(ctx.guild.roles, name=whitelist_role_id)
    if ctx.author.guild_permissions.manage_channels:
        await channel.set_permissions(ctx.author, send_messages=True)
    
    # Lock the channel by revoking send message permissions for everyone
    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    
    # If a whitelist role is provided, allow users with that role to send messages
    if whitelist_role:
        await channel.set_permissions(whitelist_role, send_messages=True)
        await ctx.send(embed=discord.Embed(description=f"This channel has been locked. Only users with the role **{whitelist_role.name}** can send messages now."), ephemeral=True)
    else:
        await ctx.send(embed=discord.Embed(description="This channel has been locked. Only administrators can send messages now."), ephemeral=True)

@client.command()
@is_whitelisted()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    if not ctx.guild.me.guild_permissions.kick_members:
        embed = discord.Embed(title="Permission Error", description="I don't have permission to kick members.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    try:
        await member.kick(reason=reason)
        embed = discord.Embed(title="Member Kicked", description=f"{member.mention} has been kicked.", color=discord.Color.default())
        message = await ctx.send(embed=embed)

        if kick_logs_channel is not None:
            log_embed = discord.Embed(title="Kicked Member",  color=discord.Color.default())
            log_embed.add_field(name="Kicked User", value=member.mention, inline=True)
            log_embed.add_field(name="Kicked By", value=ctx.author.mention, inline=True)
            log_embed.add_field(name="Reason", value=reason if reason else "No reason provided", inline=True)
            await kick_logs_channel.send(embed=log_embed)

        await asyncio.sleep(3)
        await message.delete()
    except discord.Forbidden:
        embed = discord.Embed(title="Permission Error", description="I don't have permission to kick this member.", color=discord.Color.red())
        await ctx.send(embed=embed)
    except discord.HTTPException:
        embed = discord.Embed(title="Error", description="Kicking failed due to an error.", color=discord.Color.red())
        await ctx.send(embed=embed)

@kick.error
async def kick_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        embed = discord.Embed(title="Error", description="Invalid member specified.", color=discord.Color.red())
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(title="Error", description="Missing required argument: member.", color=discord.Color.red())
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="Permission Error", description="You don't have permission to use this command.", color=discord.Color.red())
        await ctx.send(embed=embed)




@client.command()
@is_whitelisted()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.message.delete()
    channel = ctx.channel
    
    await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    
    await ctx.send(embed=discord.Embed(description="This channel has been unlocked. Everyone can send messages now."), ephemeral=True)

@client.command()
@is_whitelisted()
@commands.has_permissions(manage_channels=True)
async def nuke(ctx):
    # Get the current channel
    channel = ctx.channel
    
    # Duplicate the channel
    new_channel = await channel.clone()
    
    # Get the position of the original channel
    position = channel.position
    
    # Delete the original channel
    await channel.delete()
    
    # Send an embedded message in the new channel
    embed = discord.Embed(description="This channel has been duplicated.")
    message = await new_channel.send(embed=embed)
    
    # Wait for 5 seconds
    await asyncio.sleep(5)
    
    # Delete the message after 5 seconds
    await message.delete()
    
    await ctx.send(embed=discord.Embed(description=f"The channel has been nuked. A new channel named **{new_channel.name}** has been created."), ephemeral=True)



ticket_count = 0 
claim_notification_channel_id = None
claim_counts = {}

@client.command()
async def tickets(ctx):
    view = discord.ui.View()
    options = [
        discord.SelectOption(label="📩 General Support", value="option_support"),
        discord.SelectOption(label="📝 Staff Application", value="option_application"),
        discord.SelectOption(label="🚨 Staff Report", value="option_report"),
        discord.SelectOption(label="⚖️ Ban Appeal", value="option_appeal"),
        discord.SelectOption(label="💸 Donation Ticket", value="option_donation"),
    ]
    select = discord.ui.Select(placeholder="Make a selection", options=options, custom_id="ticket_dropdown")
    view.add_item(select)
    
    embed = discord.Embed(title="Support Ticket", description="Select the drop down to create a ticket.")
    embed.set_footer(text="Ticket system")
    
    await ctx.send(embed=embed, view=view)

@client.command()
@is_whitelisted()
async def help(ctx):
    view = discord.ui.View()
    options = [
        discord.SelectOption(label="🔨 Moderation", value="helpp_option_1"),
        discord.SelectOption(label="👥 Everyone", value="helpp_option_2"),
        discord.SelectOption(label="🚀 Booster", value="helpp_option_3")
    ]
    select = discord.ui.Select(placeholder="Make a selection", options=options, custom_id="helpp_dropdown")
    view.add_item(select)
    
    embed = discord.Embed(title="Help Categories", description="Select the drop down to choose a help category.")
    embed.set_footer(text="Help system")
    
    await ctx.send(embed=embed, view=view)

# --- Modal Classes for Each Ticket Type ---

class SupportModal(discord.ui.Modal, title='General Support Ticket'):
    def __init__(self, category_id):
        super().__init__()
        self.category_id = category_id
        self.q1 = discord.ui.TextInput(
            label="What do you need help with?",
            placeholder="Briefly describe your issue",
            required=True,
            style=discord.TextStyle.short,
            min_length=1,
            max_length=100
        )
        self.q2 = discord.ui.TextInput(
            label="Please describe your issue in detail.",
            placeholder="Provide as much detail as possible",
            required=True,
            style=discord.TextStyle.paragraph,
            min_length=1,
            max_length=500
        )
        self.add_item(self.q1)
        self.add_item(self.q2)
    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket_channel(
            interaction,
            self.category_id,
            "General Support",
            [
                ("Help Topic", self.q1.value),
                ("Issue Details", self.q2.value)
            ]
        )

class StaffApplicationModal(discord.ui.Modal, title='Staff Application'):
    def __init__(self, category_id):
        super().__init__()
        self.category_id = category_id
        self.q1 = discord.ui.TextInput(
            label="Why do you want to be staff?",
            placeholder="Explain your motivation",
            required=True,
            style=discord.TextStyle.paragraph,
            min_length=1,
            max_length=500
        )
        self.q2 = discord.ui.TextInput(
            label="What experience do you have?",
            placeholder="Describe any relevant experience",
            required=True,
            style=discord.TextStyle.paragraph,
            min_length=1,
            max_length=500
        )
        self.q3 = discord.ui.TextInput(
            label="How many hours can you contribute weekly?",
            placeholder="e.g. 10-20 hours",
            required=True,
            style=discord.TextStyle.short,
            min_length=1,
            max_length=100
        )
        self.add_item(self.q1)
        self.add_item(self.q2)
        self.add_item(self.q3)
    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket_channel(
            interaction,
            self.category_id,
            "Staff Application",
            [
                ("Why do you want to be staff?", self.q1.value),
                ("What experience do you have?", self.q2.value),
                ("How many hours can you contribute weekly?", self.q3.value)
            ]
        )

class StaffReportModal(discord.ui.Modal, title='Staff Report'):
    def __init__(self, category_id):
        super().__init__()
        self.category_id = category_id
        self.q1 = discord.ui.TextInput(
            label="Which staff member are you reporting?",
            placeholder="Enter their Discord tag or username",
            required=True,
            style=discord.TextStyle.short,
            min_length=1,
            max_length=100
        )
        self.q2 = discord.ui.TextInput(
            label="What did they do?",
            placeholder="Describe the incident",
            required=True,
            style=discord.TextStyle.paragraph,
            min_length=1,
            max_length=500
        )
        self.q3 = discord.ui.TextInput(
            label="Do you have any evidence?",
            placeholder="Provide links or details (if any)",
            required=False,
            style=discord.TextStyle.paragraph,
            min_length=0,
            max_length=500
        )
        self.add_item(self.q1)
        self.add_item(self.q2)
        self.add_item(self.q3)
    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket_channel(
            interaction,
            self.category_id,
            "Staff Report",
            [
                ("Staff Member Reported", self.q1.value),
                ("Incident Description", self.q2.value),
                ("Evidence", self.q3.value)
            ]
        )

class BanAppealModal(discord.ui.Modal, title='Ban Appeal'):
    def __init__(self, category_id):
        super().__init__()
        self.category_id = category_id
        self.q1 = discord.ui.TextInput(
            label="What is your Discord username and tag?",
            placeholder="e.g. User#1234",
            required=True,
            style=discord.TextStyle.short,
            min_length=1,
            max_length=100
        )
        self.q2 = discord.ui.TextInput(
            label="Why were you banned?",
            placeholder="Explain the reason for your ban",
            required=True,
            style=discord.TextStyle.paragraph,
            min_length=1,
            max_length=500
        )
        self.q3 = discord.ui.TextInput(
            label="Why should you be unbanned?",
            placeholder="Explain why you should be unbanned",
            required=True,
            style=discord.TextStyle.paragraph,
            min_length=1,
            max_length=500
        )
        self.add_item(self.q1)
        self.add_item(self.q2)
        self.add_item(self.q3)
    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket_channel(
            interaction,
            self.category_id,
            "Ban Appeal",
            [
                ("Discord Username & Tag", self.q1.value),
                ("Ban Reason", self.q2.value),
                ("Unban Reason", self.q3.value)
            ]
        )

class DonationModal(discord.ui.Modal, title='Donation Ticket'):
    def __init__(self, category_id):
        super().__init__()
        self.category_id = category_id
        self.q1 = discord.ui.TextInput(
            label="How much would you like to donate?",
            placeholder="Enter amount (e.g. $10)",
            required=True,
            style=discord.TextStyle.short,
            min_length=1,
            max_length=100
        )
        self.q2 = discord.ui.TextInput(
            label="What is your PayPal/transaction method?",
            placeholder="e.g. PayPal, Cash App, etc.",
            required=True,
            style=discord.TextStyle.short,
            min_length=1,
            max_length=100
        )
        self.add_item(self.q1)
        self.add_item(self.q2)
    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket_channel(
            interaction,
            self.category_id,
            "Donation Ticket",
            [
                ("Donation Amount", self.q1.value),
                ("Payment Method", self.q2.value)
            ]
        )

# Helper function to create ticket channels for new modals
import datetime
async def create_ticket_channel(interaction, category_id, ticket_type, fields):
    global ticket_count
    guild = interaction.guild
    category = interaction.client.get_channel(category_id)
    if category is None or not isinstance(category, discord.CategoryChannel):
        await interaction.response.send_message("Invalid category configuration.", ephemeral=True)
        return
    staff_role_id = 1404046934523514980
    staff_role = guild.get_role(staff_role_id)
    member = interaction.user
    ticket_count += 1
    ticket_number = str(ticket_count).zfill(4)
    channel_name = f"ticket-{ticket_number}"
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    if staff_role is not None:
        overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    ticket_channel = await category.create_text_channel(channel_name, overwrites=overwrites)
    embed = discord.Embed(
        title=f"{ticket_type} - #{ticket_number}",
        color=0x2a2d30,
        timestamp=datetime.datetime.now()
    )
    embed.add_field(name="Requested By", value=member.mention, inline=False)
    for label, value in fields:
        embed.add_field(name=label, value=value, inline=False)
    claim_button = ClaimButton(member, staff_role)
    close_button = CloseButton()
    transcript_button = TranscriptButton()
    view = discord.ui.View(timeout=None)
    view.add_item(claim_button)
    view.add_item(close_button)
    view.add_item(transcript_button)
    await ticket_channel.send(embed=embed, view=view)
    await ticket_channel.send(f"{member.mention}")
    await interaction.response.send_message(f"Ticket channel {ticket_channel.mention} has been created in {category.mention}.", ephemeral=True)

# --- Update on_dropdown event ---
@client.event
async def on_dropdown(interaction: discord.Interaction):
    global ticket_count
    if interaction.data["custom_id"] == "ticket_dropdown":
        selected_option = interaction.data["values"][0]
        # Set your category ID for all ticket types (or use different ones if needed)
        category_id = 1404038490471268362
        if selected_option == "option_support":
            try:
                modal = SupportModal(category_id)
                await interaction.response.send_modal(modal)
                return
            except Exception as e:
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
                return
        elif selected_option == "option_application":
            try:
                modal = StaffApplicationModal(category_id)
                await interaction.response.send_modal(modal)
                return
            except Exception as e:
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
                return
        elif selected_option == "option_report":
            try:
                modal = StaffReportModal(category_id)
                await interaction.response.send_modal(modal)
                return
            except Exception as e:
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
                return
        elif selected_option == "option_appeal":
            try:
                modal = BanAppealModal(category_id)
                await interaction.response.send_modal(modal)
                return
            except Exception as e:
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
                return
        elif selected_option == "option_donation":
            try:
                modal = DonationModal(category_id)
                await interaction.response.send_modal(modal)
                return
            except Exception as e:
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
                return
        else:
            await interaction.response.send_message("Invalid option selected.", ephemeral=True)
            return
    
    elif interaction.data["custom_id"] == "helpp_dropdown":
        selected_option = interaction.data["values"][0]
        
        if selected_option == "helpp_option_1":
            title = "Moderation Commands"
            commands_list = ".ban, .banlogs, .boostmessage, .unbanlogs, .kick, .kicklogs, .antiraid, .antiraidwhitelist, .antiraidremove, .antiraidcheck, .level, .resetlevel, .setlevel, setlevelreset, .botwhitelist, .botwhitelistremove, .botwhitelistcheck, .avatarlogs, .noavatarkick, .displaylogs, .memberupdate, .memberupdatestop, .messagelogs, .messagelogstop, .resetrole, .resetvc, .setpanel, .say, .clonesticker/cs, .stealemoji/se, .setrole, .usernamelogs, .setvc, .timeout/to, .untimeout/unto, .timeoutlogs, .vanity, .vanitystop, .welcome, .welcomestop, .autorole, .clear, .nuke, .lock, .unlock, .setprefix, .resetprefix"
        elif selected_option == "helpp_option_2":
            title = "Everyone Commands"
            commands_list = ".hello, .help, .avatar, .info, .prefix, .serverinfo, .vcpanel, .checklevel, .levellb, .setlevelcheck, .members, .reject, .permit, .insta/ig, .roblox/rblx, .inrole, .snipe, .play, .lyrics, .skip, .pause, .resume, .stop (more coming soon)"
        elif selected_option == "helpp_option_3":
            title = "Booster Commands"
            commands_list = ".createvc, .deletevc, .renamevc, .whitelist, .checkwhitelist, .blacklist, .checkblacklist, .disconnect, .lockvc, .unlockvc, .limitvc, .ghostvc, .createrole, .deleterole, .rolecolor, .renamerole"
        else:
            await interaction.response.send_message("Invalid option selected.", ephemeral=True)
            return

        commands = commands_list.split(', ')
        chunks = [commands[i:i + 10] for i in range(0, len(commands), 10)]  # Split commands into chunks of 10

        embed = discord.Embed(title=title)
        for chunk in chunks:
            embed.add_field(name="", value=' '.join(chunk), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    
    elif interaction.data["custom_id"] == "disconnect_dropdown":
        selected_user_id = interaction.data['values'][0]
        voice_channel = interaction.user.voice.channel
        selected_member = voice_channel.guild.get_member(int(selected_user_id))
        if selected_member:
            await selected_member.edit(voice_channel=None)
            await interaction.response.send_message(f"{selected_member.display_name} has been disconnected from {voice_channel.name}.", ephemeral=True)
        else:
            await interaction.response.send_message("Invalid user selection.", ephemeral=True)





class ClaimButton(discord.ui.Button):
    def __init__(self, member, staff_role):
        super().__init__(style=discord.ButtonStyle.secondary, label="Claim")
        self.member = member
        self.staff_role = staff_role
        self.claimed_by = None

    async def callback(self, interaction: discord.Interaction):
        global claim_counts

        embed = discord.Embed()
        embed.colour = discord.Colour.dark_gray()

        if self.claimed_by:
            embed.description = f"This ticket has already been claimed by {self.claimed_by.mention}."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if self.staff_role in interaction.user.roles or interaction.user.guild_permissions.administrator:
            # Allow staff or admins to claim the ticket
            self.claimed_by = interaction.user
            overwrites = {
                self.member: discord.PermissionOverwrite(send_messages=True, view_channel=True),
                interaction.user: discord.PermissionOverwrite(send_messages=True, view_channel=True),
                self.staff_role: discord.PermissionOverwrite(send_messages=False, view_channel=True),
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                # Add the specific role with view permission
                interaction.guild.get_role(1404046934523514980): discord.PermissionOverwrite(send_messages=True, view_channel=True)
            }

            # Increment claim count for the user
            user_id = str(interaction.user.id)
            claim_counts[user_id] = claim_counts.get(user_id, 0) + 1

            # Send claim notification to the specified channel
            if claim_notification_channel_id:
                claim_notification_channel = interaction.guild.get_channel(claim_notification_channel_id)
                if claim_notification_channel:
                    channel_name = interaction.channel.name if interaction.channel else "deleted channel"
                    embed.description = f"{interaction.user.mention} has claimed {channel_name} and now has {claim_counts[user_id]} claims."
                    await claim_notification_channel.send(embed=embed)
            else:
                embed.description = "Claim notification channel not set. Please set it using the `claimlogs` command."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        else:
            # Non-authorized users
            embed.description = "You don't have permission to claim this ticket."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        ticket_channel = interaction.channel
        await ticket_channel.edit(overwrites=overwrites)

        embed.description = f"{interaction.user.mention} has claimed the ticket."
        await interaction.response.send_message(embed=embed, ephemeral=True)




@client.command()
@commands.has_permissions(administrator=True)
async def claimlogs(ctx, channel_id: int):
    global claim_notification_channel_id
    claim_notification_channel_id = channel_id
    embed = discord.Embed(description=f"Claim notification channel set to <#{channel_id}>.")
    await ctx.send(embed=embed)

@client.command()
@commands.has_permissions(administrator=True)
async def checkclaims(ctx):
    global claim_counts

    # Filter users with at least one claim
    users_with_claims = {user_id: count for user_id, count in claim_counts.items() if count > 0}

    if not users_with_claims:
        embed = discord.Embed(description="No users have claimed any tickets.")
        await ctx.send(embed=embed)
        return

    # Sort users by claim count
    sorted_users = sorted(users_with_claims.items(), key=lambda x: x[1], reverse=True)

    # Generate pages
    pages = []
    page_content = ""
    for user_id, claim_count in sorted_users:
        user = ctx.guild.get_member(int(user_id))
        if user:
            page_content += f"{user.mention} ({user_id}): **{claim_count} claims\n**"
        else:
            # User not found in the guild
            page_content += f"User ID: {user_id}: {claim_count} claims\n"

        # If page content reaches character limit, start a new page
        if len(page_content) > 1900:  # Discord has a 2000 character limit for messages, leaving a buffer
            pages.append(page_content)
            page_content = ""

    # Add remaining content as the last page
    if page_content:
        pages.append(page_content)

    if not pages:
        embed = discord.Embed(description="No users have claimed any tickets.")
        await ctx.send(embed=embed)
        return

    # Send paginated embeds
    current_page = 0
    embed = discord.Embed(title="Claims Overview", description=pages[current_page])
    embed.set_footer(text=f"Page {current_page + 1}/{len(pages)}")
    message = await ctx.send(embed=embed)

    # Add reactions for pagination if there are multiple pages
    if len(pages) > 1:
        await message.add_reaction("◀️")
        await message.add_reaction("▶️")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"]

        while True:
            try:
                reaction, user = await client.wait_for("reaction_add", timeout=60.0, check=check)
            except asyncio.TimeoutError:
                break

            if str(reaction.emoji) == "▶️" and current_page < len(pages) - 1:
                current_page += 1
                embed.description = pages[current_page]
                embed.set_footer(text=f"Page {current_page + 1}/{len(pages)}")
                await message.edit(embed=embed)
                await message.remove_reaction(reaction, user)
            elif str(reaction.emoji) == "◀️" and current_page > 0:
                current_page -= 1
                embed.description = pages[current_page]
                embed.set_footer(text=f"Page {current_page + 1}/{len(pages)}")
                await message.edit(embed=embed)
                await message.remove_reaction(reaction, user)

import typing

@client.command()
@commands.has_permissions(administrator=True)
async def resetclaims(ctx, user_id: typing.Optional[int] = None):
    global claim_counts

    if user_id is None:
        # Reset all claims for every user
        claim_counts = {}
        embed = discord.Embed(description="All claim counts have been reset.")
        await ctx.send(embed=embed)
    else:
        # Reset claims for a specific user
        user_id_str = str(user_id)
        if user_id_str in claim_counts:
            del claim_counts[user_id_str]
            embed = discord.Embed(description=f"Claims for user with ID {user_id} have been reset.")
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description="No claims found for the specified user ID.")
            await ctx.send(embed=embed)

@client.command()
@commands.check(lambda ctx: ctx.author.id == 856896451019276298)  # Replace YOUR_SPECIFIC_DISCORD_ID with the actual Discord ID
@commands.has_permissions(administrator=True)
async def addclaims(ctx, user_id: int, amount: int):
    global claim_counts

    # Ensure user_id is a string to use as a key in the claim_counts dictionary
    user_id_str = str(user_id)

    # Update claim count for the specified user
    if user_id_str in claim_counts:
        claim_counts[user_id_str] += amount
    else:
        claim_counts[user_id_str] = amount

    embed = discord.Embed(description=f"Added {amount} claim(s) to user with ID {user_id}.")
    await ctx.send(embed=embed)




class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="Close")

    async def callback(self, interaction: discord.Interaction):
        import datetime
        channel = interaction.channel
        messages = [msg async for msg in channel.history(limit=100, oldest_first=True)]
        ticket_info = {}
        ticket_type = "Unknown"
        ticket_embed = None
        for message in messages:
            if message.embeds:
                embed = message.embeds[0]
                ticket_embed = embed
                if embed.title:
                    if "Robux" in embed.title:
                        ticket_type = "Robux Purchase"
                    elif "Support" in embed.title:
                        ticket_type = "General Support"
                    elif "Staff Application" in embed.title:
                        ticket_type = "Staff Application"
                    elif "Staff Report" in embed.title:
                        ticket_type = "Staff Report"
                    elif "Ban Appeal" in embed.title:
                        ticket_type = "Ban Appeal"
                    elif "Donation" in embed.title:
                        ticket_type = "Donation Ticket"
                    else:
                        ticket_type = embed.title
                for field in embed.fields:
                    ticket_info[field.name] = field.value
                break
        creator = None
        for message in messages:
            if message.mentions:
                creator = message.mentions[0]
                break
        logs_channel = interaction.guild.get_channel(1404047311998287967)  # Replace with your logs channel ID
        if logs_channel:
            log_embed = discord.Embed(
                title="📝 Ticket Closed",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            log_embed.add_field(name="🎟️ Created By", value=creator.mention if creator else "Unknown", inline=True)
            log_embed.add_field(name="🔒 Closed By", value=interaction.user.mention, inline=True)
            log_embed.add_field(name="📋 Ticket Type", value=ticket_type, inline=True)
            # Add all ticket fields except Created By, Closed By, Ticket Type, Closed At
            skip_fields = {"Requested By", "Created By", "Closed By", "Ticket Type", "Closed At"}
            for field in (ticket_embed.fields if ticket_embed else []):
                if field.name not in skip_fields:
                    log_embed.add_field(name=field.name, value=field.value, inline=False)
            log_embed.add_field(name="📅 Closed At", value=f"<t:{int(datetime.datetime.now().timestamp())}:F>", inline=True)
            await logs_channel.send(embed=log_embed)
        embed = discord.Embed(
            title="Ticket Closed",
            description=f"This ticket will be getting deleted in 5 seconds and got deleted by {interaction.user.mention}",
            color=discord.Color.red()
        )
        try:
            await interaction.response.send_message(embed=embed)
            await asyncio.sleep(5)
            await interaction.channel.delete()
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to delete the ticket channel.")

class TranscriptButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="Transcript")

    async def callback(self, interaction: discord.Interaction):
        try:
            # Check if the user has the specific role or admin perms
            role_id = 1404046934523514980  # Replace with the specific role ID
            user = interaction.user
            member = interaction.guild.get_member(user.id)
            if role_id not in [role.id for role in member.roles] and not member.guild_permissions.administrator:
                await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
                return
            
            # Inform the user that the transcript is being generated
            await interaction.response.send_message("Transcripting...", ephemeral=True)
            await asyncio.sleep(1)

            # Get the ticket channel where the transcript will be generated
            ticket_channel = interaction.channel

            # Get the specific channel ID where you want to save the transcript
            transcript_channel_id = 1404047311998287967  # Replace with the specific channel ID
            transcript_channel = interaction.guild.get_channel(transcript_channel_id)

            # Ensure the transcript channel exists and is a text channel
            if transcript_channel is None or not isinstance(transcript_channel, discord.TextChannel):
                await interaction.followup.send("Invalid transcript channel configuration.")
                return

            # Fetch recent messages from the ticket channel
            try:
                messages = []
                async for message in ticket_channel.history(limit=None):
                    messages.append((message.author.display_name, message.content))
            except discord.Forbidden:
                await interaction.followup.send("I don't have permission to fetch messages.")
                return

            # Reverse the list of messages to display the oldest message first
            messages.reverse()

            # Generate HTML content for the transcript
            html_content = "<html><head><title>Ticket Transcript</title>"
            html_content += "<style>"
            html_content += "body {font-family: Arial, sans-serif; background-color: #36393F; color: #FFFFFF;}"
            html_content += ".message {margin-bottom: 10px;}"
            html_content += ".message .author {font-weight: bold;}"
            html_content += ".message .content {margin-left: 10px;}"
            html_content += "</style>"
            html_content += "</head><body>"

            for author, content in messages:
                html_content += f'<div class="message"><span class="author">{author}</span><span class="content">{content}</span></div>'

            html_content += "</body></html>"

            # Save the HTML content to a file
            file_name = f"ticket_transcript_{ticket_channel.id}.html"
            with open(file_name, "w", encoding="utf-8") as file:
                file.write(html_content)

            # Send the HTML file as an attachment to the transcript channel
            transcript_file = discord.File(file_name)
            await transcript_channel.send(f"Ticket Transcript generated by {interaction.user.mention}:", file=transcript_file)

            # Delete the temporary HTML file
            os.remove(file_name)

            # Create an embed to send
            embed = discord.Embed(
                title="Transcript Generated",
                description="Transcript has been generated and sent to the transcript channel.",
                color=discord.Color.green()
            )
            
            # Send the embed message along with the text response
            await interaction.followup.send(embed=embed)
        except discord.errors.InteractionResponded:
            pass



@client.command()
async def close(ctx):
    # Define a dictionary mapping category IDs to category names
    ticket_categories = {
        1404038490471268362: "General Support",
        1404038490471268362: "Staff Application",
        1404038490471268362: "Staff Report",
        1404038490471268362: "Ban Appeal",
        1404038490471268362: "Donation Ticket",
        # Add more categories as needed
    }

    # Check if the command is being used in a ticket channel
    channel_category_id = ctx.channel.category_id
    if channel_category_id not in ticket_categories:
        # If the channel category is not a ticket category, inform the user and return
        await ctx.send("This command can only be used within a ticket channel.")
        return

    # Check if the user invoking the command has the necessary permissions
    staff_role_id = 1404046934523514980  # Replace with your staff role ID
    staff_role = ctx.guild.get_role(staff_role_id)
    if not (ctx.author.guild_permissions.administrator or (staff_role and staff_role in ctx.author.roles)):
        await ctx.send("You don't have permission to use this command.")
        return

    # --- Ticket log embed logic (same as CloseButton) ---
    import datetime
    channel = ctx.channel
    messages = [msg async for msg in channel.history(limit=100, oldest_first=True)]
    ticket_info = {}
    ticket_type = "Unknown"
    ticket_embed = None
    for message in messages:
        if message.embeds:
            embed = message.embeds[0]
            ticket_embed = embed
            if embed.title:
                if "Robux" in embed.title:
                    ticket_type = "Robux Purchase"
                elif "Support" in embed.title:
                    ticket_type = "General Support"
                elif "Staff Application" in embed.title:
                    ticket_type = "Staff Application"
                elif "Staff Report" in embed.title:
                    ticket_type = "Staff Report"
                elif "Ban Appeal" in embed.title:
                    ticket_type = "Ban Appeal"
                elif "Donation" in embed.title:
                    ticket_type = "Donation Ticket"
                else:
                    ticket_type = embed.title
            for field in embed.fields:
                ticket_info[field.name] = field.value
            break
    creator = None
    for message in messages:
        if message.mentions:
            creator = message.mentions[0]
            break
    logs_channel = ctx.guild.get_channel(1404047311998287967)
    if logs_channel:
        log_embed = discord.Embed(
            title="📝 Ticket Closed",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        log_embed.add_field(name="🎟️ Created By", value=creator.mention if creator else "Unknown", inline=True)
        log_embed.add_field(name="🔒 Closed By", value=ctx.author.mention, inline=True)
        log_embed.add_field(name="📋 Ticket Type", value=ticket_type, inline=True)
        skip_fields = {"Requested By", "Created By", "Closed By", "Ticket Type", "Closed At"}
        for field in (ticket_embed.fields if ticket_embed else []):
            if field.name not in skip_fields:
                log_embed.add_field(name=field.name, value=field.value, inline=False)
        log_embed.add_field(name="📅 Closed At", value=f"<t:{int(datetime.datetime.now().timestamp())}:F>", inline=True)
        await logs_channel.send(embed=log_embed)

    # Create an embed to send
    embed = discord.Embed(
        title="Ticket Closed",
        description=f"This ticket will be getting deleted in 5 seconds and got deleted by {ctx.author.mention}",
        color=discord.Color.red()
    )

    try:
        # Send the embed message
        await ctx.send(embed=embed)

        # Delete the ticket channel after 5 seconds
        await asyncio.sleep(5)
        await ctx.channel.delete()
    except discord.Forbidden:
        await ctx.send("I don't have permission to delete the ticket channel.")

@client.command()
async def transcript(ctx):
    # Check if the user invoking the command has the necessary permissions
    staff_role_id = 1404047311998287967  # Replace with your staff role ID
    staff_role = ctx.guild.get_role(staff_role_id)
    if not (ctx.author.guild_permissions.administrator or (staff_role and staff_role in ctx.author.roles)):
        await ctx.send("You don't have permission to use this command.")
        return

    try:
        # Inform the user that the transcript is being generated
        await ctx.send("Transcripting...")

        # Get the ticket channel where the transcript will be generated
        ticket_channel = ctx.channel

        # Get the specific channel ID where you want to save the transcript
        transcript_channel_id = 1404047311998287967  # Replace with the specific channel ID
        transcript_channel = ctx.guild.get_channel(transcript_channel_id)

        # Ensure the transcript channel exists and is a text channel
        if transcript_channel is None or not isinstance(transcript_channel, discord.TextChannel):
            await ctx.send("Invalid transcript channel configuration.")
            return

        # Fetch recent messages from the ticket channel
        try:
            messages = []
            async for message in ticket_channel.history(limit=None):
                messages.append((message.author.display_name, message.content))
        except discord.Forbidden:
            await ctx.send("I don't have permission to fetch messages.")
            return

        # Reverse the list of messages to display the oldest message first
        messages.reverse()

        # Generate HTML content for the transcript
        html_content = "<html><head><title>Ticket Transcript</title>"
        html_content += "<style>"
        html_content += "body {font-family: Arial, sans-serif; background-color: #36393F; color: #FFFFFF;}"
        html_content += ".message {margin-bottom: 10px;}"
        html_content += ".message .author {font-weight: bold;}"
        html_content += ".message .content {margin-left: 10px;}"
        html_content += "</style>"
        html_content += "</head><body>"

        for author, content in messages:
            html_content += f'<div class="message"><span class="author">{author}</span><span class="content">{content}</span></div>'

        html_content += "</body></html>"

        # Save the HTML content to a file
        file_name = f"ticket_transcript_{ticket_channel.id}.html"
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(html_content)

        # Send the HTML file as an attachment to the transcript channel
        transcript_file = discord.File(file_name)
        await transcript_channel.send(f"Ticket Transcript generated by {ctx.author.mention}:", file=transcript_file)

        # Delete the temporary HTML file
        os.remove(file_name)

        # Create an embed to send
        embed = discord.Embed(
            title="Transcript Generated",
            description="Transcript has been generated and sent to the transcript channel.",
            color=discord.Color.green()
        )

        # Send the embed message along with the text response
        await ctx.send(embed=embed)
    except discord.errors.InteractionResponded:
        pass



@client.command()
async def add(ctx, target):
    # Check if the user invoking the command has the staff role or admin perms
    staff_role_id = 1404046934523514980  # Replace with your staff role ID
    staff_role = ctx.guild.get_role(staff_role_id)
    if not (ctx.author.guild_permissions.administrator or (staff_role and staff_role in ctx.author.roles)):
        embed = discord.Embed(
            title="Permission Denied",
            description="You don't have permission to use this command.",
            color=0x2a2d30  # Set color to 0x2a2d30
        )
        await ctx.send(embed=embed)
        return

    # Get the ticket channel
    ticket_channel = ctx.channel

    # Check if the target is a role mention
    if target.startswith("<@&") and target.endswith(">"):
        role_id = int(target[3:-1])
        role = ctx.guild.get_role(role_id)
        if role:
            # Add the role to the ticket channel
            await ticket_channel.set_permissions(role, read_messages=True, send_messages=True)
            embed = discord.Embed(
                title="Role Added",
                description=f"{role.name} has been added to the ticket.",
                color=0x2a2d30  # Set color to 0x2a2d30
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Role Not Found",
                description="The specified role was not found.",
                color=0x2a2d30  # Set color to 0x2a2d30
            )
            await ctx.send(embed=embed)
    else:
        # Try to convert target to a discord.Member object
        try:
            user = await commands.MemberConverter().convert(ctx, target)
        except commands.MemberNotFound:
            # If the conversion fails, try to find the user by name
            user = discord.utils.find(lambda m: m.name == target or str(m) == target, ctx.guild.members)

        if user:
            # Add the user to the ticket channel
            await ticket_channel.set_permissions(user, read_messages=True, send_messages=True)
            embed = discord.Embed(
                title="User Added",
                description=f"{user.mention} has been added to the ticket.",
                color=0x2a2d30  # Set color to 0x2a2d30
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="User Not Found",
                description="The specified user was not found.",
                color=0x2a2d30  # Set color to 0x2a2d30
            )
            await ctx.send(embed=embed)

@client.command()
async def remove(ctx, target):
    # Check if the user invoking the command has the staff role or admin perms
    staff_role_id = 1404046934523514980  # Replace with your staff role ID
    staff_role = ctx.guild.get_role(staff_role_id)
    if not (ctx.author.guild_permissions.administrator or (staff_role and staff_role in ctx.author.roles)):
        embed = discord.Embed(
            title="Permission Denied",
            description="You don't have permission to use this command.",
            color=0x2a2d30  # Set color to 0x2a2d30
        )
        await ctx.send(embed=embed)
        return

    # Get the ticket channel
    ticket_channel = ctx.channel

    # Check if the target is a role mention
    if target.startswith("<@&") and target.endswith(">"):
        role_id = int(target[3:-1])
        role = ctx.guild.get_role(role_id)
        if role:
            # Remove the role from the ticket channel
            await ticket_channel.set_permissions(role, read_messages=False, send_messages=False)
            embed = discord.Embed(
                title="Role Removed",
                description=f"{role.name} has been removed from the ticket.",
                color=0x2a2d30  # Set color to 0x2a2d30
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Role Not Found",
                description="The specified role was not found.",
                color=0x2a2d30  # Set color to 0x2a2d30
            )
            await ctx.send(embed=embed)
    else:
        # Try to convert target to a discord.Member object
        try:
            user = await commands.MemberConverter().convert(ctx, target)
        except commands.MemberNotFound:
            # If the conversion fails, try to find the user by name
            user = discord.utils.find(lambda m: m.name == target or str(m) == target, ctx.guild.members)

        if user:
            # Remove the user from the ticket channel
            await ticket_channel.set_permissions(user, read_messages=False, send_messages=False)
            embed = discord.Embed(
                title="User Removed",
                description=f"{user.mention} has been removed from the ticket.",
                color=0x2a2d30  # Set color to 0x2a2d30
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="User Not Found",
                description="The specified user was not found.",
                color=0x2a2d30  # Set color to 0x2a2d30
            )
            await ctx.send(embed=embed)


@client.command()
async def rename(ctx, *, new_name):
    # Check if the user invoking the command has the staff role or admin perms
    staff_role_id = 1404046934523514980  # Replace with your staff role ID
    staff_role = ctx.guild.get_role(staff_role_id)
    if not (ctx.author.guild_permissions.administrator or (staff_role and staff_role in ctx.author.roles)):
        embed = discord.Embed(description="You don't have permission to use this command.", color=0x2a2d30)  # Set color to 0x2a2d30
        await ctx.send(embed=embed)
        return
    
    # Get the ticket channel
    ticket_channel = ctx.channel
    
    # Rename the ticket channel
    try:
        await ticket_channel.edit(name=new_name)
        embed = discord.Embed(description=f"Ticket has been renamed to `{new_name}`.", color=0x2a2d30)  # Set color to 0x2a2d30
        await ctx.send(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(description="I don't have permission to rename the ticket.", color=0x2a2d30)  # Set color to 0x2a2d30
        await ctx.send(embed=embed)

roster = {
    "Server Management": [],
    "Head Management": [],
    "Senior Management": [],
    "Management": [],
    "Community Manager": [],
    "Head of Staff": [],
    "Head Administrator": [],
    "Senior Administrator": [],
    "Administrator": [],
    "Head Moderator": [],
    "Senior Moderator": [],
    "Moderator": [],
    "Trial Moderator": [],
    "Support": []
}


roster_message = None

@client.event
async def on_ready():
    """
    Background task to update the roster message periodically.
    """
    global update_roster_task
    update_roster_task.start()

@tasks.loop(seconds=60)  # Update the roster every 60 seconds
async def update_roster():
    """
    Background task to update the roster message periodically.
    """
    global roster_message
    if roster_message:
        embed = discord.Embed(title="Roster", color=discord.Color.blue())
        for position, members in roster.items():
            embed.add_field(name=position, value=", ".join(members) or "None", inline=False)
        await roster_message.edit(embed=embed)

@update_roster.before_loop
async def before_update_roster():
    await client.wait_until_ready()

member_update_logs = {}
boost_messages = {}
member_update_logs = {}

@client.command()
@is_whitelisted()
async def boostmessage(ctx, channel_id: int = None, *, message: str = None):
    if ctx.author.guild_permissions.administrator:
        if not channel_id or not message:
            usage_embed = discord.Embed(
                title="Boost Message Command Usage",
                description="Use this command to set a boost message. Mention a user and set a footer using placeholders.",
                color=0x2a2d30
            )
            usage_embed.add_field(
                name="Usage",
                value="`.boostmessage <channel_id> <message>`",
                inline=False
            )
            usage_embed.add_field(
                name="Placeholders",
                value="{user} - Mention the user who boosted\n"
                      "{footer} - footer message which is `{We now have {boost_count} boosts.}`",
                inline=False
            )
            await ctx.send(embed=usage_embed)
            return

        boost_messages[ctx.guild.id] = (channel_id, message)
        confirmation_embed = discord.Embed(
            title="Boost Message Set",
            description=f'Boost message set for channel <#{channel_id}>!',
            color=0x2a2d30
        )
        confirmation_embed.add_field(name="Message", value=message, inline=False)
        await ctx.send(embed=confirmation_embed)
    else:
        permission_embed = discord.Embed(
            title="Permission Denied",
            description='You do not have permission to use this command.',
            color=0x2a2d30
        )
        await ctx.send(embed=permission_embed)




@client.event
async def on_member_update(before, after):
    # Antiraid protection for mass timeouts
    if antiraid_enabled and before.timed_out_until != after.timed_out_until and after.timed_out_until:
        # Member just got timed out
        debug_antiraid(f"Member timed out: {after.name} (ID: {after.id})")
        
        try:
            # Check if this was actually a timeout (not a timeout expiring)
            timeout_found = False
            async for entry in after.guild.audit_logs(action=discord.AuditLogAction.member_update, limit=5):
                debug_antiraid(f"Checking timeout audit entry: {entry.user.name} -> {entry.target.name if hasattr(entry.target, 'name') else 'Unknown'}")
                if entry.target.id == after.id and (time.time() - entry.created_at.timestamp()) < 5:
                    # Check if this audit entry is for a timeout
                    if hasattr(entry, 'changes'):
                        debug_antiraid(f"Entry changes: {dir(entry.changes)}")
                        # Try different ways to access the timeout change
                        timeout_change = None
                        
                        # Check for timeout changes - look at before and after objects
                        if hasattr(entry.changes, 'before') and hasattr(entry.changes, 'after'):
                            before_obj = entry.changes.before
                            after_obj = entry.changes.after
                            
                            debug_antiraid(f"Before object: {before_obj}")
                            debug_antiraid(f"After object: {after_obj}")
                            
                            # Check if timed_out_until changed
                            before_timeout = getattr(before_obj, 'timed_out_until', None)
                            after_timeout = getattr(after_obj, 'timed_out_until', None)
                            
                            debug_antiraid(f"Before timeout: {before_timeout}, After timeout: {after_timeout}")
                            
                            # Check if this is a new timeout (before is None or past, after is future)
                            import datetime
                            now = datetime.datetime.now(datetime.timezone.utc)
                            
                            # This is a new timeout if:
                            # 1. before is None (no previous timeout) OR before is in the past (timeout expired)
                            # 2. after is in the future (new timeout applied)
                            is_new_timeout = (
                                (before_timeout is None or before_timeout < now) and 
                                after_timeout is not None and after_timeout > now
                            )
                            
                            debug_antiraid(f"Is new timeout: {is_new_timeout}")
                            
                            if is_new_timeout:
                                    timeout_found = True
                                    debug_antiraid(f"Found recent timeout entry: {entry.user.name} timed out {after.name}")
                                    
                                    # Track the timeout action
                                    user_id = entry.user.id
                                    if user_id not in user_action_timestamps:
                                        user_action_timestamps[user_id] = {'timeouts': []}
                                    elif 'timeouts' not in user_action_timestamps[user_id]:
                                        user_action_timestamps[user_id]['timeouts'] = []
                                    
                                    user_action_timestamps[user_id]['timeouts'].append(time.time())
                                    debug_antiraid(f"Added timeout timestamp for {entry.user.name}. Total timeouts: {len(user_action_timestamps[user_id]['timeouts'])}")
                                    
                                    # Remove old timestamps (older than 4 seconds)
                                    user_action_timestamps[user_id]['timeouts'] = [
                                        t for t in user_action_timestamps[user_id]['timeouts'] 
                                        if time.time() - t < 4
                                    ]
                                    debug_antiraid(f"After cleanup: {len(user_action_timestamps[user_id]['timeouts'])} timeouts in last 4 seconds")
                                    
                                    # Check if user is whitelisted
                                    if user_id in antiraid_whitelist:
                                        debug_antiraid(f"User {entry.user.name} is whitelisted, skipping timeout")
                                        break
                                    
                                    # If 2 or more timeouts in 4 seconds, timeout the user and remove their roles
                                    if len(user_action_timestamps[user_id]['timeouts']) >= 2:
                                        debug_antiraid(f"TIMEOUTING {entry.user.name} for mass timeouts!")
                                        try:
                                            # Remove all roles with permissions
                                            roles_to_remove = []
                                            for role in entry.user.roles:
                                                if role.permissions.administrator or role.permissions.manage_guild or role.permissions.manage_roles or role.permissions.manage_channels or role.permissions.kick_members or role.permissions.ban_members or role.permissions.manage_messages:
                                                    roles_to_remove.append(role)
                                            
                                            if roles_to_remove:
                                                await entry.user.remove_roles(*roles_to_remove, reason="Antiraid: Mass timeout detection - removing permissions")
                                                debug_antiraid(f"Removed {len(roles_to_remove)} roles with permissions from {entry.user.name}")
                                            
                                            # Timeout the user for 1 hour
                                            import datetime
                                            await entry.user.timeout(datetime.timedelta(hours=1), reason="Antiraid: Mass timeout detection")
                                            
                                            embed = discord.Embed(
                                                title="🛡️ Antiraid Protection",
                                                description=f"**{entry.user.name}** has been timed out and had their permissions removed for mass timing out members.",
                                                color=0xff0000
                                            )
                                            embed.add_field(name="Action", value="Mass timeout detection", inline=False)
                                            embed.add_field(name="Timeouts", value=f"{len(user_action_timestamps[user_id]['timeouts'])} in 4 seconds", inline=False)
                                            embed.add_field(name="Roles Removed", value=f"{len(roles_to_remove)} roles with permissions", inline=False)
                                            embed.add_field(name="Timeout Duration", value="1 hour", inline=False)
                                            
                                            # Send to antiraid logs channel if configured
                                            logs_channel_id = antiraid_logs_channels.get(str(after.guild.id))
                                            if logs_channel_id:
                                                logs_channel = after.guild.get_channel(logs_channel_id)
                                                if logs_channel and logs_channel.permissions_for(after.guild.me).send_messages:
                                                    await logs_channel.send(embed=embed)
                                                else:
                                                    # Fallback to first available channel
                                                    for channel in after.guild.text_channels:
                                                        if channel.permissions_for(after.guild.me).send_messages:
                                                            await channel.send(embed=embed)
                                                            break
                                            else:
                                                # Send to first available channel
                                                for channel in after.guild.text_channels:
                                                    if channel.permissions_for(after.guild.me).send_messages:
                                                        await channel.send(embed=embed)
                                                        break
                                        except Exception as e:
                                            debug_antiraid(f"Error timing out user: {e}")
                                    break
        except Exception as e:
            debug_antiraid(f"Error in timeout detection: {e}")
    
    guild_id = after.guild.id
    logs_channel_id = member_update_logs.get(str(guild_id))

    # Timeout/Untimeout logging
    timeout_log_channel_id = timeout_log_channels.get(guild_id)
    if before.timed_out_until != after.timed_out_until:
        import datetime
        import asyncio
        channel = after.guild.get_channel(timeout_log_channel_id) if timeout_log_channel_id else None

        # Try to get the moderator and reason from audit logs (with delay)
        moderator = None
        reason = None
        await asyncio.sleep(1)  # Give Discord a moment to write the audit log
        async for entry in after.guild.audit_logs(action=discord.AuditLogAction.member_update, limit=10):
            if entry.target.id == after.id:
                before_timeout = getattr(entry.changes.before, "communication_disabled_until", None)
                after_timeout = getattr(entry.changes.after, "communication_disabled_until", None)
                if before_timeout != after_timeout:
                    moderator = entry.user
                    reason = entry.reason
                    break
        moderator_value = moderator.mention if moderator else "Unknown"
        reason_value = reason if reason else "Unknown"

        # Timeout applied
        if after.timed_out_until and (before.timed_out_until is None or (before.timed_out_until and after.timed_out_until > before.timed_out_until)):
            duration = after.timed_out_until - datetime.datetime.now(datetime.timezone.utc)
            total_seconds = int(duration.total_seconds())
            if total_seconds < 60:
                duration_str = f"{total_seconds} seconds"
            elif total_seconds < 3600:
                duration_str = f"{total_seconds // 60} minutes"
            elif total_seconds < 86400:
                duration_str = f"{total_seconds // 3600} hours"
            else:
                duration_str = f"{total_seconds // 86400} days"
            embed = discord.Embed(title="Timed Out", color=0x2a2d30)
            embed.add_field(name="User", value=after.mention, inline=True)
            embed.add_field(name="Moderator", value=moderator_value, inline=True)
            embed.add_field(name="Duration/Reason", value=f"{duration_str} - {reason_value}", inline=True)
            if channel:
                await channel.send(embed=embed)
        # Timeout removed
        elif before.timed_out_until and (after.timed_out_until is None or after.timed_out_until < before.timed_out_until):
            embed = discord.Embed(title="Untimed Out", color=0x2a2d30)
            embed.add_field(name="User", value=after.mention, inline=True)
            embed.add_field(name="Moderator", value=moderator_value, inline=True)
            embed.add_field(name="Reason", value=reason_value, inline=True)
            if channel:
                await channel.send(embed=embed)

    if logs_channel_id:
        logs_channel = client.get_channel(logs_channel_id)
        if logs_channel:
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]
            role_updated = False
            moderator = None

            if added_roles:
                async for entry in after.guild.audit_logs(action=discord.AuditLogAction.member_role_update, limit=1):
                    if entry.target == after:
                        moderator = entry.user
                        break

                added_roles_mentions = ", ".join([role.mention for role in added_roles])
                if moderator:
                    action_description = f"{after.mention} got role(s) added: {added_roles_mentions}\nGiven by: {moderator.mention}"
                else:
                    action_description = f"{after.mention} got role(s) added: {added_roles_mentions}\nGiven by: Unknown"
                color = 0x00ff00
                role_updated = True

            if removed_roles:
                async for entry in after.guild.audit_logs(action=discord.AuditLogAction.member_role_update, limit=1):
                    if entry.target == after:
                        moderator = entry.user
                        break

                removed_roles_mentions = ", ".join([role.mention for role in removed_roles])
                if moderator:
                    action_description = f"{after.mention} got role(s) removed: {removed_roles_mentions}\nTaken by: {moderator.mention}"
                else:
                    action_description = f"{after.mention} got role(s) removed: {removed_roles_mentions}\nTaken by: Unknown"
                color = 0xff0000
                role_updated = True

            if role_updated:
                avatar_url = after.avatar.url if after.avatar else after.default_avatar.url
                embed = discord.Embed(title="Role Update", description=action_description, color=color)
                embed.set_author(name=after.name, icon_url=avatar_url)
                embed.set_thumbnail(url=avatar_url)
                await logs_channel.send(embed=embed)

            if not before.premium_since and after.premium_since:
                    if guild_id in boost_messages:
                        channel_id, message = boost_messages[guild_id]
                        channel = client.get_channel(channel_id)
                        if channel:
                            # Format the message to include the user mention and total boost count
                            user_mention = after.mention
                            boost_count = after.guild.premium_subscription_count
                            
                            # Handle footer replacement
                            footer_text = f"We now have {boost_count} boosts."
                            if "{footer" in message:
                                start_index = message.index("{footer")
                                end_index = message.index("}", start_index)
                                custom_footer = message[start_index + 1:end_index].strip()
                                footer_text = custom_footer.replace("{amount}", str(boost_count))

                                # Remove the custom footer tag from the message
                                message = message[:start_index] + message[end_index + 1:]

                            formatted_message = message.replace("{user}", user_mention).strip()
                            embed = discord.Embed(description=formatted_message, color=0x2a2d30)
                            embed.set_footer(text=footer_text)
                            await channel.send(embed=embed)
                        else:
                            print(f'Channel ID {channel_id} not found in guild {guild_id}.')
                    



    specific_role_ids = {
        1219705433112186930: "Server Management",
        1219707373862522931: "Head Management",
        1219706799758905480: "Senior Management",
        1219706164737085562: "Management",
        1219705638234357760: "Community Manager",
        1219705160360792074: "Head of Staff",
        1219703969832767559: "Head Administrator",
        1219703527103008889: "Senior Administrator",
        1219703129126473759: "Administrator",
    }

    for role_id, role_name in specific_role_ids.items():
        role = after.guild.get_role(role_id)
        if role:
            members = [member.mention for member in role.members]
            roster[role_name] = members

    if roster_message:
        embed = discord.Embed(title="Roster", color=discord.Color.blue())
        for position, members in roster.items():
            embed.add_field(name=position, value=", ".join(members) or "None", inline=False)
        await roster_message.edit(embed=embed)

@client.event
async def on_ready():
    global roster_message
    roster_channel_id = 1219702722275274752
    roster_channel = client.get_channel(roster_channel_id)
    if roster_channel:
        embed = discord.Embed(title="Roster", color=discord.Color.blue())
        for position, members in roster.items():
            embed.add_field(name=position, value=", ".join(members) or "None", inline=False)
        roster_message = await roster_channel.send(embed=embed)

    # Start the update_roster task
    update_roster.start()


@client.command()
async def check(ctx):
    """
    Check the roster by fetching users with specific roles.
    """
    global roster_message
    
    guild = ctx.guild
    members = guild.members
    
    role_members = {}
    role_counts = {}
    
    for role_id, roster_name in specific_role_ids.items():
        role = discord.utils.get(guild.roles, id=role_id)
        if role:
            role_members[roster_name] = [member.mention for member in members if role in member.roles]
            role_counts[roster_name] = len(role_members[roster_name])
    
    for position, members in role_members.items():
        roster[position] = members
    
    embed = discord.Embed(title="Roster", color=0x2a2d30)
    for position, members in roster.items():
        embed.add_field(name=f"{position} ({role_counts.get(position, 0)})", value=", ".join(members) or "None", inline=False)
    if roster_message is None:
        roster_message = await ctx.send(embed=embed)
    else:
        await roster_message.edit(embed=embed)






@client.command(name="setpanel")
@is_whitelisted()
@commands.has_permissions(administrator=True)
async def set_lock(ctx):
    category = ctx.channel.category

    interface_channel = await category.create_text_channel("interface")
    
    join_to_create_channel = await category.create_voice_channel("Join to Create")
    
    guild_name = ctx.guild.name
    
    author_profile_picture = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
    
    thumbnail_url = "https://cdn.discordapp.com/avatars/1199492627251339274/79b1a1ad3ccb8886edac3ef6cd401f3d.webp?size=1024&format=webp&width=0&height=256"
    
    embed = discord.Embed(title="VoiceMaster Interface", description="Click the buttons below to control your voice channel")
    embed.add_field(name="Button Usage", value="🔒 — [`Lock`](https://discord.gg/tip) the voice channel\n🔓 — [`Unlock`](https://discord.gg/tip) the voice channel\n👻 — [`Ghost`](https://discord.gg/tip) the voice channel\n🔍 — [`Reveal`](https://discord.gg/tip) the voice channel\n🔑 — [`Claim`](https://discord.gg/tip) the voice channel\n👢 — [`Disconnect`](https://discord.gg/tip) a member\nℹ️ — [`View`](https://discord.gg/tip) channel information\n➕ — [`Increase`](https://discord.gg/tip) the user limit\n➖ — [`Decrease`](https://discord.gg/tip) the user limit")
    embed.set_author(name=guild_name, icon_url=author_profile_picture)
    embed.set_thumbnail(url=thumbnail_url)
    
    lock_message = await interface_channel.send(embed=embed, view=LockButton())
    await ctx.send("panel has been created")


intents = discord.Intents.default()
intents.messages = True
intents.guilds = True


@client.command()
@is_whitelisted()
async def voicelogs(ctx, channel_id: int):
    # Set the voice logs channel ID for the guild
    guild_id = ctx.guild.id
    guild_settings.setdefault(guild_id, {})
    guild_settings[guild_id]['voice_logs_channel_id'] = channel_id
    
    # Create an embed confirming the change
    embed = discord.Embed(title="Voice Logs Channel Set",
                          description=f"Voice logs will now be sent to <#{channel_id}>.",
                          color=discord.Color.green())
    await ctx.send(embed=embed)

custom_prefixes = {}

# Command to get the current prefix
@client.command()
@is_whitelisted()
async def prefix(ctx):
    guild_id = ctx.guild.id
    current_prefix = custom_prefixes.get(guild_id, default_prefix)

    embed = discord.Embed(description=f"The prefix is `{current_prefix}`", color=0x2a2d30)
    await ctx.send(embed=embed)

# Command to set a custom prefix for the guild
@client.command()
@is_whitelisted()
async def setprefix(ctx, new_prefix):
    guild_id = ctx.guild.id
    custom_prefixes[guild_id] = new_prefix

    embed = discord.Embed(description=f"Prefix set to `{new_prefix}`", color=0x2a2d30)
    await ctx.send(embed=embed)

# Default prefix
default_prefix = '.'  # You can set this to whatever you want

# Override the default prefix check function
def get_custom_prefix(bot, message):
    guild_id = message.guild.id
    return custom_prefixes.get(guild_id, default_prefix)

client.command_prefix = get_custom_prefix

@client.command()
@is_whitelisted()
async def resetprefix(ctx):
    guild_id = ctx.guild.id
    custom_prefixes.pop(guild_id, None)  # Remove custom prefix for the guild

    embed = discord.Embed(description=f"Prefix set to `{default_prefix}`", color=0x2a2d30)
    await ctx.send(embed=embed)


from datetime import datetime, timedelta, timezone

@client.command(aliases=['si'])
@is_whitelisted()
async def serverinfo(ctx):
    guild = ctx.guild
    main_owner = guild.owner
    member_count = guild.member_count
    role_count = len(guild.roles)
    category_count = len(guild.categories)
    text_channel_count = len(guild.text_channels)
    voice_channel_count = len(guild.voice_channels)
    boost_count = guild.premium_subscription_count
    boost_tier = guild.premium_tier
    roles = ", ".join([role.name for role in guild.roles])
    server_icon = guild.icon.url if guild.icon else None
    server_banner = guild.banner.url if guild.banner else None
    est = timezone(timedelta(hours=-5))
    created_at_est = guild.created_at.astimezone(est)

    embed = discord.Embed(title=f"{guild.name} Server Information", color=0x2a2d30)
    if server_icon:
        embed.set_thumbnail(url=server_icon)
    if server_banner:
        embed.set_image(url=server_banner)
    embed.add_field(name="Main Owner", value=main_owner)
    embed.add_field(name="Member Count", value=member_count)
    embed.add_field(name="Role Count", value=role_count)
    embed.add_field(name="Category Count", value=category_count)
    embed.add_field(name="Text Channel Count", value=text_channel_count)
    embed.add_field(name="Voice Channel Count", value=voice_channel_count)
    
    boost_info = f"Boost Count: {boost_count} (Tier {boost_tier})"
    
    embed.add_field(name="Boost Information", value=boost_info, inline=False)
    
    embed.add_field(name="Roles", value=roles)
    
    embed.set_footer(text=f"Server ID: {guild.id} | Created at: {created_at_est.strftime('%Y-%m-%d %H:%M:%S')} EST")

    await ctx.send(embed=embed)


blacklisted_users = set()

@client.command()
@is_whitelisted()
async def autorole(ctx, *, role: discord.Role = None):
    if role is None:
        embed = discord.Embed(description="You need to mention a role. Example: `autorole @rolename`", color=0x2a2d30)
        await ctx.send(embed=embed)
        return

    if ctx.author.guild_permissions.manage_roles:
        try:
            embed = discord.Embed(description=f"Assigning role {role.name} to all members", color=0x2a2d30)
            await ctx.send(embed=embed)
            for member in ctx.guild.members:
                await member.add_roles(role)
            embed = discord.Embed(description=f"All members have been assigned the role {role.name}.", color=0x2a2d30)
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(description=f"An error occurred: {e}", color=0xFF0000)
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed(description="You do not have permission to use this command.", color=0xFF0000)
        await ctx.send(embed=embed)





ban_logs = {}

@client.command()
@is_whitelisted()
async def ban(ctx, member: discord.Member=None, *, reason=None):
    if ctx.author.guild_permissions.ban_members:
        if member is None or reason is None:
            embed = discord.Embed(title="Error", description="Please use the command in the format: `ban <@user> <reason>`.", color=0xff0000)
            await ctx.send(embed=embed)
            return
        
        await member.ban(reason=reason)
        
        ban_embed = discord.Embed(title="Member Banned", color=0xff0000)
        ban_embed.add_field(name="Banned Member", value=member.mention)
        ban_embed.add_field(name="Banned By", value=ctx.author.mention)
        ban_embed.add_field(name="Reason", value=reason if reason else "No reason provided")
        ban_message = await ctx.send(embed=ban_embed)

        modlog_embed = discord.Embed(title="Member Banned", color=0xff0000)
        modlog_embed.add_field(name="Banned Member", value=member.mention)
        modlog_embed.add_field(name="Banned By", value=ctx.author.mention)
        modlog_embed.add_field(name="Reason", value=reason if reason else "No reason provided")

        guild_id = ctx.guild.id
        if guild_id in ban_logs:
            banlogs = client.get_channel(ban_logs[guild_id])
            if banlogs is not None:
                await banlogs.send(embed=modlog_embed)
            else:
                embed = discord.Embed(title="Error", description="Failed to find the logging channel. Make sure the channel ID is correct.", color=0xff0000)
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Error", description="No ban logs channel configured for this guild. Please use .banlogs to set it up.", color=0xff0000)
            await ctx.send(embed=embed)

        try:
            await member.send(f"You have been banned from {ctx.guild.name} for the following reason: {reason if reason else 'No reason provided'}")
        except discord.Forbidden:
            embed = discord.Embed(title="Error", description="Failed to send DM to the banned member.", color=0xff0000)
            await ctx.send(embed=embed)

        await ctx.message.delete()
        await ban_message.delete(delay=5)
    else:
        embed = discord.Embed(title="Error", description="You do not have permission to use this command.", color=0xff0000)
        await ctx.send(embed=embed)

@client.command()
@is_whitelisted()
async def banlogs(ctx, channel_id: int = None):
    if channel_id is None:
        embed = discord.Embed(title="Error", description="Please specify the channel ID: `.banlogs <channel_id>`.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    guild_id = ctx.guild.id
    ban_logs[guild_id] = channel_id
    embed = discord.Embed(title="Ban Logs Channel Set", description=f"Ban logs will now be sent to <#{channel_id}>", color=0x00ff00)
    await ctx.send(embed=embed)

unban_logs = {}

@client.command()
@is_whitelisted()
async def unbanlogs(ctx, channel_id: int = None):
    if channel_id is None:
        embed = discord.Embed(title="Error", description="Please specify the channel ID: `.unbanlogs <channel_id>`.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    guild_id = ctx.guild.id
    unban_logs[guild_id] = channel_id
    embed = discord.Embed(title="Unban Logs Channel Set", description=f"Unban logs will now be sent to <#{channel_id}>", color=0x00ff00)
    await ctx.send(embed=embed)

@client.command()
@is_whitelisted()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    guild = ctx.guild
    try:
        user = await client.fetch_user(user_id)
        await guild.unban(user)
        await ctx.send(f'Successfully unbanned {user.name} (ID: {user_id})')
    except discord.NotFound:
        await ctx.send('User not found.')
    except discord.Forbidden:
        await ctx.send('I do not have permission to unban this user.')
    except discord.HTTPException as e:
        await ctx.send(f'An error occurred: {e}')


@client.event
async def on_member_ban(guild, member):
    debug_antiraid(f"Member banned: {member.name} (ID: {member.id})")
    
    # Antiraid protection for mass bans
    if antiraid_enabled and guild.owner_id != member.id:
        debug_antiraid(f"Antiraid enabled, checking for bans...")
        try:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
                debug_antiraid(f"Found ban entry: {entry.user.name} banned {entry.target.name}")
                if entry.target.id == member.id and (time.time() - entry.created_at.timestamp()) < 5:
                    debug_antiraid(f"Recent ban detected by {entry.user.name}")
                    # Track the ban action
                    user_id = entry.user.id
                    if user_id not in user_action_timestamps:
                        user_action_timestamps[user_id] = {'bans': []}
                    elif 'bans' not in user_action_timestamps[user_id]:
                        user_action_timestamps[user_id]['bans'] = []
                    
                    user_action_timestamps[user_id]['bans'].append(time.time())
                    debug_antiraid(f"Added ban timestamp for {entry.user.name}. Total bans: {len(user_action_timestamps[user_id]['bans'])}")
                    
                    # Remove old timestamps (older than 4 seconds)
                    user_action_timestamps[user_id]['bans'] = [
                        t for t in user_action_timestamps[user_id]['bans'] 
                        if time.time() - t < 4
                    ]
                    debug_antiraid(f"After cleanup: {len(user_action_timestamps[user_id]['bans'])} bans in last 4 seconds")
                    
                    # Check if user is whitelisted
                    if user_id in antiraid_whitelist:
                        debug_antiraid(f"User {entry.user.name} is whitelisted, skipping ban")
                        break
                    
                    # If 2 or more bans in 4 seconds, ban the user
                    if len(user_action_timestamps[user_id]['bans']) >= 2:
                        debug_antiraid(f"BANNING {entry.user.name} for mass bans!")
                        try:
                            await guild.ban(entry.user, reason="Antiraid: Mass ban detection")
                            embed = discord.Embed(
                                title="🛡️ Antiraid Protection",
                                description=f"**{entry.user.name}** has been banned for mass banning members.",
                                color=0xff0000
                            )
                            embed.add_field(name="Action", value="Mass ban detection", inline=False)
                            embed.add_field(name="Bans", value=f"{len(user_action_timestamps[user_id]['bans'])} in 4 seconds", inline=False)
                            
                            # Send to antiraid logs channel if configured
                            logs_channel_id = antiraid_logs_channels.get(str(guild.id))
                            if logs_channel_id:
                                logs_channel = guild.get_channel(logs_channel_id)
                                if logs_channel and logs_channel.permissions_for(guild.me).send_messages:
                                    await logs_channel.send(embed=embed)
                                else:
                                    # Fallback to first available channel
                                    for channel in guild.text_channels:
                                        if channel.permissions_for(guild.me).send_messages:
                                            await channel.send(embed=embed)
                                            break
                            else:
                                # Send to first available channel
                                for channel in guild.text_channels:
                                    if channel.permissions_for(guild.me).send_messages:
                                        await channel.send(embed=embed)
                                        break
                        except Exception as e:
                            debug_antiraid(f"Error banning user: {e}")
                    break
        except Exception as e:
            debug_antiraid(f"Error in ban detection: {e}")
    else:
        debug_antiraid(f"Antiraid disabled or owner banned")
    
    # Original ban logging functionality
    async for entry in guild.audit_logs(action=discord.AuditLogAction.ban):
        if entry.target == member:
            ban_embed = discord.Embed(title="Member Banned", color=0xff0000)
            ban_embed.add_field(name="Banned Member", value=member.mention)
            ban_embed.add_field(name="Banned By", value=entry.user.mention)
            ban_embed.add_field(name="Reason", value=entry.reason if entry.reason else "No reason provided")

            guild_id = guild.id
            if guild_id in ban_logs:
                banlogs = client.get_channel(ban_logs[guild_id])
                if banlogs is not None:
                    await banlogs.send(embed=ban_embed)
                else:
                    print(f"Failed to find the logging channel for ban of {member.display_name} ({member.id}) in guild {guild.name} ({guild.id}). Make sure the channel ID is correct.")
            else:
                print(f"No ban logs channel configured for guild {guild.name} ({guild.id}). Please use .banlogs to set it up.")
            break


@client.event
async def on_guild_role_delete(role):
    """Monitor for mass role deletions"""
    debug_antiraid(f"Role deleted: {role.name} (ID: {role.id})")
    
    if not antiraid_enabled:
        debug_antiraid("Antiraid disabled, skipping role deletion check")
        return
    
    debug_antiraid("Antiraid enabled, checking for role deletions...")
    try:
        async for entry in role.guild.audit_logs(action=discord.AuditLogAction.role_delete, limit=1):
            try:
                debug_antiraid(f"Found role deletion entry: {entry.user.name} deleted role")
                if entry.target.id == role.id and (time.time() - entry.created_at.timestamp()) < 5:
                    debug_antiraid(f"Recent role deletion detected by {entry.user.name}")
                    # Track the role deletion action
                    user_id = entry.user.id
                    if user_id not in user_action_timestamps:
                        user_action_timestamps[user_id] = {'role_deletions': []}
                    elif 'role_deletions' not in user_action_timestamps[user_id]:
                        user_action_timestamps[user_id]['role_deletions'] = []
                    
                    user_action_timestamps[user_id]['role_deletions'].append(time.time())
                    debug_antiraid(f"Added role deletion timestamp for {entry.user.name}. Total deletions: {len(user_action_timestamps[user_id]['role_deletions'])}")
                    
                    # Remove old timestamps (older than 4 seconds)
                    user_action_timestamps[user_id]['role_deletions'] = [
                        t for t in user_action_timestamps[user_id]['role_deletions'] 
                        if time.time() - t < 4
                    ]
                    debug_antiraid(f"After cleanup: {len(user_action_timestamps[user_id]['role_deletions'])} role deletions in last 4 seconds")
                    
                    # Check if user is whitelisted
                    if user_id in antiraid_whitelist:
                        debug_antiraid(f"User {entry.user.name} is whitelisted, skipping ban")
                        return
                    
                    # If 2 or more role deletions in 4 seconds, ban the user
                    if len(user_action_timestamps[user_id]['role_deletions']) >= 2:
                        debug_antiraid(f"BANNING {entry.user.name} for mass role deletions!")
                        try:
                            await role.guild.ban(entry.user, reason="Antiraid: Mass role deletion detection")
                            embed = discord.Embed(
                                title="🛡️ Antiraid Protection",
                                description=f"**{entry.user.name}** has been banned for mass deleting roles.",
                                color=0xff0000
                            )
                            embed.add_field(name="Action", value="Mass role deletion detection", inline=False)
                            embed.add_field(name="Role Deletions", value=f"{len(user_action_timestamps[user_id]['role_deletions'])} in 4 seconds", inline=False)
                            
                            # Send to antiraid logs channel if configured
                            logs_channel_id = antiraid_logs_channels.get(str(role.guild.id))
                            if logs_channel_id:
                                logs_channel = role.guild.get_channel(logs_channel_id)
                                if logs_channel and logs_channel.permissions_for(role.guild.me).send_messages:
                                    await logs_channel.send(embed=embed)
                                else:
                                    # Fallback to first available channel
                                    for channel in role.guild.text_channels:
                                        if channel.permissions_for(role.guild.me).send_messages:
                                            await channel.send(embed=embed)
                                            break
                            else:
                                # Send to first available channel
                                for channel in role.guild.text_channels:
                                    if channel.permissions_for(role.guild.me).send_messages:
                                        await channel.send(embed=embed)
                                        break
                        except Exception as e:
                            debug_antiraid(f"Error banning user: {e}")
            except Exception as e:
                debug_antiraid(f"Error processing role deletion entry: {e}")
    except Exception as e:
        debug_antiraid(f"Error in role deletion detection: {e}")


@client.event
async def on_member_unban(guild, member):
    async for entry in guild.audit_logs(action=discord.AuditLogAction.unban):
        if entry.target == member:
            unban_embed = discord.Embed(title="Member Unbanned", color=0x00ff00)
            unban_embed.add_field(name="Unbanned Member", value=member.mention)
            unban_embed.add_field(name="Unbanned By", value=entry.user.mention)

            guild_id = guild.id
            if guild_id in unban_logs:
                unbanlogs = client.get_channel(unban_logs[guild_id])
                if unbanlogs is not None:
                    await unbanlogs.send(embed=unban_embed)
                else:
                    print(f"Failed to find the logging channel for unban of {member.display_name} ({member.id}) in guild {guild.name} ({guild.id}). Make sure the channel ID is correct.")
            else:
                print(f"No unban logs channel configured for guild {guild.name} ({guild.id}). Please use .unbanlogs to set it up.")
            break

@client.event
async def on_guild_channel_create(channel):
    """Monitor for mass channel creation"""
    debug_antiraid(f"Channel created: {channel.name} (ID: {channel.id})")
    
    if not antiraid_enabled:
        debug_antiraid("Antiraid disabled, skipping channel creation check")
        return
    
    debug_antiraid("Antiraid enabled, checking for channel creation...")
    try:
        async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_create, limit=1):
            try:
                debug_antiraid(f"Found channel creation entry: {entry.user.name} created channel")
                if entry.target.id == channel.id and (time.time() - entry.created_at.timestamp()) < 5:
                    debug_antiraid(f"Recent channel creation detected by {entry.user.name}")
                    # Track the channel creation action
                    user_id = entry.user.id
                    if user_id not in user_action_timestamps:
                        user_action_timestamps[user_id] = {}
                    
                    if 'channel_creations' not in user_action_timestamps[user_id]:
                        user_action_timestamps[user_id]['channel_creations'] = []
                    
                    user_action_timestamps[user_id]['channel_creations'].append(time.time())
                    debug_antiraid(f"Added channel creation timestamp for {entry.user.name}. Total channel creations: {len(user_action_timestamps[user_id]['channel_creations'])}")
                    
                    # Remove old timestamps (older than 4 seconds)
                    user_action_timestamps[user_id]['channel_creations'] = [
                        t for t in user_action_timestamps[user_id]['channel_creations'] 
                        if time.time() - t < 4
                    ]
                    debug_antiraid(f"After cleanup: {len(user_action_timestamps[user_id]['channel_creations'])} channel creations in last 4 seconds")
                    
                    # Check if user is whitelisted
                    if user_id in antiraid_whitelist:
                        debug_antiraid(f"User {entry.user.name} is whitelisted, skipping kick")
                        break
                    
                    # If 3 or more channel creations in 4 seconds, kick the user
                    if len(user_action_timestamps[user_id]['channel_creations']) >= 3:
                        debug_antiraid(f"KICKING {entry.user.name} for mass channel creation!")
                        try:
                            await entry.user.kick(reason="Antiraid: Mass channel creation detection")
                            embed = discord.Embed(
                                title="🛡️ Antiraid Protection",
                                description=f"**{entry.user.name}** has been kicked for mass creating channels.",
                                color=0xff0000
                            )
                            embed.add_field(name="Action", value="Mass channel creation detection", inline=False)
                            embed.add_field(name="Channel Creations", value=f"{len(user_action_timestamps[user_id]['channel_creations'])} in 4 seconds", inline=False)
                            
                            # Send to antiraid logs channel if configured
                            logs_channel_id = antiraid_logs_channels.get(str(channel.guild.id))
                            if logs_channel_id:
                                logs_channel = channel.guild.get_channel(logs_channel_id)
                                if logs_channel and logs_channel.permissions_for(channel.guild.me).send_messages:
                                    await logs_channel.send(embed=embed)
                                else:
                                    # Fallback to first available channel
                                    for ch in channel.guild.text_channels:
                                        if ch.permissions_for(channel.guild.me).send_messages:
                                            await ch.send(embed=embed)
                                            break
                            else:
                                # Send to first available channel
                                for ch in channel.guild.text_channels:
                                    if ch.permissions_for(channel.guild.me).send_messages:
                                        await ch.send(embed=embed)
                                        break
                        except Exception as e:
                            debug_antiraid(f"Error kicking user: {e}")
                    break
            except Exception as e:
                debug_antiraid(f"Error processing channel creation entry: {e}")
    except Exception as e:
        debug_antiraid(f"Error in channel creation detection: {e}")

@client.event
async def on_guild_channel_delete(channel):
    """Monitor for mass channel deletion"""
    debug_antiraid(f"Channel deleted: {channel.name} (ID: {channel.id})")
    
    if not antiraid_enabled:
        debug_antiraid("Antiraid disabled, skipping channel deletion check")
        return
    
    debug_antiraid("Antiraid enabled, checking for channel deletion...")
    try:
        async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_delete, limit=1):
            try:
                debug_antiraid(f"Found channel deletion entry: {entry.user.name} deleted channel")
                if entry.target.id == channel.id and (time.time() - entry.created_at.timestamp()) < 5:
                    debug_antiraid(f"Recent channel deletion detected by {entry.user.name}")
                    # Track the channel deletion action
                    user_id = entry.user.id
                    if user_id not in user_action_timestamps:
                        user_action_timestamps[user_id] = {}
                    
                    if 'channel_deletions' not in user_action_timestamps[user_id]:
                        user_action_timestamps[user_id]['channel_deletions'] = []
                    
                    user_action_timestamps[user_id]['channel_deletions'].append(time.time())
                    debug_antiraid(f"Added channel deletion timestamp for {entry.user.name}. Total channel deletions: {len(user_action_timestamps[user_id]['channel_deletions'])}")
                    
                    # Remove old timestamps (older than 4 seconds)
                    user_action_timestamps[user_id]['channel_deletions'] = [
                        t for t in user_action_timestamps[user_id]['channel_deletions'] 
                        if time.time() - t < 4
                    ]
                    debug_antiraid(f"After cleanup: {len(user_action_timestamps[user_id]['channel_deletions'])} channel deletions in last 4 seconds")
                    
                    # Check if user is whitelisted
                    if user_id in antiraid_whitelist:
                        debug_antiraid(f"User {entry.user.name} is whitelisted, skipping kick")
                        break
                    
                    # If 3 or more channel deletions in 4 seconds, kick the user
                    if len(user_action_timestamps[user_id]['channel_deletions']) >= 3:
                        debug_antiraid(f"KICKING {entry.user.name} for mass channel deletion!")
                        try:
                            await entry.user.kick(reason="Antiraid: Mass channel deletion detection")
                            embed = discord.Embed(
                                title="🛡️ Antiraid Protection",
                                description=f"**{entry.user.name}** has been kicked for mass deleting channels.",
                                color=0xff0000
                            )
                            embed.add_field(name="Action", value="Mass channel deletion detection", inline=False)
                            embed.add_field(name="Channel Deletions", value=f"{len(user_action_timestamps[user_id]['channel_deletions'])} in 4 seconds", inline=False)
                            
                            # Send to antiraid logs channel if configured
                            logs_channel_id = antiraid_logs_channels.get(str(channel.guild.id))
                            if logs_channel_id:
                                logs_channel = channel.guild.get_channel(logs_channel_id)
                                if logs_channel and logs_channel.permissions_for(channel.guild.me).send_messages:
                                    await logs_channel.send(embed=embed)
                                else:
                                    # Fallback to first available channel
                                    for ch in channel.guild.text_channels:
                                        if ch.permissions_for(channel.guild.me).send_messages:
                                            await ch.send(embed=embed)
                                            break
                            else:
                                # Send to first available channel
                                for ch in channel.guild.text_channels:
                                    if ch.permissions_for(channel.guild.me).send_messages:
                                        await ch.send(embed=embed)
                                        break
                        except Exception as e:
                            debug_antiraid(f"Error kicking user: {e}")
                    break
            except Exception as e:
                debug_antiraid(f"Error processing channel deletion entry: {e}")
    except Exception as e:
        debug_antiraid(f"Error in channel deletion detection: {e}")

@client.event
async def on_guild_role_create(role):
    """Monitor for mass role creation"""
    debug_antiraid(f"Role created: {role.name} (ID: {role.id})")
    
    if not antiraid_enabled:
        debug_antiraid("Antiraid disabled, skipping role creation check")
        return
    
    debug_antiraid("Antiraid enabled, checking for role creation...")
    try:
        async for entry in role.guild.audit_logs(action=discord.AuditLogAction.role_create, limit=1):
            try:
                debug_antiraid(f"Found role creation entry: {entry.user.name} created role")
                if entry.target.id == role.id and (time.time() - entry.created_at.timestamp()) < 5:
                    debug_antiraid(f"Recent role creation detected by {entry.user.name}")
                    # Track the role creation action
                    user_id = entry.user.id
                    if user_id not in user_action_timestamps:
                        user_action_timestamps[user_id] = {}
                    
                    if 'role_creations' not in user_action_timestamps[user_id]:
                        user_action_timestamps[user_id]['role_creations'] = []
                    
                    user_action_timestamps[user_id]['role_creations'].append(time.time())
                    debug_antiraid(f"Added role creation timestamp for {entry.user.name}. Total role creations: {len(user_action_timestamps[user_id]['role_creations'])}")
                    
                    # Remove old timestamps (older than 4 seconds)
                    user_action_timestamps[user_id]['role_creations'] = [
                        t for t in user_action_timestamps[user_id]['role_creations'] 
                        if time.time() - t < 4
                    ]
                    debug_antiraid(f"After cleanup: {len(user_action_timestamps[user_id]['role_creations'])} role creations in last 4 seconds")
                    
                    # Check if user is whitelisted
                    if user_id in antiraid_whitelist:
                        debug_antiraid(f"User {entry.user.name} is whitelisted, skipping kick")
                        break
                    
                    # If 3 or more role creations in 4 seconds, kick the user
                    if len(user_action_timestamps[user_id]['role_creations']) >= 3:
                        debug_antiraid(f"KICKING {entry.user.name} for mass role creation!")
                        try:
                            await entry.user.kick(reason="Antiraid: Mass role creation detection")
                            embed = discord.Embed(
                                title="🛡️ Antiraid Protection",
                                description=f"**{entry.user.name}** has been kicked for mass creating roles.",
                                color=0xff0000
                            )
                            embed.add_field(name="Action", value="Mass role creation detection", inline=False)
                            embed.add_field(name="Role Creations", value=f"{len(user_action_timestamps[user_id]['role_creations'])} in 4 seconds", inline=False)
                            
                            # Send to antiraid logs channel if configured
                            logs_channel_id = antiraid_logs_channels.get(str(role.guild.id))
                            if logs_channel_id:
                                logs_channel = role.guild.get_channel(logs_channel_id)
                                if logs_channel and logs_channel.permissions_for(role.guild.me).send_messages:
                                    await logs_channel.send(embed=embed)
                                else:
                                    # Fallback to first available channel
                                    for ch in role.guild.text_channels:
                                        if ch.permissions_for(role.guild.me).send_messages:
                                            await ch.send(embed=embed)
                                            break
                            else:
                                # Send to first available channel
                                for ch in role.guild.text_channels:
                                    if ch.permissions_for(role.guild.me).send_messages:
                                        await ch.send(embed=embed)
                                        break
                        except Exception as e:
                            debug_antiraid(f"Error kicking user: {e}")
                    break
            except Exception as e:
                debug_antiraid(f"Error processing role creation entry: {e}")
    except Exception as e:
        debug_antiraid(f"Error in role creation detection: {e}")

timeoutlogs_channel_id = None

import json
from discord.ext import commands

def load_timeoutlogs_channels():
    try:
        with open("timeoutlogs_channels.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        with open("timeoutlogs_channels.json", "w") as file:
            json.dump({}, file)
        return {}
def save_timeoutlogs_channels(channels):
    with open("timeoutlogs_channels.json", "w") as file:
        json.dump(channels, file)

timeoutlogs_channels = load_timeoutlogs_channels()

@client.command()
@is_whitelisted()
async def rules(ctx, *, content):
    if ctx.author.guild_permissions.administrator:
        await ctx.message.delete()

        embed = discord.Embed(description=content, color=embed_color)

        await ctx.send(embed=embed)
    else:
        await ctx.send("You do not have permission to use this command.")


@client.command()
@is_whitelisted()
async def say(ctx, *, content):
    if ctx.author.guild_permissions.administrator:
        await ctx.message.delete()

        embed = discord.Embed(description=content, color=embed_color)

        await ctx.send(embed=embed)
    else:
        await ctx.send("You do not have permission to use this command.")


@client.command(name='snipe', aliases=['s'])
@is_whitelisted()
async def snipe(ctx, message_index: int = 1):
    # Get deleted messages for the channel
    channel_messages = last_deleted_messages.get(ctx.channel.id, [])
    
    if not channel_messages:
        await ctx.send('No recently deleted messages to snipe.')
        return
    
    # Validate message index
    if message_index < 1 or message_index > len(channel_messages):
        await ctx.send(f'Invalid message index. Available messages: 1-{len(channel_messages)}')
        return
    
    # Get the requested message (index is 1-based, so subtract 1)
    message_data = channel_messages[-(message_index)]
    deleted_message = message_data['message']
    deleted_at = message_data['deleted_at']
    
    # Calculate time since deletion
    time_since_deletion = time.time() - deleted_at
    seconds = int(time_since_deletion)
    
    # Create embed
    embed = discord.Embed(color=0x2a2d30)
    embed.set_author(
        name=deleted_message.author.display_name,
        icon_url=deleted_message.author.avatar.url if deleted_message.author.avatar else deleted_message.author.default_avatar.url
    )
    
    # Add message content
    if deleted_message.content:
        embed.description = deleted_message.content
    else:
        embed.description = "*[No text content]*"
    
    # Add attachments info if any
    if deleted_message.attachments:
        attachment_text = f"\n\n**Attachments:** {len(deleted_message.attachments)} file(s)"
        embed.description += attachment_text
    
    # Set footer with timestamp and message counter
    embed.set_footer(text=f"Deleted {seconds} seconds ago • {message_index}/{len(channel_messages)}")
    
    await ctx.send(embed=embed)


@client.command(name='clearsnipes', aliases=['cs'])
@is_whitelisted()
@commands.has_permissions(manage_messages=True)
async def clearsnipes(ctx):
    """Clear all stored deleted messages for the current channel"""
    channel_id = ctx.channel.id
    
    if channel_id in last_deleted_messages:
        deleted_count = len(last_deleted_messages[channel_id])
        del last_deleted_messages[channel_id]
        embed = discord.Embed(
            title="✅ Snipes Cleared",
            description=f"Cleared {deleted_count} stored deleted messages from this channel.",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="ℹ️ No Snipes to Clear",
            description="No deleted messages are currently stored for this channel.",
            color=0xffff00
        )
        await ctx.send(embed=embed)


@client.command(name='antiraid', aliases=['ar'])
@is_whitelisted()
async def antiraid(ctx, user_id: int = None):
    # Check if user is the server owner
    if ctx.author.id != ctx.guild.owner_id:
        embed = discord.Embed(
            title="❌ Access Denied",
            description="Only the server owner can use this command.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    """Enable/disable antiraid protection and manage whitelist"""
    global antiraid_enabled, antiraid_whitelist
    
    if user_id is None:
        # Toggle antiraid on/off
        antiraid_enabled = not antiraid_enabled
        status = "enabled" if antiraid_enabled else "disabled"
        debug_antiraid(f"Antiraid toggled to: {status}")
        embed = discord.Embed(
            title="🛡️ Antiraid System",
            description=f"Antiraid protection is now **{status}**",
            color=0x00ff00 if antiraid_enabled else 0xff0000
        )
        embed.add_field(name="Whitelisted Users", value=f"{len(antiraid_whitelist)} users" if antiraid_whitelist else "None", inline=False)
        embed.add_field(name="Protection", value="• Mass kick detection\n• Mass ban detection\n• Mass role deletion\n• Mass channel deletion", inline=False)
        await ctx.send(embed=embed)
    else:
        # Add/remove user from whitelist
        if user_id in antiraid_whitelist:
            antiraid_whitelist.remove(user_id)
            action = "removed from"
            debug_antiraid(f"User {user_id} removed from whitelist")
        else:
            antiraid_whitelist.add(user_id)
            action = "added to"
            debug_antiraid(f"User {user_id} added to whitelist")
        
        embed = discord.Embed(
            title="🛡️ Antiraid Whitelist",
            description=f"User <@{user_id}> has been **{action}** the antiraid whitelist.",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

@client.command(name='antiraidlogs')
@is_whitelisted()
async def antiraidlogs(ctx, channel_id: int = None):
    # Check if user is the server owner
    if ctx.author.id != ctx.guild.owner_id:
        embed = discord.Embed(
            title="❌ Access Denied",
            description="Only the server owner can use this command.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    """Set the channel for antiraid logs"""
    global antiraid_logs_channels
    
    if channel_id is None:
        # Show current logs channel
        current_channel_id = antiraid_logs_channels.get(str(ctx.guild.id))
        if current_channel_id:
            channel = ctx.guild.get_channel(current_channel_id)
            if channel:
                embed = discord.Embed(
                    title="📋 Antiraid Logs",
                    description=f"Antiraid logs are currently being sent to {channel.mention}",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="❌ Channel Not Found",
                    description=f"The configured logs channel (ID: {current_channel_id}) no longer exists.",
                    color=0xff0000
                )
        else:
            embed = discord.Embed(
                title="📋 Antiraid Logs",
                description="No antiraid logs channel is currently configured.",
                color=0xffff00
            )
        await ctx.send(embed=embed)
        return
    
    # Set new logs channel
    channel = ctx.guild.get_channel(channel_id)
    if not channel:
        embed = discord.Embed(
            title="❌ Invalid Channel",
            description=f"Channel with ID `{channel_id}` not found in this server.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    if not isinstance(channel, discord.TextChannel):
        embed = discord.Embed(
            title="❌ Invalid Channel Type",
            description="The specified channel must be a text channel.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    # Check if bot has permission to send messages in the channel
    if not channel.permissions_for(ctx.guild.me).send_messages:
        embed = discord.Embed(
            title="❌ Missing Permissions",
            description=f"I don't have permission to send messages in {channel.mention}",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    # Save the channel ID
    antiraid_logs_channels[str(ctx.guild.id)] = channel_id
    save_antiraid_logs_channels()
    
    embed = discord.Embed(
        title="✅ Antiraid Logs Configured",
        description=f"Antiraid logs will now be sent to {channel.mention}",
        color=0x00ff00
    )
    embed.add_field(name="Channel", value=channel.mention, inline=False)
    embed.add_field(name="Channel ID", value=str(channel_id), inline=False)
    await ctx.send(embed=embed)

@client.command()
@is_whitelisted()
@commands.has_permissions(administrator=True)
async def messagelogs(ctx, channel_id: int = None):
    global message_logs_channels

    if channel_id is None:
        embed = discord.Embed(title="Error", description="Please use the command in the format: messagelogs <channel id>", color=0xff0000)
        await ctx.send(embed=embed)
        return

    channel = ctx.guild.get_channel(channel_id)
    if channel:
        message_logs_channels[str(ctx.guild.id)] = channel_id
        embed = discord.Embed(title="Message Logs Channel Updated", description=f"Message logs will now be sent to {channel.mention}.", color=0x00ff00)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="Invalid channel ID. Please provide a valid channel ID.", color=0xff0000)
        await ctx.send(embed=embed)

@client.command()
@is_whitelisted()
@commands.has_permissions(administrator=True)
async def messagelogstop(ctx):
    global message_logs_channels

    guild_id = str(ctx.guild.id)

    if guild_id in message_logs_channels:
        message_logs_channels.pop(guild_id)
        embed = discord.Embed(title="Message Logs Stopped", description="Logging of message edits and deletions has been stopped in this server.", color=0xff0000)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="Message logging is not enabled in this server.", color=0xff0000)
        await ctx.send(embed=embed)



@client.command()
@is_whitelisted()
async def memberupdate(ctx, channel_id: int = None):
    if ctx.author.guild_permissions.administrator:
        global member_update_logs
        guild_id = str(ctx.guild.id)

        if channel_id is None:
            embed = discord.Embed(title="Error", description="Please use the command in the format: memberupdate <channel id>", color=0xff0000)
            await ctx.send(embed=embed)
            return

        logs_channel = ctx.guild.get_channel(channel_id)
        if logs_channel:
            member_update_logs[guild_id] = channel_id
            embed = discord.Embed(title="Member Update Logs Channel Updated", description=f"Logs for member updates will now be sent to {logs_channel.mention}.", color=0x00ff00)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Error", description="Failed to find the specified channel. Please make sure the ID is correct.", color=0xff0000)
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="You need to be an administrator to use this command.", color=0xff0000)
        await ctx.send(embed=embed)

@client.command()
@is_whitelisted()
async def memberupdatestop(ctx):
    if ctx.author.guild_permissions.administrator:
        global member_update_logs
        guild_id = str(ctx.guild.id)

        if guild_id in member_update_logs:
            member_update_logs.pop(guild_id)
            embed = discord.Embed(title="Member Update Logs Stopped", description="Logging of member updates has been stopped in this server.", color=0xff0000)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Error", description="Member update logging is not enabled in this server.", color=0xff0000)
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="You need to be an administrator to use this command.", color=0xff0000)
        await ctx.send(embed=embed)



# Function to load channel IDs for a specific guild
def load_channel_ids(guild_id):
    try:
        with open(f"{guild_id}_channel_ids.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Function to save channel IDs for a specific guild
def save_channel_ids(guild_id, data):
    with open(f"{guild_id}_channel_ids.json", "w") as file:
        json.dump(data, file)

# Load saved channel IDs for a specific guild
def get_channel_ids(guild_id):
    channel_ids = load_channel_ids(guild_id)
    return {
        "display_name_logs_channel_id": channel_ids.get("display_name_logs_channel_id"),
        "avatar_logs_channel_id": channel_ids.get("avatar_logs_channel_id"),
        "log_channel_id": channel_ids.get("log_channel_id")
    }

# Commands to set logging channels for a guild
@client.command()
@is_whitelisted()
@commands.has_permissions(administrator=True)
async def displaylogs(ctx, channel_id: int):
    channel_ids = get_channel_ids(ctx.guild.id)
    channel_ids["display_name_logs_channel_id"] = channel_id
    save_channel_ids(ctx.guild.id, channel_ids)
    await ctx.send(f"I will now send display name logs to <#{channel_id}>.")

@client.command()
@is_whitelisted()
@commands.has_permissions(administrator=True)
async def avatarlogs(ctx, channel_id: int):
    channel_ids = get_channel_ids(ctx.guild.id)
    channel_ids["avatar_logs_channel_id"] = channel_id
    save_channel_ids(ctx.guild.id, channel_ids)
    await ctx.send(f"I will now send avatar logs to <#{channel_id}>.")

@client.command()
@is_whitelisted()
@commands.has_permissions(administrator=True)
async def usernamelogs(ctx, channel_id: int):
    channel_ids = get_channel_ids(ctx.guild.id)
    channel_ids["log_channel_id"] = channel_id
    save_channel_ids(ctx.guild.id, channel_ids)
    await ctx.send(f"I will now send all logs to <#{channel_id}>.")

# Event to handle user updates for all guilds
@client.event
async def on_user_update(before, after):
    for guild in client.guilds:
        channel_ids = get_channel_ids(guild.id)
        display_name_logs_channel = guild.get_channel(channel_ids["display_name_logs_channel_id"])
        avatar_logs_channel = guild.get_channel(channel_ids["avatar_logs_channel_id"])
        log_channel = guild.get_channel(channel_ids["log_channel_id"])

        if log_channel:
            if before.name != after.name:  # Username change
                change_embed = discord.Embed(
                    color=0x2a2d30
                )
                change_embed.add_field(name="Username", value=f"**{before.name}** is now available")
                await log_channel.send(embed=change_embed)

        if display_name_logs_channel:
            if before.display_name != after.display_name:  # Display name change
                new_avatar_url = after.avatar.url if after.avatar else after.default_avatar.url
                change_embed = discord.Embed(
                    description=f"{after.mention} has changed their display name.",
                    color=0x2a2d30
                )
                change_embed.set_thumbnail(url=new_avatar_url)  # Set the user's avatar as thumbnail
                change_embed.add_field(name="Before", value=before.display_name, inline=False)
                change_embed.add_field(name="After", value=after.display_name, inline=False)
                await display_name_logs_channel.send(embed=change_embed)

        if avatar_logs_channel:
            if before.avatar != after.avatar:  # Avatar change
                old_avatar_url = before.avatar.url if before.avatar else before.default_avatar.url
                new_avatar_url = after.avatar.url if after.avatar else after.default_avatar.url

                old_avatar_embed = discord.Embed(
                    color=0x2a2d30
                )
                old_avatar_embed.set_image(url=old_avatar_url)
                await avatar_logs_channel.send(embed=old_avatar_embed)

                new_avatar_embed = discord.Embed(
                    color=0x2a2d30
                )
                new_avatar_embed.set_image(url=new_avatar_url)
                await avatar_logs_channel.send(embed=new_avatar_embed)


LOGS_CHANNEL_FILE = "logs_channel.json"

# Function to read the logs channel ID from the JSON file
def read_logs_channel_id():
    try:
        with open(LOGS_CHANNEL_FILE, "r") as file:
            data = json.load(file)
            return data.get("logs_channel_id")
    except FileNotFoundError:
        return None

# Function to write the logs channel ID to the JSON file
def write_logs_channel_id(channel_id):
    data = {"logs_channel_id": channel_id}
    with open(LOGS_CHANNEL_FILE, "w") as file:
        json.dump(data, file)

# Initialize logs channel ID
logs_channel_id = read_logs_channel_id()

@client.command()
@is_whitelisted()
@commands.has_permissions(administrator=True)
async def leavelogs(ctx, channel: discord.TextChannel):
    global logs_channel_id
    logs_channel_id = channel.id

    write_logs_channel_id(logs_channel_id)

    await ctx.send(f"I will now send leave logs to {channel.mention}.")



def load_settings():
    try:
        with open("welcome_settings.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_settings(settings):
    with open("welcome_settings.json", "w") as file:
        json.dump(settings, file)

settings = load_settings()

import json
from discord.ext import commands

def load_settings():
    try:
        with open("welcome_settings.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_settings(settings):
    with open("welcome_settings.json", "w") as file:
        json.dump(settings, file)

@client.event
async def on_ready():
    global settings
    settings = load_settings()

@client.command()
@is_whitelisted()
@commands.has_permissions(administrator=True)
async def welcome(ctx):
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel
    
    guild_id = str(ctx.guild.id)
    if guild_id not in settings:
        settings[guild_id] = {}

    guild_settings = settings[guild_id]

    embed = discord.Embed(color=0x2a2d30)

    embed.add_field(name="Role ID", value="Please provide the ID of the role you want to assign to new members (or type '0' for no role):")
    await ctx.send(embed=embed)
    role_msg = await client.wait_for('message', check=check)
    role_id = int(role_msg.content)
    embed.clear_fields()

    embed.add_field(name="Welcome Channel ID", value="Please provide the ID of the channel where you want to send the welcome message:")
    await ctx.send(embed=embed)
    channel_msg = await client.wait_for('message', check=check)
    channel_id = int(channel_msg.content)
    embed.clear_fields()

    embed.add_field(name="Welcome Log Channel ID", value="Please provide the ID of the channel where you want to log user joins:")
    await ctx.send(embed=embed)
    log_channel_msg = await client.wait_for('message', check=check)
    log_channel_id = int(log_channel_msg.content)
    embed.clear_fields()

    # Only set role_id if it's not 0
    if role_id != 0:
        guild_settings["role_id"] = role_id
    else:
        # Remove role_id if it exists
        guild_settings.pop("role_id", None)
    
    guild_settings["channel_id"] = channel_id
    guild_settings["log_channel_id"] = log_channel_id

    with open("welcome_settings.json", "w") as file:
        json.dump(settings, file)
    
    embed_settings_saved = discord.Embed(color=0x2a2d30)
    if role_id == 0:
        embed_settings_saved.add_field(name="Settings Saved", value="Welcome settings saved. No role will be assigned to new members. The welcome message will use the Stock Robux format.")
    else:
        embed_settings_saved.add_field(name="Settings Saved", value="Welcome settings saved. The welcome message will now automatically use the Stock Robux format.")
    await ctx.send(embed=embed_settings_saved)


@client.command()
@is_whitelisted()
@commands.has_permissions(administrator=True)
async def testwelcome(ctx):
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel
    
    guild_id = str(ctx.guild.id)
    guild_settings = settings.get(guild_id)

    if guild_settings:
        role_id = guild_settings.get("role_id")
        channel_id = guild_settings.get("channel_id")
        log_channel_id = guild_settings.get("log_channel_id")

        role = ctx.guild.get_role(role_id)
        welcome_channel = ctx.guild.get_channel(channel_id)
        log_channel = ctx.guild.get_channel(log_channel_id)

        if role and welcome_channel and log_channel:
            member = ctx.author  # You can change this if you want to test with a specific member
            
            # Create embed with the Stock Robux welcome message
            embed = discord.Embed(color=0x2a2d30)
            embed.title = "Welcome To Stock Robux!"
            embed.description = f"""**Welcome to Stock Robux, {member.mention}**

**To access the server, please verify yourself:**

✅ Go to https://canary.discord.com/channels/1286843093873852437/1286848144763781180
✅ Follow the instructions
✅ Gain full access to the server.

If you have any issues, make a support ticket in https://canary.discord.com/channels/1286843093873852437/1375559689936441436"""
            embed.set_image(url="https://cdn.discordapp.com/attachments/1232291016128729118/1394433866013606011/Stock_Robux.png?ex=6876cb3c&is=687579bc&hm=a8b319b06f6318dcb10bdcf68a4b7788dac4ea3ac2688f64b546c062b54b5622&")
            
            await welcome_channel.send(embed=embed)
            await ctx.send("Test welcome message sent.")
        else:
            await ctx.send("Couldn't send the test welcome message. Make sure the settings are properly configured.")
    else:
        await ctx.send("Welcome settings not found for this guild.")







@client.command()
@is_whitelisted()
async def noavatarkick(ctx, mode: str = None):
    """
    Toggle the no avatar kick feature on or off.
    
    Parameters:
        mode (str): "on" to enable, "off" to disable.
    """
    if mode is None:
        embed = discord.Embed(
            title="No Avatar Kick Command",
            description="specify whether you want to turn the feature 'on' or 'off'.",
            color=discord.Color.red()
        )
        embed.add_field(name="Example Usage:", value="`noavatarkick on` or `noavatarkick off`")
        await ctx.send(embed=embed)
        return

    guild_id = str(ctx.guild.id)
    if mode.lower() == "on":
        settings[guild_id] = {"no_avatar_kick": True}
        embed = discord.Embed(
            title="No Avatar Kick Feature",
            description="No avatar kick feature enabled.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    elif mode.lower() == "off":
        settings[guild_id] = {"no_avatar_kick": False}
        embed = discord.Embed(
            title="No Avatar Kick Feature",
            description="No avatar kick feature disabled.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="Invalid Mode",
            description="Please use 'on' or 'off' to toggle the feature.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


@client.event
async def on_member_join(member):
    await update_status()
    guild_id = str(member.guild.id)
    guild_settings = settings.get(guild_id, {})
    no_avatar_kick_enabled = guild_settings.get("no_avatar_kick", False)

    if no_avatar_kick_enabled and not member.bot and not member.avatar:
        await member.kick(reason='No profile picture.')

    if guild_settings:
        role_id = guild_settings.get("role_id")
        channel_id = guild_settings.get("channel_id")
        log_channel_id = guild_settings.get("log_channel_id")
        
        welcome_channel = member.guild.get_channel(channel_id)
        log_channel = member.guild.get_channel(log_channel_id)
        
        if welcome_channel and log_channel:
            # Create embed with the Stock Robux welcome message
            embed = discord.Embed(color=0x2a2d30)
            embed.title = "Welcome To Stock Robux!"
            embed.description = f"""**Welcome to Stock Robux, {member.mention}**

**To access the server, please verify yourself:**

✅ Go to https://canary.discord.com/channels/1286843093873852437/1286848144763781180
✅ Follow the instructions
✅ Gain full access to the server.

If you have any issues, make a support ticket in https://canary.discord.com/channels/1286843093873852437/1375559689936441436"""
            embed.set_image(url="https://cdn.discordapp.com/attachments/1232291016128729118/1394433866013606011/Stock_Robux.png?ex=6876cb3c&is=687579bc&hm=a8b319b06f6318dcb10bdcf68a4b7788dac4ea3ac2688f64b546c062b54b5622&")

            # Only add role if one is set
            if role_id:
                role = member.guild.get_role(role_id)
                if role:
                    await member.add_roles(role)
            
            await welcome_channel.send(embed=embed)
            
            # Log the join
            avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
            created_at = member.created_at.strftime("%B %d, %Y @ %I:%M %p")
            member_count = len(member.guild.members)
            log_embed = discord.Embed(color=0x00FF00)
            log_embed.set_author(name=f"{member.name}#{member.discriminator} joined the server ({member.id})", icon_url=avatar_url)
            log_embed.add_field(name="", value=f"**Created:** {created_at}", inline=True)
            log_embed.set_footer(text=f"Member Count: {member_count}")
            await log_channel.send(embed=log_embed)
    
    # Bot whitelisting logic
    try:
        async for entry in member.guild.audit_logs(action=discord.AuditLogAction.bot_add, limit=1):
            inviter_id = entry.user.id
            break
    except:
        inviter_id = None

    if member.bot and inviter_id in whitelisted_users:
        await member.guild.system_channel.send(f'{member} has joined the server and is whitelisted.')
    elif member.bot:
        await member.kick(reason='Only whitelisted users can add bots to the server.')





    

@client.command()
@is_whitelisted()
@commands.has_permissions(administrator=True)
async def welcomestop(ctx):
    guild_id = str(ctx.guild.id)
    if guild_id in settings:
        del settings[guild_id]
        save_settings(settings)
        await ctx.send("Welcome logging has been stopped for this server.")
    else:
        await ctx.send("Welcome logging is not enabled for this server.")

embed_color = 0x2a2d30 


@client.command(name='clear', aliases=['purge'])
@is_whitelisted()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, target: typing.Optional[discord.Member], amount: int = None):
    embed = discord.Embed(color=0x2a2d30)

    if amount is None or (target is None and amount is None):
        embed.description = "Please specify either the number of messages to delete or the user whose messages you want to delete. Usage: `clearr [user] <amount>`"
        await ctx.send(embed=embed)
        return

    if amount and amount <= 0:
        embed.description = "Please provide a positive number of messages to delete."
        await ctx.send(embed=embed)
        return

    if target:
        # Function to check if message is from the target user
        def check(message):
            return message.author == target

        # If amount is provided, delete messages from the user within a specific timeframe
        deleted = await ctx.channel.purge(limit=amount, check=check)
        embed.description = f"Deleted {len(deleted)} messages from {target.display_name}."
    else:
        try:
            # If no target user is specified, just delete the specified amount of messages
            await ctx.channel.purge(limit=amount + 1)
            embed.description = f"Deleted {amount} messages."
        except discord.Forbidden:
            embed.description = "I don't have permission to delete messages in this channel."

    await ctx.send(embed=embed, delete_after=5)



vanity_info = {}

async def apply_vanity(guild, vanity_settings):
    role_id = vanity_settings['role_id']
    channel_id = vanity_settings['channel_id']

    role = guild.get_role(role_id)
    channel = guild.get_channel(channel_id)

    if role and channel:
        pass

@client.command()
@is_whitelisted()
@commands.has_permissions(manage_messages=True)
async def vanity(ctx, vanity_text: str = None, channel_id: int = None, role_id: int = None):
    if vanity_text is None or channel_id is None or role_id is None:
        embed = discord.Embed(color=discord.Color.red())
        embed.description = "Please provide all required arguments. Usage: `vanity <vanity_text> <channel_id> <role_id>`"
        await ctx.send(embed=embed)
        return
    vanity_info[str(ctx.guild.id)] = {'role_id': role_id, 'channel_id': channel_id, 'vanity_text': vanity_text}

    embed = discord.Embed(color=discord.Color.green())
    embed.add_field(name="Vanity Settings Updated", value=f"Role ID: {role_id}\nChannel ID: {channel_id}\nVanity Text: {vanity_text}")
    await ctx.send(embed=embed)

@client.event
async def on_presence_update(before, after):
    guild_id = str(after.guild.id)
    if guild_id in vanity_info:
        vanity_settings = vanity_info[guild_id]
        role_id = vanity_settings['role_id']
        channel_id = vanity_settings['channel_id']
        vanity_text = vanity_settings.get('vanity_text', '')  

        if before.activities != after.activities:
            guild = after.guild
            role = guild.get_role(role_id)
            channel = guild.get_channel(channel_id)

            if any(isinstance(activity, discord.CustomActivity) and vanity_text in activity.name for activity in after.activities):
                if role and role not in after.roles and channel:
                    await after.add_roles(role)
                    await send_custom_status_message(channel, after, role, vanity_text)
            elif any(isinstance(activity, discord.CustomActivity) and vanity_text in activity.name for activity in before.activities):
                if role and role in after.roles and channel:
                    await after.remove_roles(role)
                    await send_removed_status_message(channel, after, vanity_text)

async def send_custom_status_message(channel, member, role, vanity_text):
    embed = discord.Embed(
        title="Status Update",
        description=f"{member.name} changed their status to {vanity_text} and received {role.mention}.",
        color=discord.Color.green()
    )
    avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
    embed.set_author(name=f"{member.name}", icon_url=avatar_url)
    embed.set_thumbnail(url=avatar_url)
    await channel.send(embed=embed)

async def send_removed_status_message(channel, member, vanity_text):
    embed = discord.Embed(
        title="Status Update",
        description=f"{member.name} removed '{vanity_text}' from their status and lost the role",
        color=discord.Color.red()
    )
    avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
    embed.set_author(name=f"{member.name}", icon_url=avatar_url)
    embed.set_thumbnail(url=avatar_url)
    await channel.send(embed=embed)

@client.command()
@is_whitelisted()
@commands.has_permissions(manage_messages=True)
async def vanitystop(ctx):
    guild_id = str(ctx.guild.id)
    if guild_id in vanity_info:
        del vanity_info[guild_id]
        await ctx.send("Vanity logging has been stopped for this server.")
    else:
        await ctx.send("Vanity logging is not enabled for this server.")
    await ctx.message.delete()


from discord.ext import commands
from datetime import datetime, timedelta

# Define dictionaries to store guild-specific information
allowed_role_ids = {}
create_role_cooldowns = {}
BLACKLISTED_WORDS = ["nigger", "faggot", "virgin", "simp", "admin", "mod", "owner"]
user_created_roles = {}


COOLDOWN_DURATION = 999999999

@client.command()
@is_whitelisted()
@commands.has_permissions(administrator=True)
async def setrole(ctx, role_id: int = None):
    global allowed_role_ids
    guild_id = ctx.guild.id

    if role_id is None:
        embed = discord.Embed(title="Error", description="You need to provide the role ID.", color=0xff0000)
        embed.add_field(name="Usage", value="`setrole  [role_id]`")
        await ctx.send(embed=embed)
        return

    allowed_role_ids[guild_id] = role_id
    embed = discord.Embed(title="Success", description=f"Booster role ID set to {role_id}.", color=0x00ff00)
    await ctx.send(embed=embed)

@client.command()
@is_whitelisted()
async def createrole(ctx, *args):
    guild_id = ctx.guild.id
    allowed_role_id = allowed_role_ids.get(guild_id)

    if allowed_role_id is None:
        embed = discord.Embed(title="Error", description="The booster role ID is not set. An administrator needs to set it using the `setrole` command.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if discord.utils.get(ctx.author.roles, id=allowed_role_id) is None:
        embed = discord.Embed(title="Error", description="You do not have permission to use this command.", color=0xff0000)
        await ctx.send(embed=embed)
        return
    
    if ctx.author.id in create_role_cooldowns.get(guild_id, {}):
        remaining_time = create_role_cooldowns[guild_id][ctx.author.id] - datetime.utcnow()
        if remaining_time.total_seconds() > 0:
            embed = discord.Embed(title="Error", description="You already made your role", color=0xff0000)
            await ctx.send(embed=embed)
            return

    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel

    if len(args) < 2:
        embed = discord.Embed(title="Error", description="Usage: `createrole [role name] [hex color]`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    role_name = ' '.join(args[:-1])
    color = args[-1]

    for word in BLACKLISTED_WORDS:
        if word.lower() in role_name.lower():
            embed = discord.Embed(title="Error", description="The role name contains a blacklisted word. Please choose another name.", color=0xff0000)
            await ctx.send(embed=embed)
            return

    try:
        color_int = int(color, 16)
        role = await ctx.guild.create_role(name=role_name, color=discord.Color(color_int))
        await ctx.author.add_roles(role)

        embed = discord.Embed(title="Success", description=f"Role '{role_name}' created and given to {ctx.author.mention}!", color=0x00ff00)
        await ctx.send(embed=embed)

        user_created_roles.setdefault(ctx.author.id, []).append(role.id)

        create_role_cooldowns.setdefault(guild_id, {})[ctx.author.id] = datetime.utcnow() + timedelta(seconds=COOLDOWN_DURATION)
    except ValueError:
        embed = discord.Embed(title="Error", description="Invalid hex color provided. Please provide a valid hex color.", color=0xff0000)
        await ctx.send(embed=embed)


import asyncio
import random
import discord

PEG = '🔸'
CHIP = '🔵'
EMPTY = '⬛'
SLOT = '⬜'
SLOT_EMOJIS = ['❌', '🥉', '🥈', '🏆', '💎', '🏆', '🥈']

# --- REGISTER AS A COMMAND ---
from main import client, balances

@client.command()
async def plinko(ctx, amount: int):
    user_id = str(ctx.author.id)
    if user_id not in balances:
        balances[user_id] = 1000
    if amount > balances[user_id]:
        await ctx.send(f"💰 You don't have enough balance to play Plinko for {amount}. Your balance is {balances[user_id]}.")
        return
    if amount <= 0:
        await ctx.send("❌ You must bet a positive amount!")
        return
    balances[user_id] -= amount
    board_width = 7
    board_height = 7
    start_col = random.randint(0, board_width - 1)
    board_str = render_plinko_board(board_width, board_height, [start_col], 0)
    embed = make_plinko_embed(ctx, amount, 1.0, 0, board_str, state='dropping')
    msg = await ctx.send(embed=embed)
    await run_plinko_game(ctx, amount, start_col, board_width, board_height, msg)

def make_plinko_embed(ctx, amount, multiplier, winnings, board_str, state='dropping', color=None):
    if color is None:
        color = discord.Color.blurple() if state == 'dropping' else (discord.Color.green() if winnings > 0 else discord.Color.red())
    embed = discord.Embed(
        title="Plinko!" if state == 'dropping' else ("🎉 You Win!" if winnings > 0 else "💥 You Lose!"),
        color=color
    )
    embed.add_field(name="Board", value=f"```\n{board_str}\n```", inline=False)
    embed.add_field(name="Bet", value=f"{amount} coins", inline=True)
    embed.add_field(name="Multiplier", value=f"x{multiplier}", inline=True)
    embed.add_field(name="Winnings", value=f"{winnings} coins", inline=True)
    embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    return embed

async def run_plinko_game(ctx, amount, start_col, width, height, message):
    slot_multipliers = [0, 0.5, 1, 2, 5, 2, 1]
    chip_col = start_col
    chip_path = [chip_col]
    for row in range(height):
        await asyncio.sleep(0.5)
        move = random.choice([-1, 0, 1])
        if chip_col == 0:
            move = random.choice([0, 1])
        elif chip_col == width-1:
            move = random.choice([-1, 0])
        chip_col += move
        chip_path.append(chip_col)
        board_str = render_plinko_board(width, height, chip_path, row+1)
        embed = make_plinko_embed(ctx, amount, slot_multipliers[chip_col], 0, board_str, state='dropping')
        await message.edit(embed=embed)
    multiplier = slot_multipliers[chip_col]
    winnings = int(amount * multiplier)
    user_id = str(ctx.author.id)
    if multiplier == 0:
        balances[user_id] -= amount
    else:
        balances[user_id] += winnings - amount
    final_board = render_plinko_board(width, height, chip_path, height, final=True)
    embed = make_plinko_embed(ctx, amount, multiplier, winnings, final_board, state='done', color=(discord.Color.green() if multiplier > 0 else discord.Color.red()))
    await message.edit(embed=embed)

def render_plinko_board(width, height, chip_path, chip_row, final=False):
    board = []
    for row in range(height):
        row_str = ''
        for col in range(width):
            if chip_path and row < len(chip_path) and row == chip_row and col == chip_path[row]:
                row_str += CHIP
            elif row < height-1 and (row % 2 == 0 and col % 2 == 1 or row % 2 == 1 and col % 2 == 0):
                row_str += PEG
            else:
                row_str += EMPTY
        board.append(row_str)
    slot_row = ''
    for col in range(width):
        if final and chip_path and col == chip_path[-1]:
            slot_row += SLOT_EMOJIS[col]
        else:
            slot_row += SLOT
    board.append(slot_row)
    return '\n'.join(board) 


@client.command()
@is_whitelisted()
@commands.has_permissions(administrator=True)
async def resetrole(ctx, user_id: int):
    guild_id = ctx.guild.id
    if user_id in create_role_cooldowns.get(guild_id, {}):
        del create_role_cooldowns[guild_id][user_id]
        embed = discord.Embed(title="Success", description=f"Cooldown for user with ID {user_id} has been reset.", color=discord.Color.green())
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Error", description=f"User with ID {user_id} is not on cooldown for creating roles.", color=discord.Color.red())
        await ctx.send(embed=embed)

@client.command()
@is_whitelisted()
async def renamerole(ctx, *new_name):
    guild_id = ctx.guild.id
    allowed_role_id = allowed_role_ids.get(guild_id)

    if allowed_role_id is None:
        embed = discord.Embed(title="Error", description="The booster role ID is not set. An administrator needs to set it using the `setrole` command.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if discord.utils.get(ctx.author.roles, id=allowed_role_id) is None:
        embed = discord.Embed(title="Error", description="You do not have permission to use this command.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if not new_name:
        embed = discord.Embed(title="Error", description="Usage: `renamerole [new role name]`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    new_name = ' '.join(new_name)
    user_created_roles_list = user_created_roles.get(ctx.author.id, [])
    if not user_created_roles_list:
        embed = discord.Embed(title="Error", description="You haven't created any roles to rename.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    role_id = user_created_roles_list[-1]
    role_to_rename = ctx.guild.get_role(role_id)

    if role_to_rename is None:
        embed = discord.Embed(title="Error", description="The specified role does not exist or was not created by you.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        await role_to_rename.edit(name=new_name)

        embed = discord.Embed(title="Success", description=f"Role renamed to '{new_name}'.", color=0x00ff00)
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(title="Error", description=f"An error occurred while renaming the role: {str(e)}", color=0xff0000)
        await ctx.send(embed=embed)

@client.command()
@is_whitelisted()
async def rolecolor(ctx, color: str):
    guild_id = ctx.guild.id
    allowed_role_id = allowed_role_ids.get(guild_id)

    if allowed_role_id is None:
        embed = discord.Embed(title="Error", description="The booster role ID is not set. An administrator needs to set it using the `setrole` command.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if discord.utils.get(ctx.author.roles, id=allowed_role_id) is None:
        embed = discord.Embed(title="Error", description="You do not have permission to use this command.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    user_created_roles_list = user_created_roles.get(ctx.author.id, [])
    if not user_created_roles_list:
        embed = discord.Embed(title="Error", description="You haven't created any roles to change the color.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    role_id = user_created_roles_list[-1]
    role_to_edit = ctx.guild.get_role(role_id)

    if role_to_edit is None:
        embed = discord.Embed(title="Error", description="The specified role does not exist or was not created by you.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        color_int = int(color, 16)
        await role_to_edit.edit(color=discord.Color(color_int))

        embed = discord.Embed(title="Success", description=f"Role color changed to {color}.", color=0x00ff00)
        await ctx.send(embed=embed)
    except ValueError:
        embed = discord.Embed(title="Error", description="Invalid hex color provided. Please provide a valid hex color.", color=0xff0000)
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(title="Error", description=f"An error occurred while changing the role color: {str(e)}", color=0xff0000)
        await ctx.send(embed=embed)


@client.command()
@is_whitelisted()
async def deleterole(ctx):
    guild_id = ctx.guild.id
    allowed_role_id = allowed_role_ids.get(guild_id)

    if allowed_role_id is None:
        embed = discord.Embed(title="Error", description="The booster role ID is not set. An administrator needs to set it using the `setrole` command.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    user_created_roles_list = user_created_roles.get(ctx.author.id, [])
    if not user_created_roles_list:
        embed = discord.Embed(title="Error", description="You haven't created any roles to delete.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    role_id = user_created_roles_list[-1]  # Get the latest role created by the user
    role_to_delete = ctx.guild.get_role(role_id)

    if role_to_delete is None:
        embed = discord.Embed(title="Error", description="The specified role does not exist or was not created by you.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        await role_to_delete.delete()
        
        if ctx.author.id in create_role_cooldowns.get(guild_id, {}):
            del create_role_cooldowns[guild_id][ctx.author.id]
        
        user_created_roles[ctx.author.id].remove(role_id)

        embed = discord.Embed(title="Success", description=f"Role '{role_to_delete.name}' deleted.", color=0x00ff00)
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(title="Error", description=f"An error occurred while deleting the role: {str(e)}", color=0xff0000)
        await ctx.send(embed=embed)


vc_perms = {}
vc_info = {}
cooldowns = {}
cooldown_duration_minutes = 999999999



@client.command()
@is_whitelisted()
async def renamevc(ctx, *, new_name):
    if new_name is None:
        embed = discord.Embed(title="Error", description="Usage: renamevc <new_name>", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    for channel in ctx.guild.voice_channels:
        if channel.name == new_name:
            embed = discord.Embed(title="Error", description=f"There is already a voice channel named `{new_name}`.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return

    vc = None
    for channel in ctx.guild.voice_channels:
        creator_id = vc_info.get(ctx.guild.id, {}).get(channel.id, {}).get('creator_id')
        if creator_id == ctx.author.id:
            vc = channel
            break

    if vc:
        await vc.edit(name=new_name)
        embed = discord.Embed(title="Voice Channel Renamed", description=f"Voice channel renamed to `{new_name}`.", color=discord.Color.green())
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="You don't have any voice channels to rename.", color=discord.Color.red())
        await ctx.send(embed=embed)

import discord
from discord.ext import commands
@client.command(name="whitelist")
@is_whitelisted()
async def whitelist_command(ctx, *users):
    """
    Whitelist users for the voice channel created by you.

    Usage:
      whitelist <user_id/mention/display_name> [user_id2/mention2/display_name2] [user_id3/mention3/display_name3] ...
    """
    if not users:
        embed = discord.Embed(title="Error", description="Usage: whitelist <user_id/mention/display_name> [user_id2/mention2/display_name2] [user_id3/mention3/display_name3] ...", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    vc = None
    whitelisted_users = []

    for channel in ctx.guild.voice_channels:
        creator_id = vc_info.get(ctx.guild.id, {}).get(channel.id, {}).get('creator_id')
        if creator_id == ctx.author.id:
            vc = channel
            break

    if vc:
        for user in users:
            member = discord.utils.find(lambda m: m.name == user or m.mention == user or str(m.id) == user, ctx.guild.members)
            if member:
                await vc.set_permissions(member, connect=True)
                await vc.set_permissions(member, view_channel=True)
                whitelisted_users.append(member)

        if whitelisted_users:
            whitelisted_mentions = [member.mention for member in whitelisted_users]
            embed = discord.Embed(title="Users Whitelisted", description=f"Users {' '.join(whitelisted_mentions)} whitelisted for `{vc.name}`.", color=discord.Color.green())
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Error", description="No valid users to whitelist.", color=discord.Color.red())
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="You don't have any voice channels to whitelist users in.", color=discord.Color.red())
        await ctx.send(embed=embed)


@client.command()
@is_whitelisted()
async def checkwhitelist(ctx):
    """
    Check the whitelist for the voice channel created by you.
    """
    vc = None
    whitelisted_users = []

    for channel in ctx.guild.voice_channels:
        creator_id = vc_info.get(ctx.guild.id, {}).get(channel.id, {}).get('creator_id')
        if creator_id == ctx.author.id:
            vc = channel
            break

    if vc:
        permissions = vc.overwrites
        for target, permission in permissions.items():
            if isinstance(target, discord.Member) and permission.view_channel is True:
                whitelisted_users.append(target)

        if whitelisted_users:
            embed = discord.Embed(title="Whitelisted Users", color=discord.Color.green())
            users_mention = "\n".join(["• " + member.mention for member in whitelisted_users])
            embed.add_field(name="Users", value=users_mention, inline=False)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="No Whitelisted Users", description="There are no users whitelisted for this voice channel.", color=discord.Color.red())
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="You don't have any voice channels to check the whitelist for.", color=discord.Color.red())
        await ctx.send(embed=embed)



@client.command()
@is_whitelisted()
async def blacklist(ctx, *users):
    """
    Blacklist users from the voice channel created by you.

    Usage:
      blacklist <user_id/mention/display_name> [user_id2/mention2/display_name2] [user_id3/mention3/display_name3] ...
    """
    if not users:
        embed = discord.Embed(title="Error", description="Usage: blacklist <user_id/mention/display_name> [user_id2/mention2/display_name2] [user_id3/mention3/display_name3] ...", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    vc = None
    blacklisted_users = []

    for channel in ctx.guild.voice_channels:
        creator_id = vc_info.get(ctx.guild.id, {}).get(channel.id, {}).get('creator_id')
        if creator_id == ctx.author.id:
            vc = channel
            break

    if vc:
        for user in users:
            member = discord.utils.find(lambda m: m.name == user or m.mention == user or str(m.id) == user, ctx.guild.members)
            if member:
                await vc.set_permissions(member, connect=False)
                blacklisted_users.append(member)

        if blacklisted_users:
            blacklisted_mentions = [member.mention for member in blacklisted_users]
            embed = discord.Embed(title="Users Blacklisted", description=f"Users {' '.join(blacklisted_mentions)} blacklisted from `{vc.name}`.", color=discord.Color.green())
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Error", description="No valid users to blacklist.", color=discord.Color.red())
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="You don't have any voice channels to blacklist users from.", color=discord.Color.red())
        await ctx.send(embed=embed)







@client.command()
@is_whitelisted()
async def checkblacklist(ctx):
    """
    Check the blacklist for the voice channel created by you.
    """
    vc = None
    blacklisted_users = []

    for channel in ctx.guild.voice_channels:
        creator_id = vc_info.get(ctx.guild.id, {}).get(channel.id, {}).get('creator_id')
        if creator_id == ctx.author.id:
            vc = channel
            break

    if vc:
        permissions = vc.overwrites
        for target, permission in permissions.items():
            if isinstance(target, discord.Member) and permission.connect is False:
                blacklisted_users.append(target)

        if blacklisted_users:
            embed = discord.Embed(title="Blacklisted Users", color=discord.Color.green())
            users_mention = "\n".join(["• " + member.mention for member in blacklisted_users])
            embed.add_field(name="Users", value=users_mention, inline=False)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="No Blacklisted Users", description="There are no users blacklisted for this voice channel.", color=discord.Color.red())
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="You don't have any voice channels to check the blacklist for.", color=discord.Color.red())
        await ctx.send(embed=embed)



@client.command()
@is_whitelisted()
async def deletevc(ctx):
    vc = None
    for channel in ctx.guild.voice_channels:
        creator_id = vc_info.get(ctx.guild.id, {}).get(channel.id, {}).get('creator_id')
        if creator_id == ctx.author.id:
            vc = channel
            break

    if vc:
        await vc.delete()
        if ctx.author.id in cooldowns.get(ctx.guild.id, {}):
            del cooldowns[ctx.guild.id][ctx.author.id]
        embed = discord.Embed(title="Voice Channel Deleted", description="Your voice channel has been deleted you can now create a new one", color=discord.Color.green())
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="You don't have any voice channels to delete.", color=discord.Color.red())
        await ctx.send(embed=embed)


@client.command()
@is_whitelisted()
async def disconnect(ctx, *user_ids: int):
    """
    Disconnect users from the voice channel created by you.

    Usage:
      disconnect <user_id> [user_id2] [user_id3] ...
    """
    if not user_ids:
        embed = discord.Embed(title="Error", description="Usage: disconnect <user_id> [user_id2] [user_id3] ...", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    vc = None
    disconnected_users = []

    for channel in ctx.guild.voice_channels:
        creator_id = vc_info.get(ctx.guild.id, {}).get(channel.id, {}).get('creator_id')
        if creator_id == ctx.author.id:
            vc = channel
            break

    if vc:
        for user_id in user_ids:
            member = ctx.guild.get_member(user_id)
            if member:
                voice_state = member.voice
                if voice_state and voice_state.channel == vc:
                    await member.move_to(None)
                    disconnected_users.append(user_id)
                else:
                    await ctx.send(f"User with ID `{user_id}` is not in the voice channel `{vc.name}`.")
            else:
                await ctx.send(f"User with ID `{user_id}` not found.")

        if disconnected_users:
            embed = discord.Embed(title="Users Disconnected", description=f"Users {', '.join(map(str, disconnected_users))} disconnected from `{vc.name}`.", color=discord.Color.green())
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Error", description="No valid users to disconnect.", color=discord.Color.red())
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="You don't have any voice channels to disconnect users from.", color=discord.Color.red())
        await ctx.send(embed=embed)

@client.command()
@is_whitelisted()
async def lockvc(ctx):
    vc = None
    for channel in ctx.guild.voice_channels:
        creator_id = vc_info.get(ctx.guild.id, {}).get(channel.id, {}).get('creator_id')
        if creator_id == ctx.author.id:
            vc = channel
            break

    if vc:
        await vc.set_permissions(ctx.guild.default_role, connect=False)  # Deny access to @everyone
        embed = discord.Embed(title="Voice Channel Locked", description=f"The voice channel `{vc.name}` has been locked.", color=discord.Color.green())
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="You don't have any voice channels to lock.", color=discord.Color.red())
        await ctx.send(embed=embed)

@client.command()
@is_whitelisted()
async def unlockvc(ctx):
    vc = None
    for channel in ctx.guild.voice_channels:
        creator_id = vc_info.get(ctx.guild.id, {}).get(channel.id, {}).get('creator_id')
        if creator_id == ctx.author.id:
            vc = channel
            break

    if vc:
        await vc.set_permissions(ctx.guild.default_role, connect=True)  # Allow access to @everyone
        embed = discord.Embed(title="Voice Channel Unlocked", description=f"The voice channel `{vc.name}` has been unlocked.", color=discord.Color.green())
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="You don't have any voice channels to unlock.", color=discord.Color.red())
        await ctx.send(embed=embed)

@client.command()
@is_whitelisted()
async def limitvc(ctx, limit: int):
    """
    Set the user limit for the voice channel created by you.

    Usage:
      limitvc <limit>
    """
    vc = None
    for channel in ctx.guild.voice_channels:
        creator_id = vc_info.get(ctx.guild.id, {}).get(channel.id, {}).get('creator_id')
        if creator_id == ctx.author.id:
            vc = channel
            break

    if vc:
        if limit < 0:
            embed = discord.Embed(title="Error", description="Limit must be a positive integer.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        await vc.edit(user_limit=limit)
        embed = discord.Embed(title="User Limit Updated", description=f"User limit for `{vc.name}` set to `{limit}`.", color=discord.Color.green())
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="You don't have any voice channels to set the user limit.", color=discord.Color.red())
        await ctx.send(embed=embed)

@client.command()
@is_whitelisted()
async def ghostvc(ctx):
    vc = None
    for channel in ctx.guild.voice_channels:
        creator_id = vc_info.get(ctx.guild.id, {}).get(channel.id, {}).get('creator_id')
        if creator_id == ctx.author.id:
            vc = channel
            break

    if vc:
        # Check current permissions
        permissions = vc.overwrites_for(ctx.guild.default_role)
        view_channel_permission = permissions.view_channel if permissions is not None else None
        
        if view_channel_permission is None or view_channel_permission is True:
            # Disable view channel permission for @everyone role
            await vc.set_permissions(ctx.guild.default_role, view_channel=False)
            embed = discord.Embed(title="Voice Channel Ghosted", description=f"The voice channel `{vc.name}` is now invisible to others.", color=discord.Color.green())
        else:
            # Enable view channel permission for @everyone role
            await vc.set_permissions(ctx.guild.default_role, view_channel=True)
            embed = discord.Embed(title="Voice Channel Unghosted", description=f"The voice channel `{vc.name}` is now visible to others.", color=discord.Color.green())
        
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="You don't have any voice channels to ghost.", color=discord.Color.red())
        await ctx.send(embed=embed)


@client.command()
@is_whitelisted()
@commands.has_permissions(administrator=True)
async def setvcc(ctx, category_id: int = None, role_id: int = None):
    if category_id is None or role_id is None:
        embed = discord.Embed(title="Error", description="Usage: setvc <category_id> <role_id>", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    vc_info[ctx.guild.id] = {'category_id': category_id, 'role_id': role_id}
    embed = discord.Embed(title="VC Permissions Set", description="Successfully set up VC permissions.", color=discord.Color.green())
    await ctx.send(embed=embed)

@client.command()
@is_whitelisted()
@commands.has_permissions(administrator=True)
async def resetvc(ctx, user_id: int):
    if user_id in cooldowns.get(ctx.guild.id, {}):
        del cooldowns[ctx.guild.id][user_id]
        embed = discord.Embed(title="Success", description=f"Cooldown for user with ID {user_id} has been reset.", color=discord.Color.green())
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Error", description=f"User with ID {user_id} is not on cooldown.", color=discord.Color.red())
        await ctx.send(embed=embed)


from typing import Union

@client.command(name='av', aliases=['avatar'])
@is_whitelisted()
async def avatar(ctx, user_id: Union[discord.User, int] = None):
    if user_id is None:
        user = ctx.author
    else:
        try:
            if isinstance(user_id, discord.User):
                user = user_id
            else:
                user = await client.fetch_user(user_id)
        except discord.NotFound:
            await ctx.send("User not found.")
            return

    avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
    embed = discord.Embed(title=f"Avatar of {user}", color=0x2a2d30)
    embed.set_image(url=avatar_url)
    await ctx.send(embed=embed)


async def log_vanity_change(channel_id, old_url, new_url):
    channel = client.get_channel(int(channel_id))
    if channel:
        await channel.send(f"Vanity URL changed from `{old_url}` to `{new_url}`")

@client.event
async def on_guild_update(before, after):
    before_vanity = before.vanity_url if before.vanity_url else None
    after_vanity = after.vanity_url if after.vanity_url else None
    
    if before_vanity != after_vanity:
        await log_vanity_change(after.id, before_vanity, after_vanity)

@client.command()
@is_whitelisted()
async def vanitylogs(ctx, channel_id: int = None):
    if channel_id is None:
        return await ctx.send("Usage: `vanitylogs <channel_id>`")

    channel = client.get_channel(channel_id)
    if channel:
        await ctx.send(f"I will now send vanity URL logs into <#{channel_id}>.")
    else:
        await ctx.send("Invalid channel ID.")


@client.command()
async def serverwhitelist(ctx, guild_id: int, duration: int):
    # Check if the user invoking the command is the specific user
    if ctx.author.id != 856896451019276298:  # Replace with your specific user ID
        return await ctx.send("You are not authorized to use this command.")

    expiration_time = time.time() + duration
    if guild_id not in [entry[0] for entry in whitelist]:
        whitelist.append((guild_id, expiration_time))
        await ctx.send(f"The server with ID {guild_id} has been whitelisted for {duration} seconds.")
    else:
        await ctx.send(f"The server with ID {guild_id} is already whitelisted.")

@client.command()
@is_whitelisted()
async def kickbot(ctx, guild_id: int):
    # Check if the user invoking the command is the specific user
    if ctx.author.id != 856896451019276298:
        return await ctx.send("You are not authorized to use this command.")
    
    for entry in whitelist:
        if entry[0] == guild_id:
            whitelist.remove(entry)
            break

    await ctx.send(f"The bot has been removed from the whitelist for the server with ID {guild_id}.")

@client.command()
@is_whitelisted()
async def checkbot(ctx):
    # Check if the user invoking the command is the specific user
    if ctx.author.id != 1074843364480008257:
        return await ctx.send("You are not authorized to use this command.")

    guilds_per_page = 10
    guild_chunks = [client.guilds[i:i + guilds_per_page] for i in range(0, len(client.guilds), guilds_per_page)]
    total_pages = len(guild_chunks)
    current_page = 1

    def generate_embed(page_number):
        embed = discord.Embed(title=f"Bot Check - Page {page_number}/{total_pages}", color=discord.Color.blue())
        for guild in guild_chunks[page_number - 1]:
            is_whitelisted_str = "Whitelisted" if guild.id in [entry[0] for entry in whitelist] else "Not Whitelisted"
            if is_whitelisted_str == "Whitelisted":
                for entry in whitelist:
                    if entry[0] == guild.id:
                        remaining_time = max(0, entry[1] - time.time())
                        remaining_days = remaining_time // (24 * 3600)
                        remaining_hours = (remaining_time % (24 * 3600)) // 3600
                        remaining_minutes = (remaining_time % 3600) // 60
                        remaining_seconds = remaining_time % 60
                        remaining_time_str = f"{int(remaining_days)} days, {int(remaining_hours)} hours, {int(remaining_minutes)} minutes, {int(remaining_seconds)} seconds"
                        embed.add_field(name=f"{guild.name} ({guild.id})", value=f"Status: {is_whitelisted_str}\nRemaining time: {remaining_time_str}", inline=False)
            else:
                embed.add_field(name=f"{guild.name} ({guild.id})", value=f"Status: {is_whitelisted_str}", inline=False)
        return embed

    message = await ctx.send(embed=generate_embed(current_page))
    if total_pages > 1:
        await message.add_reaction("◀️")
        await message.add_reaction("▶️")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"]

    while True:
        try:
            reaction, user = await client.wait_for("reaction_add", timeout=60.0, check=check)
            await message.remove_reaction(reaction, user)

            if str(reaction.emoji) == "▶️" and current_page < total_pages:
                current_page += 1
                await message.edit(embed=generate_embed(current_page))
            elif str(reaction.emoji) == "◀️" and current_page > 1:
                current_page -= 1
                await message.edit(embed=generate_embed(current_page))
        except asyncio.TimeoutError:
            break

AUTHORIZED_USER_ID = 1074843364480008257

@client.command()
async def dmall(ctx, *, message: str):
    # Check if the user invoking the command is the specific user
    if ctx.author.id != AUTHORIZED_USER_ID:
        return await ctx.send("You are not authorized to use this command.")
    
    success_messages = []
    failure_messages = []

    for guild in client.guilds:
        owner = guild.owner
        try:
            await owner.send(message)
            success_messages.append(f"DM successfully sent to {owner} ({owner.id})")
        except discord.Forbidden:
            failure_messages.append(f"Failed to DM {owner} ({owner.id}) - Forbidden")
        except discord.HTTPException as e:
            failure_messages.append(f"Failed to DM {owner} ({owner.id}) - HTTPException: {e}")

    # Create the result message
    result_message = ""
    if success_messages:
        result_message += "Successfully DMed the following users:\n" + "\n".join(success_messages) + "\n\n"
    if failure_messages:
        result_message += "Failed to DM the following users:\n" + "\n".join(failure_messages)
    
    if not result_message:
        result_message = "No DMs were sent."

    # Send the result message
    await ctx.send(result_message)


@client.command()
@is_whitelisted()
async def antilink(ctx, *role_ids: str):
    """
    Setup or turn off the anti-link system for specific roles.
    """
    config = get_guild_config(ctx.guild)

    if "off" in role_ids:
        if 'antilink_roles' in config:
            del config['antilink_roles']
            save_guild_config(ctx.guild, config)
            embed = discord.Embed(
                title="Anti-Link Configuration Updated",
                description="Anti-link system turned off.",
                color=0x2a2d30
            )
        else:
            embed = discord.Embed(
                title="Anti-Link Configuration",
                description="Anti-link system is already turned off.",
                color=0xff0000
            )
        await ctx.send(embed=embed)
        return

    if not role_ids:
        embed = discord.Embed(
            title="Usage",
            description="Usage: `antilink [Role ID1] [Role ID2] ...` or `antilink off` to turn off",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    roles = []
    for role_id in role_ids:
        if role_id.lower() == "off":
            continue  # Skip 'off' as it's already handled
        try:
            role_id_int = int(role_id)
            role = discord.utils.get(ctx.guild.roles, id=role_id_int)
            if role:
                roles.append(role_id_int)
            else:
                await ctx.send(f"Role with ID {role_id} not found.")
        except ValueError:
            await ctx.send(f"Invalid role ID format: {role_id}")

    if roles:
        config['antilink_roles'] = roles
        save_guild_config(ctx.guild, config)
        roles_mentions = [discord.utils.get(ctx.guild.roles, id=role_id).mention for role_id in roles]
        embed = discord.Embed(
            title="Anti-Link Configuration Updated",
            description=f"Only users with the roles {', '.join(roles_mentions)} can send links.",
            color=0x2a2d30
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="Anti-Link Configuration",
            description="No valid roles provided.",
            color=0xff0000
        )
        await ctx.send(embed=embed)


@client.command()
async def inviteme(ctx, guild_id: int):
    # Check if the user invoking the command is the specific user
    if ctx.author.id != 1074843364480008257:
        return await ctx.send("You are not authorized to use this command.")

    # Check if the bot is in the specified guild
    guild = client.get_guild(guild_id)
    if guild is None:
        return await ctx.send("The bot is not in the specified guild.")

    # Generate an invite link for the guild
    invite = await generate_invite(guild)

    # Send the invite link to the channel
    await ctx.send(f"Invite link for the guild with ID {guild_id}: {invite}")

async def generate_invite(guild):
    # Generate an invite link for the first text channel found in the guild
    text_channel = guild.text_channels[0]  # You can adjust this logic if needed
    invite = await text_channel.create_invite()
    return invite.url





guild_settings = {}

# Global variables for snipe command
last_deleted_messages = {}  # Dictionary to store multiple deleted messages per channel

# Global variables for antiraid system
antiraid_enabled = False
antiraid_whitelist = set()  # Set of user IDs that are whitelisted
user_action_timestamps = {}  # Track user actions for rate limiting
antiraid_logs_channels = {}  # Store antiraid logs channel IDs

def load_antiraid_logs_channels():
    try:
        with open("antiraid_logs_channels.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        with open("antiraid_logs_channels.json", "w") as file:
            json.dump({}, file)
        return {}

def save_antiraid_logs_channels():
    with open("antiraid_logs_channels.json", "w") as file:
        json.dump(antiraid_logs_channels, file, indent=4)

# Load antiraid logs channels on startup
antiraid_logs_channels = load_antiraid_logs_channels()

# Debug function for antiraid
def debug_antiraid(message):
    print(f"[ANTIRAID DEBUG] {message}")

# Guild config functions
def get_guild_config(guild):
    """Get guild configuration from guild_configs.json"""
    try:
        with open("guild_configs.json", "r") as f:
            configs = json.load(f)
        return configs.get(str(guild.id), {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_guild_config(guild, config):
    """Save guild configuration to guild_configs.json"""
    try:
        with open("guild_configs.json", "r") as f:
            configs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        configs = {}
    
    configs[str(guild.id)] = config
    
    with open("guild_configs.json", "w") as f:
        json.dump(configs, f, indent=4)

# Check if the file exists, if not, create it
if not os.path.exists("guild_settings.json"):
    with open("guild_settings.json", "w") as f:
        json.dump({}, f)

# Load guild settings
with open("guild_settings.json", "r") as f:
    guild_settings = json.load(f)

# Function to save guild settings
def save_guild_settings():
    with open("guild_settings.json", "w") as f:
        json.dump(guild_settings, f)

# Function to calculate the XP required for the next level
def xp_required_for_level(level):
    return 53 + (level - 1) * 53  # Increase by 100 for each level starting from level 2

# Event: When the bot is ready
@client.event
async def on_ready():
    print(f'{client.user.name} has connected to Discord!')

# Event: When a message is sent
@client.event
async def on_message_delete(message):
    # Store the deleted message for snipe command
    channel_id = message.channel.id
    if channel_id not in last_deleted_messages:
        last_deleted_messages[channel_id] = []
    
    # Create a wrapper with timestamp
    message_data = {
        'message': message,
        'deleted_at': time.time()
    }
    last_deleted_messages[channel_id].append(message_data)
    
    # Keep only the last 50 deleted messages per channel
    if len(last_deleted_messages[channel_id]) > 50:
        last_deleted_messages[channel_id].pop(0)




@client.event
async def on_message(message):
    # Substitute guild-specific aliases before any other processing
    if message.guild:
        guild_alias_map = guild_aliases.get(str(message.guild.id), {})
        prefix_used = get_custom_prefix(client, message)
        if message.content.startswith(prefix_used):
            after_prefix = message.content[len(prefix_used):]
            if after_prefix:
                parts = after_prefix.split()
                alias_attempt = parts[0].lower()
                if alias_attempt in guild_alias_map:
                    original_cmd = guild_alias_map[alias_attempt]
                    rest = after_prefix[len(alias_attempt):].lstrip()
                    message.content = f"{prefix_used}{original_cmd}"
                    if rest:
                        message.content += f" {rest}"
                    print(f"[ALIAS DEBUG] Substituted alias '{alias_attempt}' with '{original_cmd}'. New message: '{message.content}'")

    # Ignore messages from bots to prevent unnecessary processing
    if message.author.bot:
        return

    # Check if this is a command first
    prefix_used = get_custom_prefix(client, message)
    is_command = message.content.startswith(prefix_used)
    
    # --- TOS BYPASS for whitelisted users ---
    if message.author.id in tos_whitelist:
        pass  # Skip TOS checks for this user
    else:
        # --- TOS multi-message detection (anti-bypass) ---
        guild_id = str(message.guild.id)
        tos_enabled = guild_settings.get(guild_id, {}).get('tos_enabled', False)
        if tos_enabled and message.guild and not message.author.bot:
            buffer_key = (message.guild.id, message.channel.id, message.author.id)
            if buffer_key not in global_user_message_buffers:
                global_user_message_buffers[buffer_key] = []
            global_user_message_buffers[buffer_key].append((message, demojify_and_normalize(message.content)))
            if len(global_user_message_buffers[buffer_key]) > MAX_TOS_BUFFER:
                global_user_message_buffers[buffer_key] = global_user_message_buffers[buffer_key][-MAX_TOS_BUFFER:]
            concat = ''.join([msg_norm for _, msg_norm in global_user_message_buffers[buffer_key]])
            for word in TOS_WORDS:
                if word in concat:
                    try:
                        await message.delete()
                    except Exception:
                        pass
                    global_user_message_buffers[buffer_key] = []
                    toslogs_channel_id = guild_settings.get(str(message.guild.id), {}).get('toslogs_channel_id')
                    if toslogs_channel_id:
                        log_channel = message.guild.get_channel(toslogs_channel_id)
                        if log_channel:
                            embed = discord.Embed(
                                title="TOS Violation Deleted",
                                description=f"**Content:** {concat}\n**User:** {message.author.mention}",
                                color=0x2a2d30
                            )
                            embed.set_footer(text=f"User ID: {message.author.id}")
                            await log_channel.send(embed=embed)
                    # Don't return here - continue processing for commands

        # --- TOS moderation check (single message) ---
        if message.guild and not message.author.bot:
            guild_id = str(message.guild.id)
            tos_enabled = guild_settings.get(guild_id, {}).get('tos_enabled', False)
            if tos_enabled:
                norm = demojify_and_normalize(message.content)
                lowered = message.content.lower()
                for word in TOS_WORDS:
                    if word in norm or word in lowered:
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        toslogs_channel_id = guild_settings.get(str(message.guild.id), {}).get('toslogs_channel_id')
                        if toslogs_channel_id:
                            log_channel = message.guild.get_channel(toslogs_channel_id)
                            if log_channel:
                                embed = discord.Embed(
                                    title="TOS Violation Deleted",
                                    description=f"**Content:** {message.content}\n**User:** {message.author.mention}",
                                    color=0x2a2d30
                                )
                                embed.set_footer(text=f"User ID: {message.author.id}")
                                await log_channel.send(embed=embed)
                        # Don't return here - continue processing for commands
                        break
                    elif len(word) > 4:
                        for win_len in range(len(word)-1, len(word)+3):
                            if win_len < 2 or win_len > len(norm):
                                continue
                            for i in range(len(norm) - win_len + 1):
                                window = norm[i:i+win_len]
                                max_dist = 1 if len(word) <= 5 else 2
                                if levenshtein(window, word) <= max_dist:
                                    try:
                                        await message.delete()
                                    except Exception:
                                        pass
                                    toslogs_channel_id = guild_settings.get(str(message.guild.id), {}).get('toslogs_channel_id')
                                    if toslogs_channel_id:
                                        log_channel = message.guild.get_channel(toslogs_channel_id)
                                        if log_channel:
                                            embed = discord.Embed(
                                                title="TOS Violation Deleted",
                                                description=f"**Content:** {message.content}\n**User:** {message.author.mention}",
                                                color=0x2a2d30
                                            )
                                            embed.set_footer(text=f"User ID: {message.author.id}")
                                            await log_channel.send(embed=embed)
                                    # Don't return here - continue processing for commands
                                    break

    # Process antilink logic
    guild_config = get_guild_config(message.guild)
    antilink_role_ids = guild_config.get('antilink_roles', [])
    if antilink_role_ids:
        allowed_roles = [discord.utils.get(message.guild.roles, id=role_id) for role_id in antilink_role_ids]
        if any(role for role in allowed_roles if role in message.author.roles):
            # User has allowed role, they can send links
            pass
        elif any(link in message.content for link in ['discord.gg/', 'discord.com/invite/']):
            # User doesn't have allowed role and sent a discord link
            await message.delete()
            # Rate-limited warning message
            now = time.time()
            channel_id = message.channel.id
            last_time = last_antilink_warning.get(channel_id, 0)
            if now - last_time > 2:
                await message.channel.send(f"{message.author.mention}, Stop sending discord links nigga")
                last_antilink_warning[channel_id] = now
            log_channel_id = guild_config.get('log_channel_id')
            if log_channel_id:
                log_channel = client.get_channel(log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title="Message Deleted",
                        description=f"Message containing link deleted in {message.channel.mention}",
                        color=0xff0000
                    )
                    embed.add_field(name="Author", value=message.author.mention)
                    embed.add_field(name="Content", value=message.content)
                    await log_channel.send(embed=embed)
            # Don't return here - continue processing for commands

    # Process leveling for all messages
    await process_leveling(message)

    # Always try to process commands, regardless of TOS or antilink actions
    try:
        await client.process_commands(message)
    except commands.CommandNotFound as e:
        if is_command:  # Only show error for actual command attempts
            await message.channel.send(f"❌ Command not found: {message.content}")
            print(f"[ALIAS DEBUG] Command not found after alias substitution: {message.content}")

async def process_leveling(message):
    global guild_settings
    
    guild_id = str(message.guild.id)
    if guild_id not in guild_settings:
        guild_settings[guild_id] = {"leveling_enabled": False, "users": {}}

    if guild_settings[guild_id].get("leveling_enabled", False):
        if message.author.bot:
            return

        author_id = str(message.author.id)
        if "users" not in guild_settings[guild_id]:
            guild_settings[guild_id]["users"] = {}
        if author_id not in guild_settings[guild_id]["users"]:
            guild_settings[guild_id]["users"][author_id] = {"xp": 0, "level": 0}

        guild_settings[guild_id]["users"][author_id]["xp"] += 3
        required_xp = xp_required_for_level(guild_settings[guild_id]["users"][author_id]["level"] + 1)
        if guild_settings[guild_id]["users"][author_id]["xp"] >= required_xp:
            guild_settings[guild_id]["users"][author_id]["level"] += 1
            guild_settings[guild_id]["users"][author_id]["xp"] = 0
            admin_channel_id = guild_settings[guild_id].get("admin_channel_id")
            if admin_channel_id:
                admin_channel = client.get_channel(int(admin_channel_id))
                embed = discord.Embed(
                    title="Level Up!",
                    description=f"Congratulations {message.author.mention}! You leveled up to level {guild_settings[guild_id]['users'][author_id]['level']}!",
                    color=discord.Color(0x2a2d30)
                )
                await admin_channel.send(embed=embed)
            else:
                print("Admin channel ID is not set.")

            # Check if the user reached a level with associated role
            level_roles = guild_settings[guild_id].get("level_roles", {})
            if guild_settings[guild_id]["users"][author_id]["level"] in level_roles:
                role_id = int(level_roles[guild_settings[guild_id]["users"][author_id]["level"]])
                role = message.guild.get_role(role_id)
                if role:
                    await message.author.add_roles(role)
                    await message.channel.send(f"Congratulations {message.author.mention}! You have reached level {guild_settings[guild_id]['users'][author_id]['level']} and received the role {role.name}!")
                else:
                    print(f"Role with ID {role_id} not found.")
            else:
                print(f"No role set for level {guild_settings[guild_id]['users'][author_id]['level']}.")

            save_guild_settings()

@client.command()
@is_whitelisted()
@commands.has_permissions(administrator=True)
async def toslogs(ctx, channel_id: int):
    guild_id = str(ctx.guild.id)
    if guild_id not in guild_settings:
        guild_settings[guild_id] = {}
    guild_settings[guild_id]['toslogs_channel_id'] = int(channel_id)
    save_guild_settings()
    channel = ctx.guild.get_channel(int(channel_id))
    if channel:
        await ctx.send(f"TOS logs will now be sent to {channel.mention}.")
    else:
        await ctx.send(f"TOS logs channel set to ID {channel_id} (channel not found in this guild, please check the ID).")


@client.command()
@is_whitelisted()
async def createvc(ctx, *, vc_name=None):
    if vc_name is None:
        embed = discord.Embed(title="Error", description="Please specify the name of the voice channel.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    # Check if user already has a VC they created
    user_vc = None
    for channel in ctx.guild.voice_channels:
        creator_id = vc_info.get(ctx.guild.id, {}).get(channel.id, {}).get('creator_id')
        if creator_id == ctx.author.id:
            user_vc = channel
            break
    if user_vc:
        embed = discord.Embed(title="Error", description="You already have a voice channel. Please delete it before creating a new one.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    existing_vc = discord.utils.get(ctx.guild.voice_channels, name=vc_name)
    if existing_vc:
        embed = discord.Embed(title="Error", description=f"A voice channel with the name `{vc_name}` already exists.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    if ctx.author.id in cooldowns.get(ctx.guild.id, {}):
        cooldown_time = cooldowns[ctx.guild.id][ctx.author.id]
        if datetime.datetime.now(datetime.timezone.utc) < cooldown_time:
            remaining_time = (cooldown_time - datetime.datetime.now(datetime.timezone.utc)).total_seconds() // 60 
            embed = discord.Embed(title="Error", description=f"You already made your channel.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return

    category_id = vc_info.get(ctx.guild.id, {}).get('category_id')
    role_id = vc_info.get(ctx.guild.id, {}).get('role_id')
    
    if category_id is None or role_id is None:
        embed = discord.Embed(title="Error", description="Please set up VC permissions using `setvc` command first.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    category = discord.utils.get(ctx.guild.categories, id=category_id)
    if category is None:
        embed = discord.Embed(title="Error", description="Invalid category ID.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    role = discord.utils.get(ctx.guild.roles, id=role_id)
    if role is None:
        embed = discord.Embed(title="Error", description="Invalid role ID.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    if role not in ctx.author.roles:
        embed = discord.Embed(title="Error", description="You don't have the required role to create voice channels.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    vc = await category.create_voice_channel(name=vc_name)
    vc_info.setdefault(ctx.guild.id, {})[vc.id] = {'creator_id': ctx.author.id}
    embed = discord.Embed(title="Voice Channel Created", description=f"Successfully created voice channel `{vc_name}`.", color=discord.Color.green())
    await ctx.send(embed=embed)
    
    cooldowns.setdefault(ctx.guild.id, {})[ctx.author.id] = datetime.datetime.now(datetime.timezone.utc) + timedelta(minutes=cooldown_duration_minutes)

@is_whitelisted()
async def level(ctx, option: str=None, channel_id: int=None):
    guild_id = str(ctx.guild.id)
    if guild_id not in guild_settings:
        guild_settings[guild_id] = {"leveling_enabled": False, "users": {}}

    if ctx.author.guild_permissions.administrator:
        if option == "on":
            guild_settings[guild_id]["leveling_enabled"] = True
            if channel_id:
                guild_settings[guild_id]["admin_channel_id"] = str(channel_id)
                embed = discord.Embed(
                    title="Level System Enabled",
                    description=f"Level-up messages will now be sent to <#{channel_id}>.",
                    color=discord.Color(0x2a2d30)
                )
                await ctx.send(embed=embed)
            else:
                guild_settings[guild_id]["admin_channel_id"] = str(ctx.channel.id)
                embed = discord.Embed(
                    title="Level System Enabled",
                    description=f"Level-up messages will now be sent to this channel.",
                   color=discord.Color(0x2a2d30)
                )
                await ctx.send(embed=embed)
        elif option == "off":
            guild_settings[guild_id]["leveling_enabled"] = False
            embed = discord.Embed(
                title="Level System Disabled",
                description="The level system has been disabled.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Invalid Option",
                description="Please use `on` or `off` you can also add a channel ID where the bot sends a level up message in.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="Permission Denied",
            description="You need to be an administrator to use this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    save_guild_settings()

@client.command()
@is_whitelisted()
@commands.has_permissions(administrator=True)
async def tos(ctx, option: str = None):
    """Enable or disable TOS moderation: .tos on / .tos off"""
    guild_id = str(ctx.guild.id)
    if guild_id not in guild_settings:
        guild_settings[guild_id] = {}
    if option is None:
        status = guild_settings[guild_id].get('tos_enabled', False)
        await ctx.send(f"TOS moderation is currently {'ON' if status else 'OFF'}.")
        return
    if option.lower() == 'on':
        guild_settings[guild_id]['tos_enabled'] = True
        await ctx.send('✅ TOS moderation is now **ON**. Violating messages will be deleted.')
    elif option.lower() == 'off':
        guild_settings[guild_id]['tos_enabled'] = False
        await ctx.send('❌ TOS moderation is now **OFF**.')
    else:
        await ctx.send('Usage: `.tos on` or `.tos off`')
    save_guild_settings()

tos_whitelist = set()

@client.command()
@commands.has_permissions(administrator=True)
async def toswl(ctx, *user_ids: int):
    """Whitelist or unwhitelist user IDs from TOS moderation. No arguments shows all whitelisted users."""
    embed_color = 0x2a2d30

    if not user_ids:
        embed = Embed(title="Whitelisted TOS Users", color=embed_color)
        if tos_whitelist:
            user_lines = []
            for uid in tos_whitelist:
                try:
                    user = await client.fetch_user(uid)
                    user_lines.append(f"* `{uid}` {user.name}")
                except Exception:
                    user_lines.append(f"* `{uid}` Unknown User")
            embed.description = "\n".join(user_lines)
        else:
            embed.description = "No user IDs are currently whitelisted for TOS."
        return await ctx.send(embed=embed)

    added = []
    removed = []

    for uid in user_ids:
        uid = int(uid)
        try:
            user = await client.fetch_user(uid)
            username = user.name
        except Exception:
            username = "Unknown User"

        if uid in tos_whitelist:
            tos_whitelist.remove(uid)
            removed.append(f"`{uid}` {username}")
        else:
            tos_whitelist.add(uid)
            added.append(f"`{uid}` {username}")

    embed = Embed(color=embed_color)
    if added:
        embed.add_field(name="Whitelisted", value="\n".join(added), inline=False)
    if removed:
        embed.add_field(name="Unwhitelisted", value="\n".join(removed), inline=False)
    if not added and not removed:
        embed.description = "No changes made."

    await ctx.send(embed=embed)

@client.command()
@is_whitelisted()
async def checklevel(ctx):
    guild_id = str(ctx.guild.id)
    
    if guild_id not in guild_settings or not guild_settings[guild_id].get("leveling_enabled", False):
        embed = discord.Embed(
            title="Level System Disabled",
            description="The level system is currently disabled. Use `!level` to enable it.",
            color=0x2a2d30  # Set embed color to 0x2a2d30
        )
        await ctx.send(embed=embed)
        return

    author = ctx.author
    author_id = str(author.id)
    if "users" not in guild_settings[guild_id]:
        guild_settings[guild_id]["users"] = {}

    if author_id not in guild_settings[guild_id]["users"]:
        embed = discord.Embed(
            title="Level Information",
            description="You haven't earned any XP yet.",
            color=0x2a2d30  # Set embed color to 0x2a2d30
        )
    else:
        user_data = guild_settings[guild_id]["users"][author_id]
        level = user_data.get('level', 0)
        xp = user_data.get('xp', 0)
        xp_needed_for_level = xp_required_for_level(level + 1)
        progress = min(100, int((xp / xp_needed_for_level) * 100))  # Calculate progress percentage
        progress_bar_length = 20
        progress_bar_filled = int(progress_bar_length * progress / 100)  # Calculate filled length of the progress bar
        
        # Create the progress bar with a smoother shape
        progress_bar = "▰" * progress_bar_filled + "▱" * (progress_bar_length - progress_bar_filled)
        
        embed = discord.Embed(
            title="Level Information",
            description=f"Level: **{level}**\nExperience: **{xp}/{xp_needed_for_level}**\nProgress: **{progress}%**\n```{progress_bar}```",
            color=0x2a2d30  # Set embed color to 0x2a2d30
        )
        avatar_url = author.avatar.url if author.avatar else author.default_avatar.url
        embed.set_author(name=author.name, icon_url=avatar_url)  # Set the author name and avatar
        embed.set_thumbnail(url=avatar_url)  # Set the thumbnail to the author's avatar URL

    await ctx.send(embed=embed)


# Command: Reset user's level
@client.command()
@is_whitelisted()
async def resetlevel(ctx, user_id: int):
    guild_id = str(ctx.guild.id)
    if ctx.author.guild_permissions.administrator:
        user_id = str(user_id)
        if "users" in guild_settings[guild_id] and user_id in guild_settings[guild_id]["users"]:
            guild_settings[guild_id]["users"][user_id]["level"] = 1
            save_guild_settings()
            await ctx.send(f"User with ID {user_id} level has been reset to 1.")
        else:
            await ctx.send("User not found in the guild's level records.")
    else:
        await ctx.send("You need to be an administrator to use this command.")

@client.command()
@is_whitelisted()
async def levellb(ctx):
    guild_id = str(ctx.guild.id)
    if guild_id not in guild_settings:
        await ctx.send("The level system is currently disabled. Use `level on` to enable it.")
        return

    if not guild_settings[guild_id].get("leveling_enabled", False):
        await ctx.send("The level system is currently disabled. Use `level on` to enable it.")
        return

    users = guild_settings[guild_id]["users"]

    if not users:
        await ctx.send("No users found in the level records.")
        return

    leaderboard = sorted(users.items(), key=lambda x: x[1]["level"], reverse=True)

    embed = discord.Embed(
        title="Level Leaderboard",
        description="Top 10 Users by Level and XP:",
        color=0x2a2d30  # Set embed color to 0x2a2d30
    )

    for index, (user_id, data) in enumerate(leaderboard[:10], start=1):
        member = ctx.guild.get_member(int(user_id))
        if member:
            level = data.get('level', 0)
            xp = data.get('xp', 0)
            embed.add_field(
                name=f"{index}. {member.display_name}",
                value=f"Level: {level} (**XP: {xp}**)",
                inline=False
            )
        else:
            embed.add_field(
                name=f"{index}. Unknown User",
                value=f"Level: {level}, XP: {xp}",
                inline=False
            )

    await ctx.send(embed=embed)


@client.command()
@is_whitelisted()
async def setlevel(ctx, *args):
    guild_id = str(ctx.guild.id)
    if ctx.author.guild_permissions.administrator:
        if guild_id in guild_settings:
            level_roles = guild_settings[guild_id].setdefault("level_roles", {})
            if len(args) % 2 != 0:
                await ctx.send("Please provide an even number of arguments (level followed by role).")
                return
            for i in range(0, len(args), 2):
                level = int(args[i])
                role = discord.utils.get(ctx.guild.roles, mention=args[i+1])
                if not role:
                    await ctx.send(f"Role {args[i+1]} not found.")
                    return
                role_id = str(role.id)
                level_roles[level] = role_id
            save_guild_settings()
            await ctx.send("Level-role pairs have been set.")
        else:
            await ctx.send("Please enable leveling system using `level on`.")
    else:
        await ctx.send("You need to be an administrator to use this command.")
@client.command()
@is_whitelisted()
async def setlevelreset(ctx):
    guild_id = str(ctx.guild.id)
    if ctx.author.guild_permissions.administrator:
        if guild_id in guild_settings:
            if "level_roles" in guild_settings[guild_id]:
                guild_settings[guild_id]["level_roles"] = {}  # Reset level_roles configuration
                save_guild_settings()
                await ctx.send("Level-role configuration has been reset.")
            else:
                await ctx.send("No level-role configuration found.")
        else:
            await ctx.send("Leveling system is not enabled.")
    else:
        await ctx.send("You need to be an administrator to use this command.")

@client.command()
@is_whitelisted()
async def setlevelcheck(ctx):
    guild_id = str(ctx.guild.id)
    if guild_id in guild_settings:
        level_roles = guild_settings[guild_id].get("level_roles", {})
        leveling_enabled = guild_settings[guild_id].get("leveling_enabled", False)
        
        author = ctx.author  # Get the author of the command
        
        user_id = str(author.id)
        user_data = guild_settings[guild_id]["users"].get(user_id, {})
        current_level = user_data.get("level", 0) if user_data else 0
        
        embed = discord.Embed(
            title="Level Role Configuration",
            description="",
            color=0x2a2d30  # Set the color to 0x2a2d30
        )
        
        levels_info = []
        
        if leveling_enabled:
            current_row = []  # Initialize the current row
            
            # Sort the level_roles dictionary by level
            sorted_levels = sorted(level_roles.items(), key=lambda x: int(x[0]))
            
            for level_str, role_id in sorted_levels:
                level = int(level_str)
                role = ctx.guild.get_role(int(role_id))
                if role:
                    if level <= current_level:
                        current_row.append(f"**Level {level}**\n**UNLOCKED**\n**| {role.mention}**")
                    else:
                        required_xp = max(0, xp_required_for_level(level) - (user_data.get("xp", 0) if user_data else 0))
                        current_row.append(f"**Level {level}**\nRemaining XP: **{required_xp}**\n**| {role.mention}**")
                else:
                    current_row.append(f"Level {level}\nLOCKED\nRole not found")
                
                # If the current row contains 3 items, add it to the levels_info and reset current_row
                if len(current_row) == 3:
                    levels_info.append(current_row)
                    current_row = []  # Reset the current row for the next set of levels
            
            # If there are any remaining levels in the current_row, add it to the levels_info
            if current_row:
                levels_info.append(current_row)
                
            # Add each row of levels to the embed
            for row_index, row in enumerate(levels_info):
                for level_info in row:
                    embed.add_field(name="\u200b", value=level_info, inline=True)
                if row_index == 10:  # Add fewer blank fields between the first and second row
                    embed.add_field(name="\u200b", value="\u200b", inline=False)  # Add a blank field to create space between rows
            
        else:
            embed.add_field(name="Levels", value="Leveling system is currently disabled. Use `level on` to enable it.", inline=False)
        
        # Set the author's name and avatar profile picture
        avatar_url = author.avatar.url if author.avatar else author.default_avatar.url
        embed.set_author(name=author.name, icon_url=avatar_url)
        embed.set_thumbnail(url=avatar_url) 
        await ctx.send(embed=embed)
    else:
        await ctx.send("Please enable leveling system using `level on`.")


@client.event
async def on_voice_state_update(member, before, after):
    guild_id = member.guild.id
    guild_settings.setdefault(guild_id, {})  # Ensure guild has settings
    join_to_create_channel_id = guild_settings[guild_id].get('join_to_create_channel_id')
    voice_logs_channel_id = guild_settings[guild_id].get('voice_logs_channel_id')

    if join_to_create_channel_id is None:
        for category in member.guild.categories:
            for channel in category.voice_channels:
                if channel.name == "Join to Create":
                    join_to_create_channel_id = channel.id
                    guild_settings[guild_id]['join_to_create_channel_id'] = join_to_create_channel_id
                    break
            if join_to_create_channel_id:
                break

    if after.channel and after.channel.id == join_to_create_channel_id:
        # Create a new voice channel with the user's name
        channel_name = f"{member.name}'s channel"
        new_channel = await after.channel.category.create_voice_channel(channel_name)

        # Grant permissions to the user who created the channel
        await new_channel.set_permissions(member, connect=True, mute_members=True, move_members=True, manage_channels=True)

        # Move the user to the new voice channel
        await member.move_to(new_channel)

    if before.channel and (before.channel.name.endswith("'s channel") or before.channel.name.startswith(member.name)):
        # Check if it's a user-created or claimed channel
        # Check if the channel became empty after the user moved out
        if len(before.channel.members) == 0:
            await before.channel.delete()

    if voice_logs_channel_id:
        logs_channel = member.guild.get_channel(voice_logs_channel_id)  
        if logs_channel:
            embed = discord.Embed()
            embed.set_author(name=member.name, icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

            if before.channel is None and after.channel is not None:
                embed.title = "Member Joined Voice Channel"
                embed.description = f"{member.mention} joined the voice channel {after.channel.name}."
                embed.color = discord.Color.green()
                await logs_channel.send(embed=embed)

            elif before.channel is not None and after.channel is None:
                if before.self_mute and before.self_deaf:
                    embed.title = "Member Disconnected"
                    embed.description = f"{member.mention} got disconnected."
                    embed.color = discord.Color.red()
                else:
                    embed.title = "Member Left Voice Channel"
                    embed.description = f"{member.mention} left the voice channel {before.channel.name}."
                    embed.color = discord.Color.red()
                await logs_channel.send(embed=embed)

            elif before.deaf != after.deaf:
                action = "deafened" if after.deaf else "undeafened"
                embed.title = f"Member {action}"
                embed.description = f"{member.mention} has been {action}."
                embed.color = discord.Color.orange() if after.deaf else discord.Color.blue()
                await logs_channel.send(embed=embed)

            elif before.mute != after.mute:
                action = "muted" if after.mute else "unmuted"
                embed.title = f"Member {action}"
                embed.description = f"{member.mention} has been {action}."
                embed.color = discord.Color.orange() if after.mute else discord.Color.blue()
                await logs_channel.send(embed=embed)

            elif before.channel != after.channel:
                before_channel_name = before.channel.name if before.channel else "Unknown Channel"
                embed.title = "Member Moved Voice Channel"
                embed.description = f"{member.mention} moved from {before_channel_name} to {after.channel.name}."
                embed.color = discord.Color.gold()
                await logs_channel.send(embed=embed)

            elif before.self_deaf != after.self_deaf:
                action = "self-deafened" if after.self_deaf else "undeafened"
                embed.title = f"Member {action}"
                embed.description = f"{member.mention} has {action}."
                embed.color = discord.Color.orange() if after.self_deaf else discord.Color.blue()
                await logs_channel.send(embed=embed)

            elif before.self_mute != after.self_mute:
                action = "self-muted" if after.self_mute else "unmuted"
                embed.title = f"Member {action}"
                embed.description = f"{member.mention} has {action}."
                embed.color = discord.Color.orange() if after.self_mute else discord.Color.blue()
                await logs_channel.send(embed=embed)

            elif before.self_stream != after.self_stream:
                action = "started streaming" if after.self_stream else "stopped streaming"
                embed.title = f"Member {action}"
                embed.description = f"{member.mention} has {action}."
                embed.color = discord.Color.orange() if after.self_stream else discord.Color.blue()
                await logs_channel.send(embed=embed)

            elif before.afk != after.afk:
                if after.afk:
                    embed.title = "Member Marked as AFK"
                    embed.description = f"{member.mention} has been marked as AFK."
                    embed.color = discord.Color.orange()
                else:
                    embed.title = "Member No Longer AFK"
                    embed.description = f"{member.mention} is no longer AFK."
                    embed.color = discord.Color.blue()
                await logs_channel.send(embed=embed)





import yt_dlp
import discord
import os
import asyncio
import requests
from bs4 import BeautifulSoup
import aiohttp
from googlesearch import search
import re


queues = {}
voice_clients = {}
yt_dl_options = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "extract_flat": False,
    "socket_timeout": 10,
    "nocheckcertificate": True,
    "cookiefile": "cookies.txt",  # Use YouTube cookies for authentication
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "opus",
    }]
}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -vn',
    'options': '-vn -b:a 128k -bufsize 128k'
}

async def fetch_lyrics(video_title):
    """Enhanced lyrics fetching with multiple fallback methods"""
    
    # Clean the video title by removing common YouTube suffixes
    clean_title = re.sub(r'\s*\([^)]*\)\s*', '', video_title)  # Remove (Official Video), (Audio), etc.
    clean_title = re.sub(r'\s*\[[^\]]*\]\s*', '', clean_title)  # Remove [Official], [Lyrics], etc.
    clean_title = re.sub(r'\s*-\s*Official\s*', ' ', clean_title)  # Remove "Official"
    clean_title = re.sub(r'\s*-\s*Audio\s*', ' ', clean_title)  # Remove "Audio"
    clean_title = re.sub(r'\s*-\s*Video\s*', ' ', clean_title)  # Remove "Video"
    clean_title = re.sub(r'\s*-\s*Lyrics\s*', ' ', clean_title)  # Remove "Lyrics"
    clean_title = clean_title.strip()
    
    # Try multiple parsing methods for artist and song
    artist = None
    song_title = None
    
    # Method 1: "Artist - Song" format
    match = re.match(r'^(.+?)\s*-\s*(.+)$', clean_title)
    if match:
        artist = match.group(1).strip()
        song_title = match.group(2).strip()
    
    # Method 2: "Artist: Song" format
    if not artist or not song_title:
        match = re.match(r'^(.+?)\s*:\s*(.+)$', clean_title)
        if match:
            artist = match.group(1).strip()
            song_title = match.group(2).strip()
    
    # Method 3: "Artist "Song"" format
    if not artist or not song_title:
        match = re.match(r'^(.+?)\s+"([^"]+)"', clean_title)
        if match:
            artist = match.group(1).strip()
            song_title = match.group(2).strip()
    
    # Method 4: If no clear separation, use the whole title as song name
    if not artist or not song_title:
        song_title = clean_title
        artist = ""
    
    # Create multiple search variations
    search_variations = []
    
    # If we have both artist and song
    if artist and song_title:
        search_variations.extend([
            f"{artist} {song_title} lyrics",
            f"{artist} - {song_title} lyrics",
            f'"{artist}" "{song_title}" lyrics',
            f"{song_title} {artist} lyrics"
        ])
    
    # Always include song-only searches as fallback
    search_variations.extend([
        f"{song_title} lyrics",
        f'"{song_title}" lyrics'
    ])
    
    # Try multiple lyrics sources with different search variations
    lyrics_sources = [
        "site:azlyrics.com",
        "site:genius.com", 
        "site:lyrics.com",
        "site:musixmatch.com",
        "site:metrolyrics.com"
    ]
    
    for search_variation in search_variations:
        for source in lyrics_sources:
            search_query = f"{search_variation} {source}"
            try:
                # Search for lyrics
                search_results = list(search(search_query))
                if search_results:
                    lyrics_url = search_results[0]
                    
                    # Try to fetch lyrics from the URL
                    async with aiohttp.ClientSession() as session:
                        async with session.get(lyrics_url, timeout=10) as response:
                            if response.status == 200:
                                html = await response.text()
                                soup = BeautifulSoup(html, 'html.parser')
                                
                                # Try multiple selectors for different lyrics sites
                                lyrics_text = None
                                
                                # AZLyrics format
                                if 'azlyrics.com' in lyrics_url:
                                    lyrics_div = soup.find("div", class_=None, id=None)
                                    if lyrics_div:
                                        # Remove script and style elements
                                        for script in lyrics_div(["script", "style"]):
                                            script.decompose()
                                        # Replace <br> tags with newlines
                                        for br in lyrics_div.find_all("br"):
                                            br.replace_with("\n")
                                        lyrics_text = lyrics_div.get_text().strip()
                                
                                # Genius format
                                elif 'genius.com' in lyrics_url:
                                    lyrics_div = soup.find("div", {"data-lyrics-container": "true"})
                                    if not lyrics_div:
                                        lyrics_div = soup.find("div", {"class": "lyrics"})
                                    if lyrics_div:
                                        # Remove script and style elements
                                        for script in lyrics_div(["script", "style"]):
                                            script.decompose()
                                        # Replace <br> tags with newlines
                                        for br in lyrics_div.find_all("br"):
                                            br.replace_with("\n")
                                        lyrics_text = lyrics_div.get_text().strip()
                                
                                # Lyrics.com format
                                elif 'lyrics.com' in lyrics_url:
                                    lyrics_div = soup.find("div", {"id": "lyric-body-text"})
                                    if not lyrics_div:
                                        lyrics_div = soup.find("div", {"class": "lyric-body"})
                                    if lyrics_div:
                                        for script in lyrics_div(["script", "style"]):
                                            script.decompose()
                                        for br in lyrics_div.find_all("br"):
                                            br.replace_with("\n")
                                        lyrics_text = lyrics_div.get_text().strip()
                                
                                # Musixmatch format
                                elif 'musixmatch.com' in lyrics_url:
                                    lyrics_div = soup.find("div", {"class": "lyrics"})
                                    if lyrics_div:
                                        for script in lyrics_div(["script", "style"]):
                                            script.decompose()
                                        for br in lyrics_div.find_all("br"):
                                            br.replace_with("\n")
                                        lyrics_text = lyrics_div.get_text().strip()
                                
                                # Metrolyrics format
                                elif 'metrolyrics.com' in lyrics_url:
                                    lyrics_div = soup.find("div", {"class": "lyrics-body"})
                                    if lyrics_div:
                                        for script in lyrics_div(["script", "style"]):
                                            script.decompose()
                                        for br in lyrics_div.find_all("br"):
                                            br.replace_with("\n")
                                        lyrics_text = lyrics_div.get_text().strip()
                                
                                # Generic fallback - look for any div with substantial text
                                if not lyrics_text:
                                    for div in soup.find_all("div"):
                                        text = div.get_text().strip()
                                        if len(text) > 200 and any(word in text.lower() for word in ['verse', 'chorus', 'bridge', 'lyrics']):
                                            # Remove script and style elements
                                            for script in div(["script", "style"]):
                                                script.decompose()
                                            # Replace <br> tags with newlines
                                            for br in div.find_all("br"):
                                                br.replace_with("\n")
                                            lyrics_text = div.get_text().strip()
                                            break
                                
                                # If we found lyrics, clean them up and return
                                if lyrics_text and len(lyrics_text) > 50:  # Ensure we have substantial lyrics
                                    # Clean up the lyrics
                                    # First, normalize line endings
                                    lyrics_text = lyrics_text.replace('\r\n', '\n')
                                    
                                    # Split into lines and clean each line
                                    lines = lyrics_text.split('\n')
                                    cleaned_lines = []
                                    current_section = []
                                    
                                    for line in lines:
                                        # Remove leading/trailing whitespace
                                        line = line.strip()
                                        
                                        # Skip empty lines and common metadata lines
                                        if not line or line.lower().startswith(('lyrics', 'submit corrections')):
                                            continue
                                            
                                        # If it's a section header [Verse], [Chorus], etc.
                                        if re.match(r'^\[.*?\]$', line):
                                            # If we have a previous section, add it to cleaned lines
                                            if current_section:
                                                cleaned_lines.append('\n'.join(current_section))
                                                cleaned_lines.append('')  # Add blank line between sections
                                            current_section = [f"**{line.strip('[]')}**"]  # Make section headers bold
                                        else:
                                            current_section.append(line)
                                    
                                    # Add the last section
                                    if current_section:
                                        cleaned_lines.append('\n'.join(current_section))
                                    
                                    # Join all sections with double newlines
                                    lyrics_text = '\n\n'.join(cleaned_lines)
                                    
                                    # Limit length to fit in Discord embed
                                    if len(lyrics_text) > 4000:
                                        lyrics_text = lyrics_text[:4000] + "...\n\n[Lyrics truncated due to length]"
                                    
                                    return lyrics_text
                                
            except Exception as e:
                print(f"Error fetching lyrics from {search_query}: {e}")
                continue
    
    # If all methods fail, return a helpful message
    if artist and song_title:
        return f"Could not find lyrics for '{artist} - {song_title}'. Try searching manually on AZLyrics, Genius, or Lyrics.com"
    else:
        return f"Could not find lyrics for '{clean_title}'. Try searching manually on AZLyrics, Genius, or Lyrics.com"



from youtubesearchpython import VideosSearch

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

client_id = "49d6f83ccdeb456b95595031f37e4ea3"
client_secret = "493a2c6d06134cafb9585c62e5a45d91"

spotify_client = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret, cache_handler=None))

async def play_playlist(ctx, playlist_tracks):
    for item in playlist_tracks['items']:
        track_info = item['track']
        artist = track_info['artists'][0]['name']
        song_title = track_info['name']
        try:
            search_query = f"{artist} {song_title}"
            url = await search_youtube_video(search_query)
            if url:
                queues[ctx.guild.id].append(url)
                if len(queues[ctx.guild.id]) == 1:  # Start playing the first song immediately
                    await play_next(ctx)
                await asyncio.sleep(1)  # Add a small delay before downloading the next song (optional)
            else:
                print(f"Could not find YouTube video for: {artist} - {song_title}")
        except Exception as e:
            print(f"Error searching for {artist} - {song_title}: {e}")
            continue

@client.command(name='play', aliases=['p'])
@is_whitelisted()
async def play(ctx, *, query):
    try:
        await ctx.message.delete()  # Delete the original command message

        voice_channel = ctx.author.voice.channel
        if voice_channel:
            if ctx.guild.id not in queues:
                # Initialize queue for the guild if not already present
                queues[ctx.guild.id] = []

            if query.startswith("http"):
                # If the query is a link
                if "open.spotify.com" in query:
                    # Check if it's a Spotify link
                    if "track" in query:
                        # Extract track ID from the Spotify link
                        track_id = query.split("/")[-1].split("?")[0]
                        # Get track info from Spotify API
                        track_info = spotify_client.track(track_id)
                        # Extract song name and artist
                        artist = track_info['artists'][0]['name']
                        song_title = track_info['name']
                        
                        # Search for the song on YouTube
                        try:
                            search_query = f"{artist} {song_title}"
                            url = await search_youtube_video(search_query)
                            if url:
                                pass  # URL found successfully
                            else:
                                await ctx.send("❌ Could not find the Spotify track on YouTube.")
                                return
                        except Exception as e:
                            await ctx.send(f"❌ Error searching for Spotify track: {str(e)}")
                            return
                    elif "playlist" in query:
                        # Extract playlist ID from the Spotify link
                        playlist_id = query.split("/")[-1].split("?")[0]
                        # Get tracks info from Spotify API
                        playlist_tracks = spotify_client.playlist_tracks(playlist_id)
                        # Play the playlist
                        await play_playlist(ctx, playlist_tracks)
                        return
                    else:
                        await ctx.send("Only Spotify track and playlist links are supported.")
                        return
                else:
                    # Assume it's a YouTube link
                    url = query
            else:
                # If the query is a song name, search for it on YouTube
                try:
                    url = await search_youtube_video(query)
                    if not url:
                        await ctx.send("❌ No results found for your search.")
                        return
                except Exception as e:
                    await ctx.send(f"❌ Error searching for song: {str(e)}")
                    return
            
            # Add requested song(s) to the queue
            if isinstance(url, list):
                queues[ctx.guild.id].extend(url)
            else:
                queues[ctx.guild.id].append(url)
            
            if ctx.guild.id not in voice_clients or not voice_clients[ctx.guild.id].is_playing():
                # If the bot is not already playing, play the requested song(s) immediately
                await play_next(ctx)
            else:
                if isinstance(url, list):
                    queue_message = f"Playlist added to the queue. There are now {len(queues[ctx.guild.id])} songs in the queue."
                else:
                    if len(queues[ctx.guild.id]) > 0:  # Check if there are more songs in the queue
                        song_index = len(queues[ctx.guild.id])  # Get song's index in the queue
                        try:
                            song_info = await get_song_info(url)  # Get song info asynchronously
                            song_name = song_info.get('title', 'Unknown')  # Extract song title
                        except:
                            song_name = "Unknown Song"
                        
                        # Create the queue message
                        queue_message = f"{song_name} is now added to the queue and is number {song_index} out of {len(queues[ctx.guild.id])} in the queue."
                    else:
                        queue_message = "Song added to the queue."
                
                embed = discord.Embed(title="Queue", description=queue_message, color=0x2a2d30)
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Error", description="You are not in a voice channel.", color=0xFF0000)
            await ctx.send(embed=embed)
    except Exception as e:
        print(f"Error in play command: {e}")
        await ctx.send(f"❌ An error occurred: {str(e)}")


async def get_song_info(url):
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
    return data

async def play_audio(ctx, url):
    try:
        # Check if the bot is already connected to a voice channel in the guild
        if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_connected():
            voice_client = voice_clients[ctx.guild.id]
        else:
            # Connect to the voice channel of the author of the command
            voice_channel = ctx.author.voice.channel
            voice_client = await voice_channel.connect(timeout=3.0, reconnect=True, self_deaf=True)
            voice_clients[voice_client.guild.id] = voice_client
    except Exception as e:
        await ctx.send(f"❌ Failed to join voice channel. Please try again.")
        return

    # Extract audio information from YouTube URL
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

    # Extract relevant data for playback
    song = data['url']
    duration = data['duration']
    formatted_duration = f"{duration // 60:02}:{duration % 60:02}"

    # Create FFmpegOpusAudio player
    player = discord.FFmpegOpusAudio(song, **ffmpeg_options)
    player.volume = 100

    # Play audio in the voice channel
    voice_clients[ctx.guild.id].play(player)
    voice_clients[ctx.guild.id].source.title = data['title']

    # Send a message with information about the currently playing song
    embed = discord.Embed(title="Now playing", color=0x2a2d30)
    embed.set_thumbnail(url=data['thumbnail'])
    requester = ctx.author.mention
    embed.add_field(name="Song", value=f"[{data['title']}]({url})", inline=False)
    embed.add_field(name="Requester", value=requester, inline=True)
    embed.add_field(name="Volume", value=player.volume, inline=True)
    embed.add_field(name="Duration", value=f"00:00 / {formatted_duration}", inline=True)
    message = await ctx.send(embed=embed)

    # Update playback time periodically
    playback_time = 0
    while voice_clients[ctx.guild.id].is_playing() and playback_time < duration:
        playback_time += 1
        formatted_current_time = f"{playback_time // 60:02}:{playback_time % 60:02}"
        progress_bar = f"{formatted_current_time} / {formatted_duration}"
        embed.set_field_at(3, name="Duration", value=progress_bar, inline=True)
        await message.edit(embed=embed)
        await asyncio.sleep(1)

    # Song finished playing, check if there are songs in the queue
    await play_next(ctx)


async def play_next(ctx):
    # Delete lyrics message if it exists when song ends
    if ctx.guild.id in lyrics_messages:
        try:
            await lyrics_messages[ctx.guild.id].delete()
            del lyrics_messages[ctx.guild.id]
        except:
            pass  # Message might already be deleted
    
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        # If there are songs in the queue, play the next one
        url = queues[ctx.guild.id].pop(0)
        await play_audio(ctx, url)

@client.command()
@is_whitelisted()
async def skip(ctx):
    try:
        if ctx.guild.id in voice_clients:
            voice_clients[ctx.guild.id].stop()
            await play_next(ctx)
        else:
            embed = discord.Embed(title="Error", description="I'm not playing any music right now.", color=0xFF0000)  # Set embed color to red
            await ctx.send(embed=embed)
    except Exception as e:
        print(e)

@client.command()
@is_whitelisted()
async def pause(ctx):
    try:
        if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
            voice_clients[ctx.guild.id].pause()
            embed = discord.Embed(title="⏸️ Paused", description="Music has been paused. Use `.resume` to continue playing.", color=0x2a2d30)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Error", description="No music is currently playing.", color=0xFF0000)
            await ctx.send(embed=embed)
    except Exception as e:
        print(f"Error in pause command: {e}")
        await ctx.send("❌ An error occurred while trying to pause.")

@client.command()
@is_whitelisted()
async def resume(ctx):
    try:
        if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_paused():
            voice_clients[ctx.guild.id].resume()
            embed = discord.Embed(title="▶️ Resumed", description="Music has been resumed.", color=0x2a2d30)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Error", description="No music is currently paused.", color=0xFF0000)
            await ctx.send(embed=embed)
    except Exception as e:
        print(f"Error in resume command: {e}")
        await ctx.send("❌ An error occurred while trying to resume.")

@client.command()
@is_whitelisted()
async def stop(ctx):
    try:
        voice_clients[ctx.guild.id].stop()
        await voice_clients[ctx.guild.id].disconnect()
    except Exception as e:
        print(e)

# Store lyrics messages for each guild
lyrics_messages = {}

@client.command(name='lyrics', aliases=['l'])
@is_whitelisted()
async def lyrics(ctx):
    try:
        if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
            # Delete previous lyrics message if it exists
            if ctx.guild.id in lyrics_messages:
                try:
                    await lyrics_messages[ctx.guild.id].delete()
                except:
                    pass  # Message might already be deleted
            
            song_title = voice_clients[ctx.guild.id].source.title
            
            # Send a loading message
            loading_msg = await ctx.send("🔍 Searching for lyrics...")
            
            lyrics = await fetch_lyrics(song_title)
            
            # Create embed with lyrics
            embed = discord.Embed(title=f"📜 Lyrics for: {song_title}", description=lyrics, color=0x2a2d30)
            
            # Delete loading message and send lyrics
            await loading_msg.delete()
            lyrics_msg = await ctx.send(embed=embed)
            
            # Store the lyrics message for this guild
            lyrics_messages[ctx.guild.id] = lyrics_msg
        else:
            embed = discord.Embed(title="❌ No Music Playing", description="I'm not playing any music right now. Use `.play` to start playing a song first.", color=0xFF0000)
            await ctx.send(embed=embed)
    except Exception as e:
        print(f"Error in lyrics command: {e}")
        await ctx.send(f"❌ An error occurred while fetching lyrics: {str(e)}")


import asyncio
import random
import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone  # ✅ Proper datetime import



@client.command()
async def giveaway(ctx, channel: discord.TextChannel, duration: str, guaranteed_winner: str = None, winners: int = 1, *, prize: str):
    try:
        # Time conversion setup
        time_conversion = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}

        # Validate duration input
        if len(duration) < 2 or duration[-1] not in time_conversion or not duration[:-1].isdigit():
            await ctx.send("Invalid duration format. Use something like `10s`, `5m`, `1h`, or `2d`.")
            return

        # Calculate end time
        seconds = int(duration[:-1]) * time_conversion[duration[-1]]
        end_time = datetime.datetime.now(timezone.utc) + timedelta(seconds=seconds)
        end_time_unix = int(end_time.timestamp())

        # Send giveaway embed
        embed = discord.Embed(title=prize, description="React with 🎉 to enter the giveaway.", color=discord.Color.from_rgb(42, 45, 48))
        embed.add_field(
            name="Giveaway Info",
            value=(
                f"**Ends:** <t:{end_time_unix}:R>\n"
                f"**Hosted by:** {ctx.author.mention}\n"
                f"**Winners:** {winners}"
            ),
            inline=False
        )

        message = await channel.send(embed=embed)
        await message.add_reaction("🎉")
        await ctx.send(f"✅ Giveaway started in {channel.mention}!")

        # Wait until giveaway ends
        await asyncio.sleep(seconds)

        # Fetch updated message and reactions
        message = await channel.fetch_message(message.id)
        reaction = discord.utils.get(message.reactions, emoji="🎉")
        if not reaction:
            await channel.send("No one participated in the giveaway.")
            return

        users = [user async for user in reaction.users() if user != client.user]

        # Check for guaranteed winner
        guaranteed_user = None
        if guaranteed_winner:
            try:
                gw_id = int(guaranteed_winner.strip("<@!>"))
                for user in users:
                    if user.id == gw_id:
                        guaranteed_user = user
                        users.remove(user)
                        break
            except:
                for user in users:
                    if guaranteed_winner.lower() in (user.name.lower(), user.display_name.lower()):
                        guaranteed_user = user
                        users.remove(user)
                        break

        # Not enough participants
        if len(users) + (1 if guaranteed_user else 0) < winners:
            await channel.send("Not enough participants for the giveaway.")
            return

        # Select winners
        winners_list = random.sample(users, winners - (1 if guaranteed_user else 0))
        if guaranteed_user:
            winners_list.append(guaranteed_user)

        winners_mentions = ', '.join([winner.mention for winner in winners_list])

        # Edit giveaway message with results
        result_embed = discord.Embed(title=prize, description="🎉 Giveaway has ended! 🎉", color=discord.Color.red())
        result_embed.add_field(
            name="Giveaway Results",
            value=(
                f"**Winner(s):** {winners_mentions}\n"
                f"**Prize:** {prize}\n"
                f"**Hosted by:** {ctx.author.mention}"
            ),
            inline=False
        )
        await message.edit(embed=result_embed)

        # Announce winners
        await channel.send(f"Congratulations {winners_mentions}! You won the giveaway for **{prize}**!")

    except Exception as e:
        await ctx.send(f"An error occurred: `{e}`")


@client.command()
async def reroll(ctx, message_id: int, winners: int, *, user_mentions: str = None):
    try:
        # Fetch the message with the given ID
        message = await ctx.channel.fetch_message(message_id)
        
        # Check if the message is an embed and has a giveaway announcement
        if not message.embeds or "Giveaway has ended!" not in message.embeds[0].description:
            await ctx.send("The provided message ID does not correspond to an ended giveaway.")
            return
        
        # Fetch the reaction
        reaction = discord.utils.get(message.reactions, emoji="🎉")
        if not reaction:
            await ctx.send("No reactions found on the giveaway message.")
            return
        
        # Collect users who reacted
        users = []
        async for user in reaction.users():
            if user != client.user:
                users.append(user)
        
        # Filter users if specific mentions or IDs were provided
        if user_mentions:
            # Split mentions or IDs by comma and strip any whitespace
            mention_ids = [mention.strip() for mention in user_mentions.split(',')]
            # Convert mentions to user objects if possible
            filtered_users = []
            for mention_id in mention_ids:
                try:
                    user_id = int(mention_id)
                    user = ctx.guild.get_member(user_id) or await client.fetch_user(user_id)
                    if user in users:
                        filtered_users.append(user)
                except ValueError:
                    # Ignore invalid IDs
                    continue
            users = filtered_users
        
        # Check if there are enough participants
        if len(users) < winners:
            await ctx.send("Not enough participants for the reroll.")
            return
        
        # Choose new winners
        winners_list = random.sample(users, winners)
        winners_mentions = ', '.join([winner.mention for winner in winners_list])
        
        # Edit the original message to announce the new winners
        embed = discord.Embed(title="Giveaway Reroll", description="🎉 Reroll results! 🎉", color=discord.Color.red())
        embed.add_field(name="New Winner(s)", value=winners_mentions, inline=True)
        await message.edit(embed=embed)
        
        # Announce the new winners in the channel
        await ctx.send(f"Congratulations {winners_mentions}! You won the rerolled giveaway!")

    except Exception as e:
        await ctx.send(f"An error occurred: {e}")


@client.command()
@is_whitelisted()
async def inrole(ctx, *, role_identifier: str = None):
    if role_identifier is None:
        await ctx.send("Please specify a role name, mention, or ID.")
        return

    role = None
    
    # Check if the identifier is a mention
    if role_identifier.startswith('<@&') and role_identifier.endswith('>'):
        role_id = int(role_identifier[3:-1])
        role = ctx.guild.get_role(role_id)
    # Check if the identifier is a valid ID
    elif role_identifier.isdigit():
        role = ctx.guild.get_role(int(role_identifier))
    # Otherwise, treat it as a role name
    else:
        for r in ctx.guild.roles:
            if r.name.lower() == role_identifier.lower():
                role = r
                break

    if role is None:
        await ctx.send("Role not found. Please specify a valid role name, mention, or ID.")
        return

    members = [member.mention for member in role.members]
    embed = discord.Embed(
        title=f"Role: {role.name}",
        description=f"Members with the role **{role.name}**",
        color=0x2a2d30
    )

    if members:
        embed.add_field(name=f"Members ({len(members)}):", value=', '.join(members), inline=False)
    else:
        embed.add_field(name="Members (0):", value="No members have this role.", inline=False)

    await ctx.send(embed=embed)

import io
@client.command(name='stealemoji', aliases=['se'])
@is_whitelisted()
@commands.has_guild_permissions(manage_emojis_and_stickers=True)
async def stealemoji(ctx, *emojis: str):
    successful_additions = []
    errors = []

    for emoji in emojis:
        try:
            # Extract emoji URL
            if emoji.startswith('<:') or emoji.startswith('<a:'):
                emoji_name = emoji.split(':')[1]
                emoji_id = emoji.split(':')[2][:-1]
                animated = emoji.startswith('<a:')
                emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if animated else 'png'}"

                # Download emoji
                response = requests.get(emoji_url)
                response.raise_for_status()
                emoji_image = io.BytesIO(response.content)

                # Add emoji to the server
                guild = ctx.guild
                await guild.create_custom_emoji(name=emoji_name, image=emoji_image.read())
                
                successful_additions.append(emoji_name)
            else:
                errors.append(f'Invalid format for {emoji}')

        except Exception as e:
            errors.append(f'Error with {emoji}: {e}')

    # Create embed message
    embed = discord.Embed(color=0x2a2d30)
    if successful_additions:
        embed.add_field(name='Added Emojis', value=', '.join(successful_additions), inline=False)
    if errors:
        embed.add_field(name='Errors', value='\n'.join(errors), inline=False)

    await ctx.send(embed=embed)

@stealemoji.error
async def stealemoji_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have the required permissions to add custom emojis to the server.")



@client.command(name='clonesticker', aliases=['css'])
@is_whitelisted()
@commands.has_guild_permissions(manage_emojis_and_stickers=True)
async def clone_sticker(ctx):
    if not ctx.message.reference:
        embed = discord.Embed(description="Please reply to a message containing a sticker.", color=0x2a2d30)
        await ctx.send(embed=embed)
        return

    ref_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    
    if not ref_message.stickers:
        embed = discord.Embed(description="The replied message does not contain a sticker.", color=0x2a2d30)
        await ctx.send(embed=embed)
        return

    sticker_item = ref_message.stickers[0]
    sticker = await client.fetch_sticker(sticker_item.id)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(sticker.url) as resp:
            if resp.status != 200:
                embed = discord.Embed(description="Failed to download sticker.", color=0x2a2d30)
                await ctx.send(embed=embed)
                return
            data = io.BytesIO(await resp.read())

    await ctx.guild.create_sticker(
        name=sticker.name,
        description=sticker.description or "Cloned sticker",
        emoji=sticker.emoji or "😊",
        file=discord.File(data, filename=f"{sticker.name}.png")
    )
    embed = discord.Embed(description=f"Sticker '{sticker.name}' has been cloned and added to the server.", color=0x2a2d30)
    await ctx.send(embed=embed)

@clone_sticker.error
async def clone_sticker_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(description="You do not have the required permissions to add stickers and emojis to the server.", color=0x2a2d30)
        await ctx.send(embed=embed)

@client.command()
@is_whitelisted()
async def role(ctx, user_input: str, *, role_input: commands.clean_content):
    if ctx.author.guild_permissions.manage_roles:
        member = None
        role = None
        
        if user_input.startswith('<@') and user_input.endswith('>'):
            member = ctx.message.mentions[0]
        elif user_input.isdigit():
            member = ctx.guild.get_member(int(user_input))
            if member is None:
                member = discord.utils.find(lambda m: m.id == int(user_input), ctx.guild.members)
        else:
            member = discord.utils.find(lambda m: m.name.lower() == user_input.lower() or m.display_name.lower() == user_input.lower(), ctx.guild.members)
        
        if ctx.message.role_mentions:
            role = ctx.message.role_mentions[0]
        elif role_input.isdigit():
            role = ctx.guild.get_role(int(role_input))
        else:
            role = discord.utils.find(lambda r: r.name.lower() == role_input.lower(), ctx.guild.roles)

        if member and role:
            highest_role = ctx.author.top_role
            if role.position >= highest_role.position:
                embed = discord.Embed(description="You cannot assign a role higher or equal to your highest role.", color=0x2a2d30)
                await ctx.send(embed=embed)
            else:
                await member.add_roles(role)
                embed = discord.Embed(description=f'{member.mention} has been given the {role.name} role.', color=0x2a2d30)
                await ctx.send(embed=embed)
        elif not member:
            embed = discord.Embed(description="User not found.", color=0x2a2d30)
            await ctx.send(embed=embed)
        elif not role:
            embed = discord.Embed(description="Role not found.", color=0x2a2d30)
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed(description="You don't have permission to manage roles.", color=0x2a2d30)
        await ctx.send(embed=embed)

@role.error
async def role_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(description="Please provide a user and a role.", color=0x2a2d30)
        await ctx.send(embed=embed)
    elif isinstance(error, commands.BadArgument):
        embed = discord.Embed(description="Role not found.", color=0x2a2d30)
        await ctx.send(embed=embed)

from discord import Embed

@client.command()
@is_whitelisted()
async def banner(ctx, user_id: int):
    try:
        user = await client.fetch_user(user_id)
        if user.banner:
            embed = Embed(description=f"{user.mention}'s Banner", color=0x2a2d30)
            embed.set_image(url=user.banner.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("No banner found.")
    except discord.NotFound:
        await ctx.send("User not found.")

@banner.error
async def banner_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("Invalid user ID. Please provide a valid user ID.")


import instaloader
from io import BytesIO

# Import required libraries
import requests
import json

import shutil

# Initialize the Instagram loader just for profile info
L = instaloader.Instaloader()

@client.command()
async def insta(ctx, insta_username):
    try:
        # Create the profile URL
        profile_url = f"https://www.instagram.com/{insta_username}/"
        
        # Get profile info using instaloader
        profile = instaloader.Profile.from_username(L.context, insta_username)
        
        # Create embed with profile info
        embed = discord.Embed(
            title=f"Instagram Profile of {insta_username}",
            url=profile_url,
            color=0x2a2d30
        )
        
        # Add profile information
        embed.add_field(name="Posts", value=profile.mediacount, inline=True)
        embed.add_field(name="Followers", value=profile.followers, inline=True)
        embed.add_field(name="Following", value=profile.followees, inline=True)
        
        if profile.biography:
            embed.add_field(name="Bio", value=profile.biography, inline=False)
        
        # Set the profile picture
        embed.set_thumbnail(url=profile.profile_pic_url)
        
        # Send the embed
        await ctx.send(embed=embed)

        # Check if profile is private
        if profile.is_private:
            embed = discord.Embed(
                description=f"{insta_username}'s profile is private.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        # Try to download stories using Instagram's web API
        try:
            # Create stories directory
            user_stories_dir = f"instagram_stories/{insta_username}"
            os.makedirs(user_stories_dir, exist_ok=True)
            
            # Set up session with required headers
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Origin': 'https://www.instagram.com',
                'Referer': 'https://www.instagram.com/',
                'X-IG-App-ID': '936619743392459'
            })

            # Set cookies
            session.cookies.set('sessionid', '75456884376%3Au6JdIzKeU8qCww%3A10%3AAYe-3jygooBioU1sfC89_bZ2epgVaHwcE3Fpofv1TA', domain='.instagram.com')
            
            # Get user ID
            user_id = str(profile.userid)
            
            # Get stories data
            stories_url = f'https://i.instagram.com/api/v1/feed/user/{user_id}/story/'
            response = session.get(stories_url)
            
            if response.status_code == 200:
                stories_data = response.json()
                
                if 'reel' in stories_data and 'items' in stories_data['reel']:
                    stories = stories_data['reel']['items']
                    stories_downloaded = False
                    story_count = 0
                    total_stories = len(stories)
                    
                    # Start downloading stories
                    
                    for index, story in enumerate(stories, 1):
                        try:
                            # Use story's timestamp if available, otherwise use current time
                            if 'taken_at' in story:
                                timestamp = datetime.datetime.fromtimestamp(story['taken_at']).strftime('%Y%m%d_%H%M%S')
                            else:
                                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                            
                            if story.get('video_versions'):
                                # It's a video story
                                url = story['video_versions'][0]['url']
                                filename = f"{timestamp}_story_{index}_video.mp4"
                            else:
                                # It's a photo story
                                url = story['image_versions2']['candidates'][0]['url']
                                filename = f"{timestamp}_story_{index}_photo.png"
                            
                            filepath = os.path.join(user_stories_dir, filename)
                            
                            # Download the story with retry mechanism
                            max_retries = 3
                            for retry in range(max_retries):
                                try:
                                    media_response = session.get(url, timeout=10)
                                    if media_response.status_code == 200:
                                        with open(filepath, 'wb') as f:
                                            f.write(media_response.content)
                                        story_count += 1
                                        stories_downloaded = True
                                        print(f"Downloaded story {index}/{total_stories}")
                                        break
                                except Exception as download_error:
                                    if retry == max_retries - 1:  # Last retry
                                        print(f"Failed to download story {index} after {max_retries} attempts: {download_error}")
                                    else:
                                        await asyncio.sleep(1)  # Wait before retry
                                
                        except Exception as item_error:
                            print(f"Error downloading story item: {item_error}")
                            continue
                    
                    if stories_downloaded:
                        # Get all downloaded files
                        files = []
                        for filename in sorted(os.listdir(user_stories_dir)):
                            filepath = os.path.join(user_stories_dir, filename)
                            if os.path.getsize(filepath) < 8 * 1024 * 1024:  # Check if file is under 8MB
                                files.append(discord.File(filepath))
                        
                        # Split files into groups of 10 (Discord's limit)
                        file_groups = [files[i:i + 10] for i in range(0, len(files), 10)]
                        
                        # Send files in groups
                        for group in file_groups:
                            await ctx.send(files=group)
                            
                        # Delete the user's story folder after sending files
                        import shutil
                        try:
                            shutil.rmtree(user_stories_dir)
                        except Exception as e:
                            print(f"Error deleting folder: {e}")
                    else:
                        await ctx.send("No stories found.")
                        # Clean up empty folder if it exists
                        try:
                            if os.path.exists(user_stories_dir):
                                shutil.rmtree(user_stories_dir)
                        except Exception as e:
                            print(f"Error deleting empty folder: {e}")
            else:
                raise Exception(f"API returned status code {response.status_code}")

        except Exception as e:
            print(f"Story download error: {e}")
            embed = discord.Embed(
                description="Could not download stories. The user might not have any active stories.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    except instaloader.exceptions.ProfileNotExistsException:
        embed = discord.Embed(
            description="Profile not found. Please check the username and try again.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"Error: {e}")
        embed = discord.Embed(
            description="An error occurred while fetching the profile.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


import datetime as dt
@client.command(aliases=['rblx'])
@is_whitelisted()
async def roblox(ctx, username):
    try:
        # Fetch user info from Roblox API (modern endpoint)
        user_response = requests.post(
            "https://users.roblox.com/v1/usernames/users",
            json={"usernames": [username]}
        )
        user_data = user_response.json()
        user_list = user_data.get('data', [])

        if not user_list:
            raise ValueError("User not found")

        user_id = user_list[0]["id"]

        # Fetch avatar image
        avatar_response = requests.get(
            f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=720x720&format=Png&isCircular=false"
        )
        avatar_data = avatar_response.json()
        avatar_url = avatar_data['data'][0]['imageUrl']

        # Fetch account information
        account_response = requests.get(
            f"https://users.roblox.com/v1/users/{user_id}"
        )
        account_data = account_response.json()
        created_at_str = account_data['created']
        created_at = dt.datetime.strptime(created_at_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        created_at_formatted = created_at.strftime("%B %d, %Y")

        # Fetch last online status
        presence_response = requests.post(
            'https://presence.roblox.com/v1/presence/users',
            json={"userIds": [user_id]}
        )
        presence_response.raise_for_status()
        presence_data = presence_response.json()
        user_presence = presence_data['userPresences'][0]
        presence_status = "Online" if user_presence['userPresenceType'] != 0 else "Offline"
        
        # Calculate last online time if user is offline
        if presence_status == "Offline":
            last_online_str = user_presence.get('lastOnline', None)
            last_online = dt.datetime.strptime(last_online_str, "%Y-%m-%dT%H:%M:%S.%fZ") if last_online_str else None

            # Calculate difference in time
            if last_online:
                time_difference = dt.datetime.utcnow() - last_online
                if time_difference.days > 2:
                    last_online_formatted = f"Days ago"
                elif time_difference.seconds // 3600 > 0:
                    last_online_formatted = f"{time_difference.seconds // 3600} hours ago"
                elif time_difference.seconds // 60 > 0:
                    last_online_formatted = f"{time_difference.seconds // 60} minutes ago"
                else:
                    last_online_formatted = f"{time_difference.seconds} seconds ago"
            else:
                last_online_formatted = "Unknown"
        else:
            last_online_formatted = "0 seconds ago"

        # Fetch followers count
        followers_response = requests.get(
            f"https://friends.roblox.com/v1/users/{user_id}/followers/count"
        )
        followers_count = followers_response.json().get('count', 0)

        # Fetch following count
        following_response = requests.get(
            f"https://friends.roblox.com/v1/users/{user_id}/following/count"
        )
        following_count = following_response.json().get('count', 0)

        # Fetch friends count
        friends_response = requests.get(
            f"https://friends.roblox.com/v1/users/{user_id}/friends/count"
        )
        friends_count = friends_response.json().get('count', 0)

        # Profile URL
        profile_url = f"https://www.roblox.com/users/{user_id}/profile"

        # Create embed message
        embed = discord.Embed(
            title=f"Roblox Profile of {username}",
            url=profile_url,
            color=0x2a2d30,
            timestamp=created_at
        )
        embed.set_thumbnail(url=avatar_url)
        embed.add_field(name="Created", value=created_at_formatted, inline=True)
        embed.add_field(name="Last Online", value=last_online_formatted, inline=True)
        embed.add_field(name="Status", value=presence_status, inline=True)
        embed.add_field(name="Followers", value=followers_count, inline=True)
        embed.add_field(name="Following", value=following_count, inline=True)
        embed.add_field(name="Friends", value=friends_count, inline=True)
        await ctx.send(embed=embed)

    except ValueError as e:
        embed = discord.Embed(
            description=f"Error: {e}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            description=f"An error occurred: {e}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


import requests
from io import BytesIO
import instaloader
import requests
import aiohttp




timeout_log_channels = {}
embed_color = discord.Color.from_rgb(42, 45, 48)

import datetime
@client.command()
@is_whitelisted()
async def timeoutlogs(ctx, channel: discord.TextChannel = None):
    if channel is None:
        embed = discord.Embed(
            title="Usage",
            description="`.timeoutlogs <channel_mention> or <channel_id>`",
            color=embed_color
        )
        await ctx.send(embed=embed)
        return

    timeout_log_channels[ctx.guild.id] = channel.id
    await ctx.send(f"Timeout log channel set to {channel.mention}.")

import datetime

async def log_timeout_action(ctx, member, action, duration, reason):
    guild_id = ctx.guild.id
    timeout_log_channel_id = timeout_log_channels.get(guild_id)
    if timeout_log_channel_id:
        timeout_log_channel = ctx.guild.get_channel(timeout_log_channel_id)
        if timeout_log_channel:
            embed = discord.Embed(title="Timed Out", color=0x2a2d30)
            embed.add_field(name="User", value=member.mention, inline=True)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Duration/Reason", value=f"{duration} - {reason}", inline=True)
            await timeout_log_channel.send(embed=embed)

        embed = discord.Embed(description=f"{member.mention} has been {action} for {duration}. Reason: {reason}", color=0x2a2d30)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(description=f"{member.mention} has been {action} for {duration}. Reason: {reason}", color=0x2a2d30)
        await ctx.send(embed=embed)

async def log_untimeout_action(ctx, member, action):
    guild_id = ctx.guild.id
    timeout_log_channel_id = timeout_log_channels.get(guild_id)
    if timeout_log_channel_id:
        timeout_log_channel = ctx.guild.get_channel(timeout_log_channel_id)
        if timeout_log_channel:
            embed = discord.Embed(title="Untimed Out", color=0x2a2d30)
            embed.add_field(name="User", value=member.mention, inline=True)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            await timeout_log_channel.send(embed=embed)
        await ctx.send(f"{member.mention} has been {action}.")
    else:
        await ctx.send(f"{member.mention} has been {action}.")


embed_color = discord.Color.from_rgb(42, 45, 48)


import datetime
@client.command(name='timeout', aliases=['to'])
@is_whitelisted()
async def timeout(ctx, member: discord.Member = None, timelimit = None, *, reason="No reason provided"):
    if member is None or timelimit is None:
        embed = discord.Embed(
            title="Usage",
            description="`.timeout <member_mention> <time_limit> [reason]`",
            color=embed_color
        )
        await ctx.send(embed=embed)
        return

    if ctx.author.guild_permissions.manage_roles:
        if "s" in timelimit:
            gettime = timelimit.strip("s")
            if int(gettime) > 2419000:
                await ctx.send("The timeout duration cannot be more than 28 days.")
            else:
                newtime = datetime.timedelta(seconds=int(gettime))
                await member.edit(timed_out_until=discord.utils.utcnow() + newtime)
                await log_timeout_action(ctx, member, "timed out", f"{gettime} seconds", reason)
        elif "m" in timelimit:
            gettime = timelimit.strip("m")
            if int(gettime) > 40320:
                await ctx.send("The timeout duration cannot be more than 28 days.")
            else:
                newtime = datetime.timedelta(minutes=int(gettime))
                await member.edit(timed_out_until=discord.utils.utcnow() + newtime)
                await log_timeout_action(ctx, member, "timed out", f"{gettime} minutes", reason)
        elif "h" in timelimit:
            gettime = timelimit.strip("h")
            if int(gettime) > 672:
                await ctx.send("The timeout duration cannot be more than 28 days.")
            else:
                newtime = datetime.timedelta(hours=int(gettime))
                await member.edit(timed_out_until=discord.utils.utcnow() + newtime)
                await log_timeout_action(ctx, member, "timed out", f"{gettime} hours", reason)
        elif "d" in timelimit:
            gettime = timelimit.strip("d")
            if int(gettime) > 28:
                await ctx.send("The timeout duration cannot be more than 28 days.")
            else:
                newtime = datetime.timedelta(days=int(gettime))
                await member.edit(timed_out_until=discord.utils.utcnow() + newtime)
                await log_timeout_action(ctx, member, "timed out", f"{gettime} days", reason)
        elif "w" in timelimit:
            gettime = timelimit.strip("w")
            if int(gettime) > 4:
                await ctx.send("The timeout duration cannot be more than 4 weeks.")
            else:
                newtime = datetime.timedelta(weeks=int(gettime))
                await member.edit(timed_out_until=discord.utils.utcnow() + newtime)
                await log_timeout_action(ctx, member, "timed out", f"{gettime} weeks", reason)
    else:
        await ctx.send("You don't have permission to use this command.")

embed_color = discord.Color.from_rgb(42, 45, 48)

@client.command(name='untimeout', aliases=['unto'])
@is_whitelisted()
async def untimeout(ctx, member: discord.Member = None):
    if member is None:
        embed = discord.Embed(
            title="Usage",
            description="`!untimeout <member_mention>`",
            color=embed_color
        )
        await ctx.send(embed=embed)
        return

    if ctx.author.guild_permissions.manage_roles:
        if member.timed_out_until is not None:
            await member.edit(timed_out_until=None)
            await log_untimeout_action(ctx, member, "untimed out")
        else:
            await ctx.send(f"{member.mention} is not currently timed out.")
    else:
        await ctx.send("You don't have permission to use this command.")

BASE_URL = "https://valomind.com/api/mmr/{region}"

@client.command()
async def rank(ctx, region: str, player_tag: str):
    """
    Fetches the rank of a player based on their name, tagline, and region.
    Usage: !rank NA Jordan#8762
    """
    # Define a list of supported regions for validation
    supported_regions = ['NA', 'EU', 'KR', 'BR', 'AP']
    
    if region not in supported_regions:
        await ctx.send(f"Unsupported region. Supported regions are: {', '.join(supported_regions)}.")
        return

    try:
        # Split the player tag into name and tagline
        player_name, tagline = player_tag.split('#')

        # Construct the API URL with the region
        api_url = f"{BASE_URL.format(region=region)}/{player_name}/{tagline}"

        # Fetch data from the API
        response = requests.get(api_url)
        data = response.json()

        # Extract the required information
        rank = data['data']['currenttierpatched']
        rank_in_tier = data['data']['ranking_in_tier']
        mmr_change = data['data']['mmr_change_to_last_game']

        # Create an embed object with the specified color
        embed = discord.Embed(
            title=f"{player_name}#{tagline}'s Rank Information",
            color=0x2a2d30  # Set the color to the specified hexadecimal value
        )
        
        # Add fields to the embed
        embed.add_field(name="Current Rank", value=f"{rank} - {rank_in_tier}RR", inline=False)
        if mmr_change > 0:
            embed.add_field(name="MMR", value=f"Gained +{mmr_change}RR last game.", inline=False)
        else:
            embed.add_field(name="MMR", value=f"Lost {mmr_change}RR last game.", inline=False)

        # Send the embed message to the channel
        await ctx.send(embed=embed)

    except ValueError:
        # Handle the case where the user didn't input the correct format
        await ctx.send("Please use the correct format: !rank Region PlayerName#Tagline")
    except Exception as e:
        # Handle any other exceptions, such as API errors
        await ctx.send(f"An error occurred: {str(e)}")


# Dictionary to store invite tracking
invite_tracking = {}
member_invite_info = {}  # Store who invited each member

@client.command()
@is_whitelisted()
async def invited(ctx, member: discord.Member = None):
    """Shows information about how a member joined the server"""
    try:
        # If no member specified, use the command author
        member = member or ctx.author

        embed = discord.Embed(
            title="Member Join Information",
            color=0x2a2d30
        )

        # Add member's basic info
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name="Member",
            value=f"{member.mention} ({member.name})",
            inline=False
        )

        # Add join date
        join_time = int(member.joined_at.replace(tzinfo=timezone.utc).timestamp())
        embed.add_field(
            name="Joined Server",
            value=f"<t:{join_time}:F> (<t:{join_time}:R>)",
            inline=False
        )

        # Check if we have invite information for this member
        member_info = member_invite_info.get(str(member.id))
        
        if member_info and member_info['guild_id'] == ctx.guild.id:
            # We have stored invite information for this member
            inviter = ctx.guild.get_member(member_info['inviter_id'])
            if inviter:
                embed.add_field(
                    name="Invited By",
                    value=f"{inviter.mention} ({inviter.name})",
                    inline=True
                )
                embed.add_field(
                    name="Invite Code",
                    value=f"`{member_info['invite_code']}`",
                    inline=True
                )
                
                # Add when they were invited
                invite_time = int(member_info['join_time'])
                embed.add_field(
                    name="Invite Used",
                    value=f"<t:{invite_time}:F> (<t:{invite_time}:R>)",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Invited By",
                    value="Inviter no longer in server",
                    inline=True
                )
                embed.add_field(
                    name="Invite Code",
                    value=f"`{member_info['invite_code']}`",
                    inline=True
                )
        else:
            # Check invite_tracking as a fallback
            found_invite = False
            if ctx.guild.id in invite_tracking:
                for invite_code, invite_data in invite_tracking[ctx.guild.id].items():
                    if member.id in invite_data['members']:
                        found_invite = True
                        inviter = ctx.guild.get_member(invite_data['inviter'])
                        if inviter:
                            embed.add_field(
                                name="Invited By",
                                value=f"{inviter.mention} ({inviter.name})",
                                inline=True
                            )
                        else:
                            embed.add_field(
                                name="Invited By",
                                value="Inviter no longer in server",
                                inline=True
                            )
                        embed.add_field(
                            name="Invite Code",
                            value=f"`{invite_code}`",
                            inline=True
                        )
                        break
            
            if not found_invite:
                if member.guild_permissions.administrator:
                    embed.add_field(
                        name="Join Method",
                        value="Server Administrator",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Join Method",
                        value="Joined using the Vanity",
                        inline=False
                    )

        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

def save_invite_data():
    try:
        # Save invite tracking data
        with open('invite_tracking.json', 'w') as f:
            # Convert sets to lists for JSON serialization
            data_to_save = {}
            for guild_id, guild_data in invite_tracking.items():
                data_to_save[str(guild_id)] = {}
                for invite_code, invite_data in guild_data.items():
                    data_to_save[str(guild_id)][invite_code] = {
                        'uses': invite_data['uses'],
                        'members': list(invite_data['members']),
                        'inviter': invite_data['inviter']
                    }
            json.dump(data_to_save, f)
            
        # Save member invite info
        with open('member_invite_info.json', 'w') as f:
            json.dump(member_invite_info, f)
    except Exception as e:
        print(f"Error saving invite data: {e}")

def load_invite_data():
    try:
        # Load invite tracking data
        if os.path.exists('invite_tracking.json'):
            with open('invite_tracking.json', 'r') as f:
                data = json.load(f)
                # Convert lists back to sets
                for guild_id, guild_data in data.items():
                    invite_tracking[int(guild_id)] = {}
                    for invite_code, invite_data in guild_data.items():
                        invite_tracking[int(guild_id)][invite_code] = {
                            'uses': invite_data['uses'],
                            'members': set(invite_data['members']),
                            'inviter': invite_data['inviter']
                        }
                        
        # Load member invite info
        if os.path.exists('member_invite_info.json'):
            with open('member_invite_info.json', 'r') as f:
                global member_invite_info
                member_invite_info = json.load(f)
    except Exception as e:
        print(f"Error loading invite data: {e}")

@client.event
async def on_ready():
    print(f"{client.user.name} is logged in.")
    await update_status()
    
    # Load saved invite data
    load_invite_data()
    
    # Update invite tracking for each guild
    for guild in client.guilds:
        try:
            if guild.id not in invite_tracking:
                invite_tracking[guild.id] = {}
                
            invites = await guild.invites()
            for invite in invites:
                if invite.code not in invite_tracking[guild.id]:
                    invite_tracking[guild.id][invite.code] = {
                        'uses': invite.uses,
                        'members': set(),
                        'inviter': invite.inviter.id if invite.inviter else None
                    }
                else:
                    # Update uses count for existing invites
                    invite_tracking[guild.id][invite.code]['uses'] = invite.uses
            
            # Save the updated data
            save_invite_data()
        except discord.Forbidden:
            pass
    # Store initial invite counts for all guilds
    for guild in client.guilds:
        try:
            invites = await guild.invites()
            client.cached_invites = {invite.code: invite.uses for invite in invites}
        except discord.Forbidden:
            continue

@client.event
async def on_men(member):
    try:
        if member.guild.id not in invite_tracking:
            invite_tracking[member.guild.id] = {}
        
        # Get the current invite counts
        current_invites = await member.guild.invites()
        
        # Find which invite was used by comparing with our tracking
        used_invite = None
        for invite in current_invites:
            if invite.code not in invite_tracking[member.guild.id]:
                # This is a new invite that was just used
                invite_tracking[member.guild.id][invite.code] = {
                    'uses': invite.uses,
                    'members': {member.id},
                    'inviter': invite.inviter.id if invite.inviter else None
                }
                used_invite = invite
                break
            elif invite.uses > invite_tracking[member.guild.id][invite.code]['uses']:
                # This invite's use count increased, so it was used
                invite_tracking[member.guild.id][invite.code]['uses'] = invite.uses
                invite_tracking[member.guild.id][invite.code]['members'].add(member.id)
                used_invite = invite
                break
        
        # If we found the used invite, store the member's invite info
        if used_invite:
            member_invite_info[str(member.id)] = {
                'guild_id': member.guild.id,
                'invite_code': used_invite.code,
                'inviter_id': used_invite.inviter.id if used_invite.inviter else None,
                'join_time': datetime.datetime.now(timezone.utc).timestamp()
            }
            
            # Update our tracking for all current invites
            for invite in current_invites:
                if invite.code not in invite_tracking[member.guild.id]:
                    invite_tracking[member.guild.id][invite.code] = {
                        'uses': invite.uses,
                        'members': set(),
                        'inviter': invite.inviter.id if invite.inviter else None
                    }
                else:
                    invite_tracking[member.guild.id][invite.code]['uses'] = invite.uses
            
            # Save the updated data
            save_invite_data()
                
    except discord.Forbidden:
        pass

@client.event
async def on_member_remove(member):
    debug_antiraid(f"Member removed: {member.name} (ID: {member.id})")
    
    # Antiraid protection for mass kicks
    if antiraid_enabled and member.guild.owner_id != member.id:
        debug_antiraid(f"Antiraid enabled, checking for kicks...")
        try:
            # Check if this was actually a kick (not a leave)
            kick_found = False
            async for entry in member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=5):
                debug_antiraid(f"Checking audit entry: {entry.user.name} -> {entry.target.name if hasattr(entry.target, 'name') else 'Unknown'}")
                if entry.target.id == member.id and (time.time() - entry.created_at.timestamp()) < 5:
                    kick_found = True
                    debug_antiraid(f"Found recent kick entry: {entry.user.name} kicked {member.name}")
                    # Track the kick action
                    user_id = entry.user.id
                    if user_id not in user_action_timestamps:
                        user_action_timestamps[user_id] = {}
                    
                    if 'kicks' not in user_action_timestamps[user_id]:
                        user_action_timestamps[user_id]['kicks'] = []
                    
                    user_action_timestamps[user_id]['kicks'].append(time.time())
                    debug_antiraid(f"Added kick timestamp for {entry.user.name}. Total kicks: {len(user_action_timestamps[user_id]['kicks'])}")
                    
                    # Remove old timestamps (older than 4 seconds)
                    user_action_timestamps[user_id]['kicks'] = [
                        t for t in user_action_timestamps[user_id]['kicks'] 
                        if time.time() - t < 4
                    ]
                    debug_antiraid(f"After cleanup: {len(user_action_timestamps[user_id]['kicks'])} kicks in last 4 seconds")
                    
                    # Check if user is whitelisted
                    if user_id in antiraid_whitelist:
                        debug_antiraid(f"User {entry.user.name} is whitelisted, skipping ban")
                        break
                    
                    # If 2 or more kicks in 4 seconds, ban the user
                    if len(user_action_timestamps[user_id]['kicks']) >= 2:
                        debug_antiraid(f"BANNING {entry.user.name} for mass kicks!")
                        try:
                            await member.guild.ban(entry.user, reason="Antiraid: Mass kick detection")
                            embed = discord.Embed(
                                title="🛡️ Antiraid Protection",
                                description=f"**{entry.user.name}** has been banned for mass kicking members.",
                                color=0xff0000
                            )
                            embed.add_field(name="Action", value="Mass kick detection", inline=False)
                            embed.add_field(name="Kicks", value=f"{len(user_action_timestamps[user_id]['kicks'])} in 4 seconds", inline=False)
                            
                            # Send to antiraid logs channel if configured
                            logs_channel_id = antiraid_logs_channels.get(str(member.guild.id))
                            if logs_channel_id:
                                logs_channel = member.guild.get_channel(logs_channel_id)
                                if logs_channel and logs_channel.permissions_for(member.guild.me).send_messages:
                                    await logs_channel.send(embed=embed)
                                else:
                                    # Fallback to first available channel
                                    for channel in member.guild.text_channels:
                                        if channel.permissions_for(member.guild.me).send_messages:
                                            await channel.send(embed=embed)
                                            break
                            else:
                                # Send to first available channel
                                for channel in member.guild.text_channels:
                                    if channel.permissions_for(member.guild.me).send_messages:
                                        await channel.send(embed=embed)
                                        break
                        except Exception as e:
                            debug_antiraid(f"Error banning user: {e}")
                    break
            
            if not kick_found:
                debug_antiraid(f"No recent kick found for {member.name} - likely left voluntarily")
        except Exception as e:
            debug_antiraid(f"Error in kick detection: {e}")
    else:
        debug_antiraid(f"Antiraid disabled or owner kicked")
    
    # Original invite tracking functionality
    try:
        if member.guild.id in invite_tracking:
            # Remove the member from any invite they used
            for invite_data in invite_tracking[member.guild.id].values():
                if member.id in invite_data['members']:
                    invite_data['members'].remove(member.id)
            
            # Save the updated data
            save_invite_data()
    except Exception:
        pass
async def load_invite_logging_channels():
    try:
        with open('invite_logging_channels.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

async def save_invite_logging_channels(channels):
    with open('invite_logging_channels.json', 'w') as f:
        json.dump(channels, f, indent=4)

invite_logging_channels = {}

@client.command()
@commands.has_permissions(manage_guild=True)
@is_whitelisted()
async def invitelogger(ctx, channel: discord.TextChannel = None):
    """Set up invite logging for the server. If no channel is specified, it will show active invites and the current logging channel."""
    global invite_logging_channels
    
    try:
        # Load current channels
        invite_logging_channels = await load_invite_logging_channels()
        
        if channel is None:
            # Get current invites
            current_invites = await ctx.guild.invites()
            
            embed = discord.Embed(
                title="Server Invite Information",
                color=0x2a2d30
            )
            
            # Show current logging channel
            current_channel_id = invite_logging_channels.get(str(ctx.guild.id))
            if current_channel_id:
                log_channel = ctx.guild.get_channel(int(current_channel_id))
                if log_channel:
                    embed.add_field(
                        name="📝 Logging Channel",
                        value=f"Invite events are being logged in {log_channel.mention}",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="❌ Logging Channel",
                        value="The previously set logging channel no longer exists.",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="❌ Logging Channel",
                    value="No invite logging channel has been set up.",
                    inline=False
                )
            
            # Add active invites section
            if current_invites:
                active_invites = []
                for inv in current_invites:
                    # Create detailed invite info
                    invite_info = []
                    invite_info.append(f"• Code: {inv.code}")
                    invite_info.append(f"  Uses: {inv.uses}")
                    
                    if inv.max_uses:
                        invite_info.append(f"  Max Uses: {inv.max_uses}")
                    
                    if inv.inviter:
                        invite_info.append(f"  Created by: {inv.inviter.name}")
                    
                    if inv.channel:
                        invite_info.append(f"  Channel: #{inv.channel.name}")
                    
                    # Add expiration with proper datetime handling
                    if inv.expires_at:
                        # Convert to UTC and get timestamp
                        current_time = datetime.datetime.now(timezone.utc)
                        expire_time = inv.expires_at.replace(tzinfo=timezone.utc)
                        time_remaining = expire_time - current_time
                        
                        # Get Unix timestamp for Discord formatting
                        unix_timestamp = int(expire_time.timestamp())
                        
                        # Calculate total seconds for timedelta display
                        total_seconds = int(time_remaining.total_seconds())
                        
                        if total_seconds > 0:
                            # Format using Discord's timestamp for exact time on hover
                            invite_info.append(f"  Expires: <t:{unix_timestamp}:f> (<t:{unix_timestamp}:R>)")
                        else:
                            invite_info.append("  Expires: Expired")
                    else:
                        invite_info.append("  Expires: Never")
                    
                    active_invites.append("\n".join(invite_info))
                
                # Join all invite blocks with double newline for spacing
                active_invites_text = "\n\n".join(active_invites)
                
                if len(active_invites_text) <= 1024:
                    embed.add_field(
                        name=f"🔗 Active Invite Codes ({len(current_invites)})",
                        value=f"```{active_invites_text}```",
                        inline=False
                    )
                else:
                    # If too long, split into multiple fields
                    current_field = []
                    current_length = 0
                    field_count = 1
                    
                    for invite_block in active_invites:
                        if current_length + len(invite_block) + 2 > 1024:  # +2 for the newlines
                            # Add current field
                            embed.add_field(
                                name=f"🔗 Active Invite Codes - Part {field_count}",
                                value=f"```{chr(10).join(current_field)}```",
                                inline=False
                            )
                            field_count += 1
                            current_field = [invite_block]
                            current_length = len(invite_block)
                        else:
                            current_field.append(invite_block)
                            current_length += len(invite_block) + 2  # +2 for the newlines
                    
                    # Add remaining invites
                    if current_field:
                        embed.add_field(
                            name=f"🔗 Active Invite Codes - Part {field_count}",
                            value=f"```{chr(10).join(current_field)}```",
                            inline=False
                        )
            else:
                embed.add_field(
                    name="🔗 Active Invite Codes",
                    value="```No active invites```",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            return

        # Set new logging channel
        invite_logging_channels[str(ctx.guild.id)] = channel.id
        await save_invite_logging_channels(invite_logging_channels)
        
        embed = discord.Embed(
            description=f"✅ Successfully set invite logging channel to {channel.mention}",
            color=0x2a2d30
        )
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@client.event
async def on_invite_create(invite):
    """Event handler for when an invite is created"""
    try:
        # Load current channels
        invite_logging_channels = await load_invite_logging_channels()
        
        # Get logging channel
        channel_id = invite_logging_channels.get(str(invite.guild.id))
        if not channel_id:
            return
            
        channel = invite.guild.get_channel(int(channel_id))
        if not channel:
            return
            
        # Create embed
        embed = discord.Embed(
            title="📨 New Invite Created",
            color=0x2a2d30,
            timestamp=discord.utils.utcnow()
        )
        
        # Add invite details
        embed.add_field(name="Created By", value=f"{invite.inviter.mention} ({invite.inviter.name})", inline=False)
        embed.add_field(name="Channel", value=f"{invite.channel.mention} ({invite.channel.name})", inline=True)
        embed.add_field(name="Code", value=f"`{invite.code}`", inline=True)
        embed.add_field(name="Max Uses", value=f"`{'∞' if invite.max_uses == 0 else invite.max_uses}`", inline=True)
        
        if invite.expires_at:
            time_diff = invite.expires_at - discord.utils.utcnow()
            days = time_diff.days
            hours = time_diff.seconds // 3600
            minutes = (time_diff.seconds % 3600) // 60
            
            expiry_text = ""
            if days > 0:
                expiry_text += f"{days} days "
            if hours > 0:
                expiry_text += f"{hours} hours "
            if minutes > 0:
                expiry_text += f"{minutes} minutes"
            
            embed.add_field(name="Expires In", value=f"`{expiry_text.strip()}`", inline=True)
        else:
            embed.add_field(name="Expires", value="`Never`", inline=True)
            
        await channel.send(embed=embed)
        
    except Exception as e:
        print(f"Error in on_invite_create: {str(e)}")

@client.event
async def on_invite_delete(invite):
    """Event handler for when an invite is deleted"""
    try:
        # Load current channels
        invite_logging_channels = await load_invite_logging_channels()
        
        # Get logging channel
        channel_id = invite_logging_channels.get(str(invite.guild.id))
        if not channel_id:
            return
            
        channel = invite.guild.get_channel(int(channel_id))
        if not channel:
            return
            
        # Create embed
        embed = discord.Embed(
            title="🗑️ Invite Deleted",
            color=0x2a2d30,
            timestamp=discord.utils.utcnow()
        )
        
        # Add invite details
        if invite.inviter:
            embed.add_field(name="Created By", value=f"{invite.inviter.mention} ({invite.inviter.name})", inline=False)
        embed.add_field(name="Channel", value=f"{invite.channel.mention} ({invite.channel.name})", inline=True)
        embed.add_field(name="Code", value=f"`{invite.code}`", inline=True)
        embed.add_field(name="Uses", value=f"`{invite.uses}`", inline=True)
            
        await channel.send(embed=embed)
        
    except Exception as e:
        print(f"Error in on_invite_delete: {str(e)}")

async def update_status():
    total_members = sum(guild.member_count for guild in client.guilds)

    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{total_members} members"))

async def search_youtube_fallback(query):
    """Fallback search method using a different approach"""
    try:
        # Try using a different search method
        search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url) as response:
                if response.status == 200:
                    html = await response.text()
                    # Look for video IDs in the HTML
                    import re
                    video_ids = re.findall(r'"videoId":"([^"]+)"', html)
                    if video_ids:
                        return f"https://www.youtube.com/watch?v={video_ids[0]}"
    except Exception as e:
        print(f"Fallback search failed: {e}")
    return None

async def search_youtube_video(query):
    """Main search function with fallback"""
    try:
        # Primary search method
        videos_search = VideosSearch(query, limit=1)
        search_results = videos_search.result()
        
        if search_results and 'result' in search_results and len(search_results['result']) > 0:
            return search_results['result'][0]['link']
        
        # If primary method fails, try fallback
        fallback_url = await search_youtube_fallback(query)
        if fallback_url:
            return fallback_url
            
    except Exception as e:
        print(f"Primary search failed: {e}")
        # Try fallback
        fallback_url = await search_youtube_fallback(query)
        if fallback_url:
            return fallback_url
    
    return None

@client.command()
@is_whitelisted()
async def invites(ctx, member: discord.Member = None):
    try:
        # If no member specified, use the command author
        member = member or ctx.author
        
        # Initialize tracking for this guild if it doesn't exist
        if ctx.guild.id not in invite_tracking:
            invite_tracking[ctx.guild.id] = {}
        
        # Get current invites and update tracking
        current_invites = await ctx.guild.invites()
        member_invites = [inv for inv in current_invites if inv.inviter and inv.inviter.id == member.id]
        
        # Update tracking for any new invites
        for invite in current_invites:
            if invite.code not in invite_tracking[ctx.guild.id]:
                invite_tracking[ctx.guild.id][invite.code] = {
                    'uses': invite.uses,
                    'members': set(),
                    'inviter': invite.inviter.id if invite.inviter else None
                }
        
        # Calculate statistics
        total_uses = 0
        current_members = []
        left_members = 0
        
        # For each of the member's invites
        for invite in member_invites:
            if invite.code in invite_tracking[ctx.guild.id]:
                invite_data = invite_tracking[ctx.guild.id][invite.code]
                total_uses += invite.uses
                
                # Get current members who used this invite
                for member_id in invite_data['members']:
                    member_obj = ctx.guild.get_member(member_id)
                    if member_obj and member_obj not in current_members:
                        current_members.append(member_obj)
                
                # Calculate left members
                if invite.uses > len(invite_data['members']):
                    left_members += invite.uses - len(invite_data['members'])
        
        # Create embed
        embed = discord.Embed(
            title=f"Invite Statistics for {member.display_name}",
            color=0x2a2d30
        )
        
        # Add member's avatar
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Add statistics
        embed.add_field(
            name="Active Invites",
            value=f"```{len(member_invites)}```",
            inline=True
        )
        embed.add_field(
            name="Total Invited",
            value=f"```{total_uses}```",
            inline=True
        )
        
        # Add member statistics
        embed.add_field(
            name="Member Status",
            value=f"```\nStill in server: {len(current_members)}\nLeft server: {left_members}\nTotal invited: {total_uses}\n```",
            inline=False
        )
        
        # List current members
        if current_members:
            member_list = []
            for m in current_members[:10]:
                member_list.append(f"• {m.name}")
            
            if len(current_members) > 10:
                member_list.append(f"\n+ {len(current_members) - 10} more...")
            
            embed.add_field(
                name="Members You Invited (Still Here)",
                value=f"```{chr(10).join(member_list)}```",
                inline=False
            )
        

        
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to view invites.")
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in invite command:\n{error_details}")
        await ctx.send(f"❌ An error occurred: {str(e)}")


@client.command(name="alias")
@is_whitelisted()
@commands.has_guild_permissions(administrator=True)
async def alias_command(ctx, original_command: str = None, *alias_parts):
    """Create or update a server-specific alias. Usage: `.alias role r`"""
    if original_command is None or not alias_parts:
        await ctx.send("❌  Usage: `.alias <existing_command> <alias>`")
        return

    original_command = original_command.lower()
    new_alias = " ".join(alias_parts).strip().lower()

    # Check existence of original command
    if client.get_command(original_command) is None:
        await ctx.send(f"❌  Command `{original_command}` does not exist.")
        return

    # Prevent collision with existing commands (only if the alias is a single word)
    if len(alias_parts) == 1 and client.get_command(new_alias):
        await ctx.send(f"❌  `{new_alias}` is already an existing command name.")
        return

    guild_id = str(ctx.guild.id)
    guild_aliases.setdefault(guild_id, {})[new_alias] = original_command
    save_aliases()

    await ctx.send(f"✅  Alias `{new_alias}` → `{original_command}` has been set for this server.")

@client.command(name="checkalias")
@is_whitelisted()
@commands.has_guild_permissions(administrator=True)
async def checkalias(ctx):
    """List all aliases set up for this server."""
    guild_id = str(ctx.guild.id)
    aliases = guild_aliases.get(guild_id, {})
    if not aliases:
        await ctx.send("❌ No aliases are set up for this server.")
        return
    lines = [f"`{alias}` → `{cmd}`" for alias, cmd in aliases.items()]
    embed = discord.Embed(title="Server Aliases", description="\n".join(lines), color=0x2a2d30)
    await ctx.send(embed=embed)

@client.command(name="removealias")
@is_whitelisted()
@commands.has_guild_permissions(administrator=True)
async def removealias(ctx, *, alias_or_command: str = None):
    """Remove an alias by its alias name or the original command name."""
    if not alias_or_command:
        await ctx.send("❌ Usage: `.removealias <alias or command name>`")
        return
    guild_id = str(ctx.guild.id)
    aliases = guild_aliases.get(guild_id, {})
    alias_or_command = alias_or_command.lower().strip()
    # Find all aliases to remove (by alias or by original command)
    to_remove = [alias for alias, cmd in aliases.items()
                 if alias == alias_or_command or cmd == alias_or_command]
    if not to_remove:
        await ctx.send(f"❌ No alias found for `{alias_or_command}` in this server.")
        return
    for alias in to_remove:
        del aliases[alias]
    save_aliases()
    await ctx.send(f"✅ Removed alias(es) for `{alias_or_command}`.")

from dotenv import load_dotenv
import os

load_dotenv()  # reads the .env file

token = os.getenv('DISCORD_BOT_TOKEN')
if not token:
    raise ValueError("No DISCORD_BOT_TOKEN found in environment variables or .env file.")

# Verification System
def generate_verification_code():
    """Generate a random 6-character verification code with letters and numbers"""
    chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return ''.join(random.choice(chars) for _ in range(6))

class VerifyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Verify",
            style=discord.ButtonStyle.green,
            custom_id="verify_button"
        )

    async def callback(self, interaction: discord.Interaction):
        # Generate a random verification code
        verification_code = generate_verification_code()
        
        # Create the modal
        modal = VerifyModal(verification_code)
        await interaction.response.send_modal(modal)

class VerifyModal(discord.ui.Modal):
    def __init__(self, verification_code: str):
        super().__init__(title="Verification Check")
        self.verification_code = verification_code
        
        self.code_input = discord.ui.TextInput(
            label=f"Enter the code: {verification_code}",
            placeholder="Type the code exactly as shown",
            required=True,
            max_length=10
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: discord.Interaction):
        if self.code_input.value.upper() == self.verification_code:
            # Get the verification role
            guild_id = str(interaction.guild_id)
            guild_settings = settings.get(guild_id, {})
            verification_role_id = guild_settings.get("verification_role_id")
            
            if verification_role_id:
                role = interaction.guild.get_role(verification_role_id)
                if role:
                    try:
                        await interaction.user.add_roles(role)
                        embed = discord.Embed(
                            title="✅ Verification Successful",
                            description="You have been successfully verified! You now have access to the server.",
                            color=discord.Color.green()
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                    except discord.Forbidden:
                        await interaction.response.send_message("❌ I don't have permission to assign roles.", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Verification role not found. Please contact an administrator.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Verification role not set up. Please contact an administrator.", ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ Verification Failed",
                description="The code you entered is incorrect. Please try again.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VerifyButton())

@client.command()
@commands.has_permissions(administrator=True)
async def verify(ctx):
    """Sends the verification message with a button"""
    embed = discord.Embed(
        title="🔒 Verification Required!",
        description="To access Stock Robux, you need to pass verification first.\n\n➜ Click on the Verify button below to start.",
        color=0x2b2d31
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1232291016128729118/1394433866013606011/Stock_Robux.png?ex=6876cb3c&is=687579bc&hm=a8b319b06f6318dcb10bdcf68a4b7788dac4ea3ac2688f64b546c062b54b5622&")
    await ctx.send(embed=embed, view=VerifyView())

@client.command()
@commands.has_permissions(administrator=True)
async def verifyrole(ctx, role_id: int = None):
    """Sets the role to be given upon successful verification"""
    if role_id is None:
        embed = discord.Embed(
            title="❌ Error",
            description="Please provide a role ID.\nUsage: `.verifyrole role_id`",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    role = ctx.guild.get_role(role_id)
    if not role:
        embed = discord.Embed(
            title="❌ Error",
            description="Could not find a role with that ID.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    guild_id = str(ctx.guild.id)
    if guild_id not in settings:
        settings[guild_id] = {}
    
    settings[guild_id]["verification_role_id"] = role_id
    with open("welcome_settings.json", "w") as file:
        json.dump(settings, file)
    
    embed = discord.Embed(
        title="✅ Verification Role Set",
        description=f"The verification role has been set to {role.mention} (`{role_id}`)",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@client.command()
@is_whitelisted()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, duration: str = None):
    """
    Set slowmode for the current channel.
    Usage: .slowmode <duration/off>
    Example: .slowmode 5s (5 seconds)
             .slowmode 1m (1 minute)
             .slowmode 2h (2 hours)
             .slowmode off (disable slowmode)
    """
    if duration is None:
        await ctx.send("Please specify a duration (e.g., 5s, 1m, 2h) or 'off' to disable slowmode.")
        return

    if duration.lower() == 'off':
        await ctx.channel.edit(slowmode_delay=0)
        await ctx.send(f"✅ Slowmode has been disabled in {ctx.channel.mention}")
        return

    # Convert duration string to seconds
    try:
        unit = duration[-1].lower()
        value = int(duration[:-1])
        
        if unit == 's':
            seconds = value
        elif unit == 'm':
            seconds = value * 60
        elif unit == 'h':
            seconds = value * 3600
        else:
            await ctx.send("Invalid duration format. Use 's' for seconds, 'm' for minutes, or 'h' for hours.")
            return

        # Discord's maximum slowmode is 6 hours (21600 seconds)
        if seconds > 21600:
            await ctx.send("❌ Slowmode cannot be set to more than 6 hours.")
            return
        
        if seconds < 0:
            await ctx.send("❌ Slowmode duration cannot be negative.")
            return

        await ctx.channel.edit(slowmode_delay=seconds)
        
        # Format duration for display
        if seconds >= 3600:
            formatted_time = f"{seconds // 3600} hour(s)"
        elif seconds >= 60:
            formatted_time = f"{seconds // 60} minute(s)"
        else:
            formatted_time = f"{seconds} second(s)"
            
        await ctx.send(f"✅ Slowmode set to {formatted_time} in {ctx.channel.mention}")

    except ValueError:
        await ctx.send("❌ Invalid duration format. Please use a number followed by 's', 'm', or 'h' (e.g., 5s, 1m, 2h)")
        return

@slowmode.error
async def slowmode_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need the 'Manage Channels' permission to use this command.")
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")



client.run(token)

