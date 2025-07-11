"""Automatic responses to messages matching a pattern."""

import asyncio
import random
import re
from collections.abc import Callable
from dataclasses import dataclass

import requests
from nextcord import File, Message

from cogs.awards import Award, give_award
from domain import ID, URL, ChannelName
from utils import util_functions as uf
from utils import warframe as wf


@dataclass(kw_only=True)
class RegexResponse:
    """Wrapper class for automatic response parameters."""

    trigger: str
    response: Callable | str
    flags: re.RegexFlag = re.MULTILINE | re.IGNORECASE
    prio: bool = False
    accepts: Callable = lambda x: True  # noqa: ARG005


regex_responses: list[RegexResponse] = []


async def cough_resp(message: Message) -> None:
    await message.channel.send(":mask:")
    await message.channel.send("Wear a mask!")


regex_responses.append(
    RegexResponse(trigger=r"\**(cough *){2,}\**", response=cough_resp),
)


async def ping_resp(message: Message) -> None:
    custom_responses = {
        ID.DARKNESS: URL.GITHUB_STATIC + "/images/darkness.jpg",
        ID.AIRU: URL.GITHUB_STATIC + "/images/airu.gif",
    }

    if message.author.id in custom_responses:
        await message.channel.send(custom_responses[message.author.id])
    else:
        emoji = uf.get_emoji("Pingsock")
        if emoji is not None:
            await message.channel.send(emoji)
        await message.channel.send(f"{message.author.mention}")


regex_responses.append(
    RegexResponse(trigger="^" + uf.id_to_mention(ID.BOT) + "$", response=ping_resp),
)


async def uwu_resp(message: Message) -> None:
    msg = message.content
    whitelist = [
        r":[^ ]*(o|u|0|O|U)[wvWV](o|u|0|O|U)[^ ]*:",
        "lenovo",
        "coworker",
        "kosovo",
        "provo[ck]",
        "uvula",
    ]

    for word in whitelist:
        if re.search(word, msg, re.IGNORECASE) is not None:
            return

    n = len(re.findall("[rRlL]", msg))
    if n > 4:  # noqa: PLR2004
        txt = re.sub("[rRlL]", "w", msg)
        await message.channel.send(txt)
    elif random.randint(1, 10) == 7:  # noqa: PLR2004
        txt = (
            "I'll let you off with just a warning this time "
            "but I'd better not see you doing it again."
        )
        await message.channel.send(txt)
    elif random.randint(1, 2) == 1:
        warning_video = File(URL.LOCAL_STATIC + "/videos/warning.mp4")
        await message.channel.send(file=warning_video)
    else:
        await message.channel.send(URL.GITHUB_STATIC + "/images/uwu.png")


regex_responses.append(
    RegexResponse(trigger=r"^[^\/]*(o|u|0)[wv]\1.*$", response=uwu_resp),
)


async def nephew_resp(message: Message) -> None:
    if message.content == "||nephew||":
        await message.channel.send("||delet this||")
    else:
        await message.channel.send("delet this")


regex_responses.append(RegexResponse(trigger=r"^\|*nephew\|*$", response=nephew_resp))


async def kenobi_resp(message: Message) -> None:
    if random.randint(1, 2) == 1:
        await message.channel.send("General " + message.author.mention)
    else:
        await message.channel.send(URL.GITHUB_STATIC + "/images/kenobi.png")


regex_responses.append(RegexResponse(trigger="hello there", response=kenobi_resp))


async def bell_resp(message: Message) -> None:
    await message.channel.send(URL.GITHUB_STATIC + "/images/bell.gif")


regex_responses.append(RegexResponse(trigger="ringing my bell", response=bell_resp))


async def no_u_resp(message: Message) -> None:
    await message.channel.send(URL.GITHUB_STATIC + "/images/no_u.png")


regex_responses.append(RegexResponse(trigger="^no u$", response=no_u_resp))


async def one_of_us_resp(message: Message) -> None:
    await message.channel.send("One of us!")


regex_responses.append(
    RegexResponse(trigger=r"^\**(one of us(!| |,)*)+\**$", response=one_of_us_resp),
)


async def society_resp(message: Message) -> None:
    await message.channel.send("Bottom Text")


