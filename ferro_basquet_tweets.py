import feedparser
from discord.ext import tasks
import discord

TWITTER_USER = "ferrobasquetok"
KEYWORD = "#ferro"
CHECK_MINUTES = 5
CHANNEL_ID = 1452880772372627456

last_tweet_link = None

class FerroBasquetTweets:
    def __init__(self, bot):
        self.bot = bot
        self.check_tweets.start()

    @tasks.loop(minutes=CHECK_MINUTES)
    async def check_tweets(self):
        global last_tweet_link

        rss_url = f"https://nitter.net/{TWITTER_USER}/rss"
        feed = feedparser.parse(rss_url)

        if not feed.entries:
            return

        channel = self.bot.get_channel(CHANNEL_ID)
        if channel is None:
            return

        for entry in reversed(feed.entries):
            content = entry.summary.lower()

            if KEYWORD in content and entry.link != last_tweet_link:
                embed = discord.Embed(
                    title="🏀 Ferro Básquet",
                    description=entry.summary,
                    url=entry.link,
                    color=0x0B6623
                )
                embed.set_footer(text="@ferrobasquetok")

                await channel.send(embed=embed)
                last_tweet_link = entry.link
