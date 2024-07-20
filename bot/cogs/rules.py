import asyncio
import logging
import re
from math import ceil

from nextcord import ButtonStyle, Embed, SelectOption, SlashOption, slash_command, ui
from nextcord.ext.commands import Cog

from config.domain import (
    EMPTY_STRING,
    ID,
    URL,
    ChannelName,
    Color,
    Permissions,
    RoleName,
)
from db_integration import db_functions as db
from utils import util_functions as uf

logger = logging.getLogger(__name__)

RULES_LIST = [
    "1. Respect all other members.",
    "2. Keep conversations friendly and calm.",
    "3. No impersonating a moderator, or any others.",
    "4. No inappropriate names or avatars.",
    "5. No hate speech or slurs of any kind.",
    "6. No advertising or spam.",
    "7. No links to or posting NSFW content, including pornography, "
    "gore and sexualised lolis.",
    "8. Listen to moderators.",
    "9. Do not appeal mod decisions in public channels - "
    f"open a ticket in <#{ID.TICKETS}>.",
    "10. No attacking race, religion, sexual orientation, gender identity or "
    "nationality.",
    f"11. Keep bot commands in <#{ID.BOT_SPAM}> unless it's relevant to the "
    "current conversation.",
    "12. Don't ping clan roles, @here or @everyone",
]

GENERAL_INFO = (
    f"Talking in the server awards XP - you need Level 3 to access <#{ID.GIVEAWAYS}>. "
    "Enforcement of the rules is always at the moderators' discretion. Repeated "
    "infractions within a 30 day period lead to automatic action:\n"
    "2 Warns = Muted for a day\n"
    "3 Warns = Muted for 3 days\n"
    "4 Warns = Banned for 7 days\n"
    "5 Warns = Permanent ban"
)

DELIMITERS = {"clan": "Clans", "opt-in": "Opt-in", "color": "Colors"}

MAX_SELECT_MENU_SIZE = 24