regex_responses.append(
    RegexResponse(trigger="^.{0,5}We live in a society.{0,5}$", response=society_resp),
)


async def deep_one_resp(message: Message) -> None:
    await message.channel.send(
        "blub blub blub blub blub blub blub blub blub blub blub blub blub blub blub",
    )


regex_responses.append(
    RegexResponse(trigger="^if I (were|was) a deep one", response=deep_one_resp),
)


async def sixtynine_resp(message: Message) -> None:
    await message.add_reaction("🇳")
    await message.add_reaction("🇮")
    await message.add_reaction("🇨")
    await message.add_reaction("🇪")


regex_responses.append(
    RegexResponse(
        trigger=r"^[^\/<]*69(([^1][^1]).*|[^1].|.[^1]|.?)$",
        response=sixtynine_resp,
    ),
)


async def fourtwenty_resp(message: Message) -> None:
    await message.add_reaction("🔥")
    await message.add_reaction("🇧")
    await message.add_reaction("🇱")
    await message.add_reaction("🇦")
    await message.add_reaction("🇿")
    await message.add_reaction("🇪")
    await message.add_reaction("🇮")
    await message.add_reaction("🇹")


regex_responses.append(RegexResponse(trigger=r"^[^\/<]*420", response=fourtwenty_resp))


async def woop_resp(message: Message) -> None:
    await message.channel.send("That's the sound of da police!")


regex_responses.append(RegexResponse(trigger=r"^woop woop[\.!]*$", response=woop_resp))


async def paragon_resp(message: Message) -> None:
    await message.channel.send("Fuck Epic!")


regex_responses.append(RegexResponse(trigger="paragon", response=paragon_resp))


async def bruh_resp(message: Message) -> None:
    await message.add_reaction("🅱️")
    await message.add_reaction("🇷")
    await message.add_reaction("🇺")
    await message.add_reaction("🇭")


regex_responses.append(RegexResponse(trigger=r"^\W*bruh\W*$", response=bruh_resp))


async def hans_resp(message: Message) -> None:
    await message.channel.send("Get ze Flammenwerfer!")


regex_responses.append(RegexResponse(trigger=r"^hans\W*$", response=hans_resp))


async def loli_resp(message: Message) -> None:
    glare = uf.get_emoji("BlobGlare")
    if glare is not None:
        await message.add_reaction(glare)
    await message.channel.send(
        "https://cdn.discordapp.com/attachments/413861431906402334/731636158223614113/image0-27.jpg",
    )
    if re.search("loli", message.content, re.IGNORECASE) is None:
        await message.channel.send(f"Fuck off, {message.author.mention}")


regex_responses.append(
    RegexResponse(
        trigger=r"(^|\W)[LlI|][Oo0][LlI|][Ii]",
        response=loli_resp,
        flags=re.MULTILINE,
        accepts=lambda msg: msg.author.id != ID.JORM and "http" not in msg.content,
    ),
)


async def dont_at_me_resp(message: Message) -> None:
    await message.channel.send(f"{message.author.mention}")


regex_responses.append(
    RegexResponse(trigger="do[ ]?n[o ']?t (@|at) me", response=dont_at_me_resp),
)


async def america_resp(message: Message) -> None:
    await message.channel.send("Fuck yeah!")


regex_responses.append(
    RegexResponse(trigger=r"^\W*a?'?m(e|u)rica\W*$", response=america_resp),
)


async def mod_resp(message: Message) -> None:
    mod_names = re.findall(r"(?<=\[)[a-zA-Z ']+(?=\])", message.content)
    for mod_name in mod_names:
        if mod_name.lower() in wf.mod_list:
            await message.channel.send(wf.mod_list[mod_name.lower()])


regex_responses.append(RegexResponse(trigger=r"\[.*\]", response=mod_resp))


async def x_is_x_resp(message: Message) -> None:
    await message.channel.send(URL.GITHUB_STATIC + "/images/x%20is%20x.png")


regex_responses.append(
    RegexResponse(
        trigger=r"^(.* )?(\w+) (is|are) \2(\W.{0,5})?$",
        response=x_is_x_resp,
    ),
)


async def tree_fiddy_resp(message: Message) -> None:
    await message.add_reaction("🐍")


