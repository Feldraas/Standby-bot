import json
import logging

import requests
from nextcord import SlashOption, slash_command
from nextcord.ext.commands import Cog

from config.constants import Token

logger = logging.getLogger(__name__)


class GPT(Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="Ask, and the Void shall answer.")
    async def voidgpt(
        self, interaction, prompt=SlashOption(description="Your question")
    ):
        await interaction.response.defer()
        auth = f"Bearer {Token.OPENAI_API_KEY}"
        logger.info("Sending request to openai")
        resp = requests.request(
            "POST",
            url="https://api.openai.com/v1/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": auth},
            json={
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": f"{prompt}"}],
            },
        )
        try:
            resp = json.loads(resp.content.decode("utf-8"))
            full_message = resp["choices"][0]["message"]["content"].split(" ")
            message = []
            for word in full_message:
                message.append(word)
                max_message_length = 2000
                if len(" ".join(message)) > max_message_length:
                    await interaction.send(" ".join(message[:-1]))
                    message = [message[-1]]
            await interaction.send(" ".join(message))
        except KeyError:
            logger.exception(f"Invalid response from OpenAI API: {resp}")
            await interaction.send("No response", ephemeral=True)


def setup(bot):
    bot.add_cog(GPT(bot))