class Rules(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.kick_inactives.start()

    def cog_unload(self):
        self.kick_inactives.cancel()

    @slash_command(
        description="Commands for setting up and editing "
        f"the #{ChannelName.RULES} channel",
        default_member_permissions=Permissions.MODS_ONLY,
    )
    async def rule(self, interaction):
        pass

    @rule.subcommand(description=f"Add all posts to the #{ChannelName.RULES} channel")
    async def create(
        self,
        interaction,
        delay: float = SlashOption(
            description="Delay in seconds between each post", default=0.1
        ),
    ):
        logger.info("Creating rules channel")
        vie = interaction.guild
        rules_ch = uf.get_channel(vie, ChannelName.RULES)
        await interaction.send(
            f"Creation process starting in {rules_ch.mention}", ephemeral=True
        )
        await rules_ch.send(URL.GITHUB_STATIC + "/images/Ginny_Welcome.png")
        await asyncio.sleep(delay)

        rules_embed = Embed(color=Color.VIE_PURPLE)
        rules_embed.title = r"__RULES__"
        rules_embed.description = f"\n{EMPTY_STRING}\n".join(RULES_LIST)
        await rules_ch.send(embed=rules_embed)

        info_embed = Embed(color=Color.VIE_PURPLE)
        info_embed.title = r"__GENERAL INFO__"
        info_embed.description = GENERAL_INFO
        await rules_ch.send(embed=info_embed)
        await asyncio.sleep(delay)

        alli_embed = Embed(color=Color.VIE_PURPLE)
        alli_embed.title = "Step 1 - How did you join us?"
        alli_embed.description = (
            "If you're part of a clan in the Warframe alliance, use the 'Warframe' "
            "button. If you're coming from anywhere else, use the 'Elsewhere' button."
        )

        view = StepOneView(guild=vie)
        alli_msg = await rules_ch.send(
            "__***Please carefully read the posts below "
            "or you will not gain full access to the server***__",
            embed=alli_embed,
            view=view,
        )
        await db.log_buttons(self.bot, view, rules_ch.id, alli_msg.id)

        await asyncio.sleep(delay)

        clan_embed = Embed(color=Color.VIE_PURPLE)
        clan_embed.title = (
            "Step 2 - If you're part of the Warframe alliance, "
            "use the menu below to select your clan."
        )
        view = RoleChoiceView(guild=vie, role_type="clan")
        clan_msg = await rules_ch.send(embed=clan_embed, view=view)
        await db.log_buttons(
            self.bot, view, rules_ch.id, clan_msg.id, {"role_type": "clan"}
        )
        await asyncio.sleep(delay)

        opt_embed = Embed(color=Color.VIE_PURPLE)
        opt_embed.title = (
            "Step 3 - Use the menu below if you want to be notified for things like "
            "updates, events and giveaways, or to access certain opt-in channels."
        )
        view = OptInView(guild=vie)
        opt_msg = await rules_ch.send(embed=opt_embed, view=view)
        await db.log_buttons(self.bot, view, rules_ch.id, opt_msg.id)

        color_embed = Embed(color=Color.VIE_PURPLE)
        color_embed.title = (
            "Step 4 - Use the menu below if you want a different display color "
            "than the one provided by your clan"
        )
        view = RoleChoiceView(guild=vie, role_type="color")
        color_msg = await rules_ch.send(embed=color_embed, view=view)
        await db.log_buttons(
            self.bot, view, rules_ch.id, color_msg.id, {"role_type": "color"}
        )
        await asyncio.sleep(delay)

        general = uf.get_channel(vie, "general")
        await rules_ch.send(
            "You should now have access to all necessary channels in the server!\n"
            f"Why not pop over to {general.mention} and say hi? "
            "You probably have a few welcomes waiting already."
        )

    @rule.subcommand(description="Add a new rule to the post")
    async def add(
        self, interaction, text: str = SlashOption(description="The text of the rule")
    ):
        logger.info("Adding rule")
        rules_ch = uf.get_channel(interaction.guild, ChannelName.RULES)
        rules_msg = await rules_ch.fetch_message(ID.RULES_MESSAGE)
        embed = rules_msg.embeds[0]
        rules = re.split(rf"\n{EMPTY_STRING}\n", embed.description)
        rules = [re.sub(r"^\d+\. ", "", rule) for rule in rules]

        if re.match(r"^\d+$", text[-1]):
            text, number = " ".join(text[:-1]), int(text[-1])
            if number > len(rules) + 1 or number < 1:
                number = len(rules) + 1
        else:
            text, number = " ".join(text), len(rules) + 1

        rules.insert(number - 1, text)
        rules = [str(rules.index(rule) + 1) + ". " + rule for rule in rules]
        embed.description = f"\n{EMPTY_STRING}\n".join(rules)
        await rules_msg.edit(embed=embed)
        await interaction.send("Rule successfully added")

    @rule.subcommand(description="Removes a rule from the post")
    async def remove(
        self,
        interaction,
        number: int = SlashOption(
            description="Number of the rule to remove", min_value=1
        ),
    ):
        logger.info("Removing rule")
        rules_ch = uf.get_channel(interaction.guild, ChannelName.RULES)
        rules_msg = await rules_ch.fetch_message(ID.RULES_MESSAGE)
        embed = rules_msg.embeds[0]
        rules = re.split(rf"\n{EMPTY_STRING}\n", embed.description)
        if number > len(rules):
            logger.warning(f"No rule with number {number}")
            await interaction.send("No rule with that number.", ephemeral=True)
            return

        rules = [re.sub(r"^\d+\. ", "", rule) for rule in rules]
        rules.pop(number - 1)
        rules = [str(rules.index(rule) + 1) + ". " + rule for rule in rules]
        embed.description = f"\n{EMPTY_STRING}\n".join(rules)
        await rules_msg.edit(embed=embed)
        await interaction.send("Rule successfully removed", ephemeral=True)

    @rule.subcommand(description="Edit a rule")
    async def edit(
        self,
        interaction,
        number: int = SlashOption(
            description="Number of the rule to edit", min_value=1
        ),
        new_text=SlashOption(description="New text of the rule"),
    ):
        rules_ch = uf.get_channel(interaction.guild, ChannelName.RULES)
        rules_msg = await rules_ch.fetch_message(ID.RULES_MESSAGE)
        embed = rules_msg.embeds[0]
        rules = re.split(rf"\n{EMPTY_STRING}\n", embed.description)

        if number > len(rules):
            await interaction.send("No rule with that number", ephemeral=True)
            return

        rules[number - 1] = f"{number}. {new_text}"
        embed.description = f"\n{EMPTY_STRING}\n".join(rules)

        await rules_msg.edit(embed=embed)
        await interaction.send("Rule successfully edited", ephemeral=True)

    @uf.delayed_loop(hours=8)
    async def kick_inactives(self):
        logger.info("Checking for inactive members")
        try:
            guild = await self.bot.fetch_guild(ID.GUILD)
        except Exception:
            logger.exception("Could not fetch guild")
            return

        async for member in guild.fetch_members():
            if (
                not member.bot
                and uf.get_role(member.guild, "Alliance") not in member.roles
                and (uf.get_role(member.guild, "Community") not in member.roles)
            ):
                time = uf.utcnow() - member.joined_at
                if time.days >= 30:  # noqa: PLR2004
                    discriminator = (
                        f"#{member.discriminator}"
                        if member.discriminator != "0"
                        else ""
                    )
                    try:
                        await member.send(
                            "Hi! You have been automatically kicked from the Vie for "
                            "the Void Discord as you have failed to read our rules and "
                            "unlock the full server within 30 days. If this was "
                            "an accident, please feel free to join us again!"
                            f"\n{EMPTY_STRING}\n{URL.INVITE}"
                        )
                    except Exception:
                        logger.exception(
                            f"Failed to send kick DM to {member.name}{discriminator}",
                        )

                    try:
                        maint = await self.bot.fetch_channel(ID.ERROR_CHANNEL)
                        await maint.send(
                            f"{member.name}{discriminator} has been kicked "
                            "due to inactivity."
                        )
                    except Exception:
                        logger.exception("Error channel not found")

                    try:
                        await member.kick()
                    except Exception:
                        logger.exception(
                            f"{member.name}{discriminator} couldn't be kicked",
                        )


class StepOneView(ui.View):
    def __init__(self, **params):
        super().__init__(timeout=None)
        guild = params["guild"]
        self.add_item(self.WarframeButton(guild))
        self.add_item(self.CommunityButton(guild))

    class WarframeButton(ui.Button):
        def __init__(self, guild):
            super().__init__(
                label="Warframe",
                style=ButtonStyle.blurple,
                emoji=uf.get_emoji(guild, "Alli"),
            )

        async def callback(self, interaction):
            alli = uf.get_role(interaction.guild, "Alliance")
            comm = uf.get_role(interaction.guild, "Community")

            await interaction.user.remove_roles(comm)
            await interaction.user.add_roles(alli)

    class CommunityButton(ui.Button):
        def __init__(self, guild):
            super().__init__(
                label="Elsewhere",
                style=ButtonStyle.blurple,
                emoji=uf.get_emoji(guild, "BlobWave"),
            )

        async def callback(self, interaction):
            await interaction.response.defer()

            alli = uf.get_role(interaction.guild, "Alliance")
            comm = uf.get_role(interaction.guild, "Community")
            await interaction.user.remove_roles(alli)
            await interaction.user.add_roles(comm)

            all_clan_roles = uf.get_roles_by_type(interaction.guild, DELIMITERS["clan"])
            await interaction.user.remove_roles(*all_clan_roles)


class RoleChoiceView(ui.View):
    def __init__(self, **params):
        super().__init__(timeout=None)
        self.choice = None
        guild = params["guild"]
        role_type = params.get("role_type", "clan")
        type_delimiter = DELIMITERS[role_type]
        all_roles = uf.get_roles_by_type(guild, type_delimiter)
        all_roles.sort(key=uf.role_prio)
        num_groups = ceil(len(all_roles) / MAX_SELECT_MENU_SIZE)
        group_size = ceil(len(all_roles) / num_groups)
        groups = [
            all_roles[(group_size * i) : (group_size * (i + 1))]
            for i in range(num_groups)
        ]
        for idx, group in enumerate(groups):
            self.add_item(self.RoleSelect(role_type, group, idx, num_groups))
        self.add_item(self.RoleConfirm(role_type))

    class RoleSelect(ui.Select):
        def __init__(self, role_type, roles, idx, total):
            text = f"Select your {role_type}"
            if total > 1:
                text += f" ({idx + 1}/{total})"
            super().__init__(placeholder=text, min_values=0)
            self.options = [
                SelectOption(
                    description=RoleName.descriptions().get(role.name, None),
                    label=role.name,
                )
                for role in roles
            ]
            self.options.append(SelectOption(label="None"))

        async def callback(self, interaction):  # noqa: ARG002
            self.view.choice = self.values[0] if self.values else None

    class RoleConfirm(ui.Button):
        def __init__(self, role_type):
            self.role_type = role_type
            super().__init__(style=ButtonStyle.blurple, label=f"Choose {role_type}")

        async def callback(self, interaction):
            await interaction.response.defer()
            if self.role_type == "clan" and self.view.choice != "None":
                alli = uf.get_role(interaction.guild, "Alliance")
                if alli not in interaction.user.roles:
                    await interaction.send(
                        "Please confirm you're part of the Warframe alliance in Step 1 "
                        "before choosing a clan",
                        ephemeral=True,
                    )
                    return

            all_roles_of_type = uf.get_roles_by_type(
                interaction.guild, DELIMITERS[self.role_type]
            )
            await interaction.user.remove_roles(*all_roles_of_type)
            if self.view.choice != "None":
                role = uf.get_role(interaction.guild, self.view.choice)
                await interaction.user.add_roles(role)


class OptInView(ui.View):
    def __init__(self, **params):
        guild = params["guild"]
        super().__init__(timeout=None)
        opt_in_roles = uf.get_roles_by_type(guild, DELIMITERS["opt-in"])
        groups = [
            opt_in_roles[i : i + MAX_SELECT_MENU_SIZE]
            for i in range(0, len(opt_in_roles), MAX_SELECT_MENU_SIZE)
        ]
        self.selected_roles = [[]] * len(groups)
        for index, group in enumerate(groups):
            self.add_item(self.OptInSelect(index, group))

    class OptInSelect(ui.Select):
        def __init__(self, index, roles):
            roles.sort(key=uf.role_prio)

            super().__init__(
                options=[
                    SelectOption(
                        label=role.name,
                        description=RoleName.descriptions().get(role.name, None),
                    )
                    for role in roles
                ],
                min_values=0,
                max_values=len(roles),
            )
            self.index = index

        async def callback(self, interaction):  # noqa: ARG002
            self.view.selected_roles[self.index] = self.values

    @ui.button(label="Choose selected roles", style=ButtonStyle.blurple, row=4)
    async def choose_roles(self, button, interaction):  # noqa: ARG002
        for role_list in self.selected_roles:
            for role_name in role_list:
                role = uf.get_role(interaction.guild, role_name)
                if role:
                    await interaction.user.add_roles(role)

    @ui.button(label="Remove selected roles", style=ButtonStyle.red, row=4)
    async def remove_roles(self, button, interaction):  # noqa: ARG002
        for role_list in self.selected_roles:
            for role_name in role_list:
                role = uf.get_role(interaction.guild, role_name)
                if role:
                    await interaction.user.remove_roles(role)


def setup(bot):
    bot.add_cog(Rules(bot))