regex_responses.append(RegexResponse(trigger="tree fiddy", response=tree_fiddy_resp))


async def ass_testing_resp(message: Message) -> None:
    await message.add_reaction("🍑")


regex_responses.append(RegexResponse(trigger="ass testing", response=ass_testing_resp))


async def belgium_resp(message: Message) -> None:
    await message.channel.send("Watch your language!")


regex_responses.append(
    RegexResponse(trigger=r"^.{0,4}belgium\W{0,4}$", response=belgium_resp),
)


async def finally_resp(message: Message) -> None:
    await message.channel.send("middle text")


regex_responses.append(
    RegexResponse(trigger=r"^.{0,4}finally\W{0,4}$", response=finally_resp),
)


async def now_resp(message: Message) -> None:
    await message.channel.send(URL.GITHUB_STATIC + "/images/now.png")


regex_responses.append(
    RegexResponse(trigger=r"(^|\W)NOW\W{0,4}$", response=now_resp, flags=re.MULTILINE),
)


async def maybe_resp(message: Message) -> None:
    await message.channel.send(
        URL.GITHUB_STATIC + "/images/memes/Maybe%20I%20am%20a%20monster.png",
    )


regex_responses.append(RegexResponse(trigger="^maybe i am an?", response=maybe_resp))


async def twitter_resp(message: Message) -> None:
    tweets = re.findall(
        r"(https://(?:www\.)?(\w+)\.com/\w+/status/(\d+))",
        message.content,
    )
    num_pics = [0]
    for tweet in tweets:
        if tweet[1] not in ["x", "twitter", "vxtwitter", "fxtwitter"]:
            continue
        fx_tweet = tweet[0].replace(tweet[1], "fxtwitter", 1)
        html = requests.get(fx_tweet).text
        mosaic_link = list(
            set(
                re.findall(
                    r"https://mosaic\.fxtwitter\.com/\w*/\d+((?:/[\w-]+)+)",
                    html,
                ),
            ),
        )
        if len(mosaic_link) != 1:
            continue
        image_codes = mosaic_link[0][1:].split("/")
        num_pics.append(len(image_codes))
    if max(num_pics) > 1:
        await message.add_reaction(uf.int_to_emoji(max(num_pics)))


regex_responses.append(
    RegexResponse(
        trigger=r"https:.*(((vx|fx)?twitter)|x)\.com/.*/status/\d+",
        response=twitter_resp,
    ),
)


async def coinflip_resp(message: Message) -> None:
    await message.channel.send("Heads" if random.randint(0, 1) == 1 else "Tails")


regex_responses.append(
    RegexResponse(
        trigger="(coinflip|s a 50[ /]50|(flip|toss) (a |the )?coin)",
        response=coinflip_resp,
    ),
)


async def mario_resp(message: Message) -> None:
    await message.channel.send("Mario!")


regex_responses.append(
    RegexResponse(trigger=r"(^| )it(s|'s|s a|'s a|sa) me\W{0,4}$", response=mario_resp),
)


async def uhoh_resp(message: Message) -> None:
    await message.channel.send("SpaghettiOs 😦")
    if random.randint(0, 1) == 1:
        await message.channel.send("..and stinky!")


regex_responses.append(
    RegexResponse(trigger=r"^.{0,2}(oh|uh)[ \-_](oh)\W{0,4}$", response=uhoh_resp),
)


async def ahoy_resp(message: Message) -> None:
    await message.channel.send("Ahoy Matey!")
    await message.add_reaction("BlobWave:382606234148143115")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}(ahoy).{0,12}$", response=ahoy_resp),
)


async def spooky_resp(message: Message) -> None:
    await message.channel.send("2spooky4me")


regex_responses.append(
    RegexResponse(trigger="^.{0,12}spooky.{0,12}$", response=spooky_resp),
)


async def wait_min_resp(message: Message) -> None:
    await message.add_reaction("Thonk:383190394457948181")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}wait (a )?minute.{0,4}$", response=wait_min_resp),
)


async def easy_peasy_resp(message: Message) -> None:
    await message.channel.send("Lemon squeezy!")


regex_responses.append(
    RegexResponse(trigger=r"^\W{0,4}easy peasy\W{0,4}$", response=easy_peasy_resp),
)


async def tuesday_resp(message: Message) -> None:
    await message.channel.send("Happy <@235055132843180032> appreciation day everyone!")


regex_responses.append(
    RegexResponse(trigger=r"^\W{0,4}It( i|')s tuesday\W{0,4}$", response=tuesday_resp),
)


async def yeboi_resp(message: Message) -> None:
    boii = "BO" + "I" * (len(message.content) - 1)
    await message.channel.send(boii[:1999])


regex_responses.append(RegexResponse(trigger="^ye{3,}$", response=yeboi_resp))


async def cough_bless_resp(message: Message) -> None:
    await message.channel.send("Bless you!")


regex_responses.append(
    RegexResponse(
        trigger=r"\*(\S.*)?(cough|sneeze|acho{2,5})(.*\S)?\*",
        response=cough_bless_resp,
    ),
)


async def egeis_resp(message: Message) -> None:
    await message.channel.send("👀?egeiS yas enoemos diD")


regex_responses.append(RegexResponse(trigger=r"^.*egeis[^\?]*$", response=egeis_resp))


async def fme_resp(message: Message) -> None:
    await message.channel.send("Don't mind if I do 👍")


regex_responses.append(
    RegexResponse(trigger=r"^.{0,2}fuck me\W{0,4}$", response=fme_resp),
)


async def ayaya_resp(message: Message) -> None:
    await message.channel.send("Ayaya!")
    await message.add_reaction("Ayy:610479153937907733")
    await message.add_reaction("Ayy2:470743166207787010")


regex_responses.append(RegexResponse(trigger=r"^ayaya\W{0,4}$", response=ayaya_resp))


async def link_resp(message: Message) -> None:
    ids = re.search(r"\d+/\d+/\d+", message.content).group()
    guild_id, channel_id, message_id = re.split("/", ids)
    channel = uf.get_channel(channel_id)
    source_message = None
    try:  # noqa: SIM105
        source_message = await channel.fetch_message(int(message_id))
    except Exception:
        pass

    if not (channel and source_message):
        return

    embed = uf.message_embed(source_message, "link", message.author)
    if not source_message.content and source_message.embeds:
        embed.description = "[See attached embed]"
    await message.channel.send(embed=embed)
    if not source_message.content and source_message.embeds:
        await message.channel.send(embed=source_message.embeds[0])


# TODO: Better regex
DISCORD_MESSAGE_LINK_PATTERN = (
    r"https:\/\/(\w+\.)?discord(app)?\.com\/channels\/\d+\/\d+\/\d+"
)
regex_responses.append(
    RegexResponse(
        trigger=DISCORD_MESSAGE_LINK_PATTERN,
        response=link_resp,
        prio=True,
        accepts=lambda msg: not re.search(
            rf"\|\|.*?{DISCORD_MESSAGE_LINK_PATTERN}.*?\|\|",
            msg.content,
            re.MULTILINE | re.IGNORECASE,
        ),
    ),
)


async def what_is_love_resp(message: Message) -> None:
    await message.channel.send("*♬ Baby don't hurt me ♬*")


regex_responses.append(
    RegexResponse(trigger=r"^.{0,2}what is .?ove\?{0,3}$", response=what_is_love_resp),
)


async def baby_dont_hurt_me_resp(message: Message) -> None:
    await message.channel.send("*♬ no more ♬*")


regex_responses.append(
    RegexResponse(
        trigger="^.{0,2}don'?t hurt me.{0,4}$",
        response=baby_dont_hurt_me_resp,
    ),
)


async def sweet_dreams_resp(message: Message) -> None:
    await message.channel.send("*♬ are made of this ♬*")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}sweet dreams.{0,15}$", response=sweet_dreams_resp),
)


async def yarr_harr_resp(message: Message) -> None:
    await message.channel.send("fiddle de dee")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}(yarr har|yar har).{0,4}$", response=yarr_harr_resp),
)


async def trust_me_resp(message: Message) -> None:
    await message.channel.send("I'm an engineer!")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}trust me.{0,4}$", response=trust_me_resp),
)


async def long_ass_time_resp(message: Message) -> None:
    await message.channel.send("*♬ ..in a town called Kickapoo ♬*")


regex_responses.append(
    RegexResponse(
        trigger="^.{0,2}long ass? f(ucking)? time ago.{0,4}$",
        response=long_ass_time_resp,
    ),
)


async def testing_attention_resp(message: Message) -> None:
    await message.channel.send("*♬ Feel the tension soon as someone mentions me ♬*")


regex_responses.append(
    RegexResponse(
        trigger="^testing,? [\"']?attention,? please!?[\"']?$",
        response=testing_attention_resp,
    ),
)


async def testing_emn_resp(message: Message) -> None:
    await message.channel.send("**♬ Attention please! ♬**")


regex_responses.append(
    RegexResponse(trigger="^testing.{0,4}$", response=testing_emn_resp),
)


async def spaghetti_resp(message: Message) -> None:
    await message.channel.send("*mom's spaghetti*")


regex_responses.append(
    RegexResponse(trigger=r"^.{18,30}already\W{0,4}$", response=spaghetti_resp),
)


async def moneyyy_resp(message: Message) -> None:
    await message.channel.send(
        "Money money money money money money money money money money!",
    )


regex_responses.append(
    RegexResponse(trigger="^here comes the money.{0,4}$", response=moneyyy_resp),
)


async def yesterday_resp(message: Message) -> None:
    await message.channel.send("*♬ All my troubles seemed so far away ♬*")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}yesterday.{0,4}$", response=yesterday_resp),
)


async def deja_vu_resp(message: Message) -> None:
    await message.channel.send("*♬ I've just been in this place before ♬*")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}deja vu.{0,4}$", response=deja_vu_resp),
)


async def higher_on_the_street_resp(message: Message) -> None:
    await message.channel.send("*♬ And I know it's my time to go ♬*")


regex_responses.append(
    RegexResponse(
        trigger="^.{0,2}higher on the street.{0,4}$",
        response=higher_on_the_street_resp,
    ),
)


async def somebody_resp(message: Message) -> None:
    await message.channel.send("**BODY ONCE TOLD ME**")


regex_responses.append(
    RegexResponse(trigger=r"^(some|.*\Wsome\W*)$", response=somebody_resp),
)


async def roll_me_resp(message: Message) -> None:
    await message.channel.send("**I AIN'T THE SHARPEST TOOL IN THE SHED**")


regex_responses.append(
    RegexResponse(trigger=r"\W*the world is gonna roll me\W*", response=roll_me_resp),
)


async def hard_rock_resp(message: Message) -> None:
    await message.channel.send("**Hallelujah!**")


regex_responses.append(
    RegexResponse(trigger=r"^(hard rock|.*\Whard rock\W*)$", response=hard_rock_resp),
)


async def wake_up_resp(message: Message) -> None:
    await message.channel.send("*♬ Grab a brush and put a little make up! ♬*")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}wake up.{0,4}$", response=wake_up_resp),
)


async def beep_boop_resp(message: Message) -> None:
    await message.channel.send("I'm a robot.")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}beep boop.{0,4}$", response=beep_boop_resp),
)


async def beep_beep_resp(message: Message) -> None:
    await message.channel.send("I'm a sheep.")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}beep beep.{0,4}$", response=beep_beep_resp),
)


async def bark_bark_resp(message: Message) -> None:
    await message.channel.send("I'm a shark.")


regex_responses.append(
    RegexResponse(trigger="^.{0,4}bark bark.{0,4}$", response=bark_bark_resp),
)


async def meow_meow_resp(message: Message) -> None:
    await message.channel.send("I'm a cow.")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}meow meow.{0,4}$", response=meow_meow_resp),
)


async def quack_quack_resp(message: Message) -> None:
    await message.channel.send("I'm a yak.")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}quack quack.{0,4}$", response=quack_quack_resp),
)


async def dab_dab_resp(message: Message) -> None:
    await message.channel.send("I'm a crab.")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}dab dab.{0,4}$", response=dab_dab_resp),
)


async def float_float_resp(message: Message) -> None:
    await message.channel.send("I'm a goat.")


regex_responses.append(
    RegexResponse(trigger=" ^.{0,2}float float.{0,4}$", response=float_float_resp),
)


async def screech_screech_resp(message: Message) -> None:
    await message.channel.send("I'm a leech.")


regex_responses.append(
    RegexResponse(
        trigger="^.{0,2}screech screech.{0,4}$",
        response=screech_screech_resp,
    ),
)


async def bam_bam_resp(message: Message) -> None:
    await message.channel.send("I'm a lamb.")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}(bam bam)(slam slam).{0,4}$", response=bam_bam_resp),
)


async def dig_dig_resp(message: Message) -> None:
    await message.channel.send("I'm a pig.")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}dig dig.{0,4}$", response=dig_dig_resp),
)


async def roar_roar_resp(message: Message) -> None:
    await message.channel.send(
        "I'm a boar." if random.randint(0, 1) == 1 else "Dinosaur",
    )


regex_responses.append(
    RegexResponse(trigger="^.{0,2}roar roar.{0,4}$", response=roar_roar_resp),
)


async def shake_shake_resp(message: Message) -> None:
    await message.channel.send("I'm a snake.")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}shake shake.{0,4}$", response=shake_shake_resp),
)


async def swish_swish_resp(message: Message) -> None:
    await message.channel.send("I'm a fish.")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}swish swish.{0,4}$", response=swish_swish_resp),
)


async def squawk_squawk_resp(message: Message) -> None:
    await message.channel.send("I'm a hawk.")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}squawk squawk.{0,4}$", response=swish_swish_resp),
)


async def cluck_cluck_resp(message: Message) -> None:
    await message.channel.send("I'm a duck.")


regex_responses.append(
    RegexResponse(trigger=".{0,2}cluck cluck.{0,4}$", response=cluck_cluck_resp),
)


async def growl_growl_resp(message: Message) -> None:
    await message.channel.send("I'm an owl.")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}growl growl.{0,4}$", response=growl_growl_resp),
)


async def drop_drop_resp(message: Message) -> None:
    await message.channel.send("Do the flop!")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}drop drop.{0,4}$", response=drop_drop_resp),
)


async def boink_boink_resp(message: Message) -> None:
    await message.channel.send("I'm bad at rhyming. :(")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}boink boink.{0,4}$", response=boink_boink_resp),
)


async def click_click_resp(message: Message) -> None:
    await message.channel.send("I'm a chick.")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}click click.{0,4}$", response=click_click_resp),
)


async def blue_resp(message: Message) -> None:
    await message.channel.send("♬ Da ba dee da ba di ♬")


regex_responses.append(
    RegexResponse(trigger="^.{0,2}I('| a)?m blue{0,4}$", response=blue_resp),
)


async def pingsock_resp(message: Message) -> None:
    await asyncio.sleep(5)
    if random.randint(1, 4) == 1:
        await message.channel.send(
            f"Do I see someone who loves being pinged, {message.author.mention}?",
        )


regex_responses.append(
    RegexResponse(trigger=r"^<:Pingsock:\d+>$", response=pingsock_resp),
)


async def wave_resp(message: Message) -> None:
    if message.author.id == ID.FEL:
        reacts = [
            "BlobWave:382606234148143115",
            "🇫",
            "🇪",
            "🇱",
            "❤️",
            "🇨",
            "🇭",
            "🇦",
            "🇳",
            "BlobAww:380182813300752395",
        ]
        for react in reacts:
            await message.add_reaction(react)
    elif ":Whale" not in message.content:
        await message.add_reaction("BlobWave:382606234148143115")


regex_responses.append(
    RegexResponse(
        trigger="^(<:BlobWave:382606234148143115>|<:BlobCoffee:456004868990173198>)",
        response=wave_resp,
    ),
)


async def pedestal_resp(message: Message) -> None:
    await message.add_reaction("👏")
    await message.channel.send("Quickly, master <@235055132843180032>, quickly!")


regex_responses.append(
    RegexResponse(
        trigger=r"(\[Pedestal Prime\])|(:PedestalPrime:)",
        response=pedestal_resp,
    ),
)


async def wood_resp(message: Message) -> None:
    await message.add_reaction("🪓")
    await message.add_reaction("🌲")


regex_responses.append(
    RegexResponse(
        trigger="wood",
        response=wood_resp,
        accepts=lambda message: message.author.id == ID.KROSS,
    ),
)


async def stradavar_resp(message: Message) -> None:
    await message.channel.send(f"Quickly, <@{ID.JORM}>, quickly!")
    await message.add_reaction("👏")


regex_responses.append(
    RegexResponse(
        trigger=r"^.*((\[Stradavar Prime\])|(:StradavarPrime.{0,4}:)).*$",
        response=stradavar_resp,
    ),
)


async def keto_resp(message: Message) -> None:
    await message.add_reaction("ketoroll:634859950283161602")
    await message.add_reaction("ketoface:634852360514174976")


def keto_resp_check(message: Message) -> None:
    return (
        message.author.id == ID.ANA
        and message.channel.name == "awww"
        and len(message.attachments) > 0
        and (message.attachments[0].height)
    )


regex_responses.append(
    RegexResponse(trigger=".*", response=keto_resp, accepts=keto_resp_check),
)


async def siege_resp(message: Message) -> None:
    reactions = [
        "⏰",
        "2️⃣",
        "BlobCatGun:621700315376517122",
        "🇸",
        "🇹",
        "🇷",
        "🇴",
        "🇳",
        "🇿",
        "0️⃣",
    ]
    for reaction in reactions:
        await message.add_reaction(reaction)


regex_responses.append(RegexResponse(trigger=r"siege.*\?", response=siege_resp))


async def offers_resp(message: Message) -> None:
    await message.delete()
    await message.author.send(
        f"Hi {message.author.mention}! We're trying to streamline "
        f"{message.channel.mention} - please update your post to contain a link, "
        "an image, or a specific reference to a game store and re-post it. "
        "If you've received this message in error, please contact your favorite mod.",
    )


def offers_resp_check(message: Message) -> None:
    whitelist = [
        "https",
        "store",
        "steam",
        "free",
        "epic",
        "EGS",
        "launcher",
        "percent",
        "%",
        "uplay",
        "origin",
        "GOG",
        "ubi",
        "key",
        "code",
        "sale",
    ]
    return message.channel.name == ChannelName.OFFERS and not (
        message.attachments
        or any(word in message.content.lower() for word in whitelist)
    )


regex_responses.append(
    RegexResponse(trigger=".*", response=offers_resp, accepts=offers_resp_check),
)


async def good_bot_resp(message: Message) -> None:
    await message.add_reaction("BlobAww:380182813300752395")


regex_responses.append(
    RegexResponse(
        trigger=r"^(.{0,20} |)(good|thanks?( (yo)?u)?|love( (yo)?u)?) "
        r"(bot|<..736265509951242403>)\W{0,2}$",
        response=good_bot_resp,
    ),
)


async def bad_bot_resp(message: Message) -> None:
    await message.add_reaction("BlobBan:438000257385889792")


regex_responses.append(
    RegexResponse(
        trigger=r"^(.{0,20} |)((bad)|(stupid)|(f((uc)?k)? off)|(fuck)|(hate "
        r"((yo)?u|this))|(shut up)|(stfu)|(f((uc)?k)? ?(yo)?u)) "
        r"((void )?bot|<..736265509951242403>).*$",
        response=bad_bot_resp,
    ),
)


async def hms_resp(message: Message) -> None:
    await message.channel.send(URL.GITHUB_STATIC + "/images/hms%20fucking.png")


regex_responses.append(
    RegexResponse(trigger="welcome aboard the hms fucking", response=hms_resp),
)


async def gramps_resp(message: Message) -> None:
    await message.channel.send(URL.GITHUB_STATIC + "/images/markus.gif")
    await message.channel.send(message.content)


regex_responses.append(
    RegexResponse(trigger=r"^<@!?141523991260037120>$", response=gramps_resp),
)


async def reputation_resp(message: Message) -> None:
    for mentioned_user in message.mentions:
        await give_award(
            giver=message.author,
            recipient=mentioned_user,
            award=Award.THANKS,
            channel=message.channel,
        )


regex_responses.append(
    RegexResponse(
        trigger=r"thanks?( (yo)?u)?( for .{2,60})?\W*<.{8,28}>",
        response=reputation_resp,
        prio=True,
        accepts=lambda message: message.mentions,
    ),
)


async def so_true_resp(message: Message) -> None:
    await message.channel.send(URL.GITHUB_STATIC + "/videos/so_true.mov")


regex_responses.append(
    RegexResponse(trigger="^.{0,4}so true.{0,4}$", response=so_true_resp),
)


async def is_this_real_resp(message: Message) -> None:
    await uf.invoke_slash_command(name="8ball", interaction=message.channel)  # 🦆


regex_responses.append(
    RegexResponse(
        trigger="^.{0,4}(@grok|"
        + uf.id_to_mention(ID.BOT)
        + r")\W+(is|are|am|was|were|do|does|did|have|has|had|can|can't|"
        + r"could|will|won't|would|shall|shan't|should|may|might|must)(n't)?\W.*\?",
        response=is_this_real_resp,
    ),
)


@dataclass(kw_only=True)
class WednesdayResponse(RegexResponse):
    """Wrapper class for extra parameters for Wednesday responses."""

    wrong_day_response: str
    a: str = "a"
    trigger_day: int = 2


wednesday_responses: list[WednesdayResponse] = [
    WednesdayResponse(
        trigger="It is wednesday",
        response="my dudes",
        wrong_day_response="It appears you don't know how a calendar works. "
        "Do you require assistance with that?",
    ),
    WednesdayResponse(
        trigger="Es ist Mittwoch",
        response="meine Kerle",
        wrong_day_response="Hast du keinen Kalender oder was?",
    ),
    WednesdayResponse(
        trigger="jest [sś]roda",
        response="o panowie",
        wrong_day_response="Co kurwa?",
    ),
    WednesdayResponse(
        trigger="het is woensdag",
        response="mijn makkers",
        wrong_day_response="Wie heeft jouw agenda gekoloniseerd?",
    ),
    WednesdayResponse(
        trigger="szerda van",
        response="felebarátaim",
        a="á",
        wrong_day_response="Szia uram, eladó naptár, érdekel?",
    ),
    WednesdayResponse(
        trigger="je streda",
        response="kamoši moji",
        wrong_day_response="Neviem kde si, ale tu v Slovinsku nie je streda.",
    ),
    WednesdayResponse(
        trigger="sr(e|i(je)?)da je",
        response="moji ljudi",
        wrong_day_response="Jebote, zar nemaš kalendar?",
    ),
    WednesdayResponse(
        trigger="c'?est mercredi",
        response="mes mecs",
        wrong_day_response="Ceci n'est pas un mercredi",
    ),
    WednesdayResponse(
        trigger="se on keskiviikko",
        response="kaverit",
        wrong_day_response="Unohditko kalenterin saunaan?",
    ),
    WednesdayResponse(
        trigger="det är onsdag",
        response="mina bekanta",
        wrong_day_response="Svårt att läsa kalendern eller vadå?",
    ),
    WednesdayResponse(
        trigger="det är fredag",
        response="mina bekanta",
        wrong_day_response="Svårt att läsa kalendern eller vadå?",
        trigger_day=4,
    ),
    WednesdayResponse(
        trigger="水曜日だ",
        response="お前ら",
        a="あ",
        wrong_day_response="何?",
    ),
    WednesdayResponse(
        trigger="det er onsdag",
        response="folkens",
        a="æ",
        wrong_day_response="Ikke nok oljepenger til en kalender eller?",
    ),
    WednesdayResponse(
        trigger="es mi(e|é)rcoles",
        response="mis amigos",
        wrong_day_response="https://www.google.com/search?q=¿Qué+día+es+hoy?",
    ),
    WednesdayResponse(
        trigger="(est|e|i|iî) miercuri",
        response="fraţii mei",
        wrong_day_response="Ar fi bine să-ți iei un calendar înainte "
        "să-l trimit pe Aeggis după tine",
    ),
    WednesdayResponse(
        trigger="היום יום רביעי",
        response="אחים שלי",
        a="א",
        wrong_day_response="https://www.google.com/search?q=?איזה+יום+היום",
    ),
    WednesdayResponse(
        trigger="jau tre[cč]iadienis",
        response="mano bičiuliai",
        wrong_day_response="Ką, kryžiuočių ordinas pavogė tavo kalendorių?",
    ),
]
for resp in wednesday_responses:
    resp.trigger = "^.{0,4}" + resp.trigger + r"\W{0,4}$"
