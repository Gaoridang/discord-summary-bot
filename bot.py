import os
import discord
from dotenv import load_dotenv
import openai
from datetime import datetime, time
import asyncio
import schedule
import time as time_module
import json

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # 요약을 보낼 채널 ID

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # 서버 멤버 정보에 접근하기 위해 필요
client = discord.Client(intents=intents)

openai.api_key = OPENAI_API_KEY

# 인증된 유저 목록을 저장할 파일
AUTHORIZED_USERS_FILE = "authorized_users.json"


# 인증된 유저 목록 불러오기
def load_authorized_users():
    try:
        with open(AUTHORIZED_USERS_FILE, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


# 인증된 유저 목록 저장하기
def save_authorized_users(users):
    with open(AUTHORIZED_USERS_FILE, "w") as f:
        json.dump(list(users), f)


authorized_users = load_authorized_users()


async def summarize_coding_activity(messages, user_id):
    coding_messages = [
        m
        for m in messages
        if m.author.id == user_id and "코딩테스트" in m.content.lower()
    ]
    if not coding_messages:
        return None

    combined_messages = "\n".join([m.content for m in coding_messages])
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "당신은 사용자의 코딩 테스트 활동을 요약하는 도우미입니다. 풀은 문제의 수와 문제 목록을 불렛 포인트로 요약해주세요.",
            },
            {
                "role": "user",
                "content": f"다음 메시지들에서 코딩 테스트 활동을 요약해주세요:\n\n{combined_messages}",
            },
        ],
    )
    return response.choices[0].message["content"]


async def daily_summary():
    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        print("Channel not found")
        return

    today = datetime.now().date()
    midnight = datetime.combine(today, time.min)
    messages = [msg async for msg in channel.history(after=midnight, limit=None)]

    summary = "오늘의 코딩 테스트 활동 요약:\n\n"
    for user_id in authorized_users:
        user = await client.fetch_user(user_id)
        user_summary = await summarize_coding_activity(messages, user_id)
        if user_summary:
            summary += f"{user.name}의 활동:\n{user_summary}\n\n"

    if summary == "오늘의 코딩 테스트 활동 요약:\n\n":
        summary += "오늘은 인증된 유저들의 코딩 테스트 활동이 없었습니다."

    await channel.send(summary)


@client.event
async def on_ready():
    print(f"{client.user} has connected to Discord!")


def run_daily_summary():
    asyncio.run_coroutine_threadsafe(daily_summary(), client.loop)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!요약"):
        await daily_summary()
    elif message.content.startswith("!인증"):
        authorized_users.add(message.author.id)
        save_authorized_users(authorized_users)
        await message.channel.send(f"{message.author.name}님이 인증되었습니다.")
    elif message.content.startswith("!인증취소"):
        authorized_users.discard(message.author.id)
        save_authorized_users(authorized_users)
        await message.channel.send(f"{message.author.name}님의 인증이 취소되었습니다.")


async def schedule_daily_summary():
    schedule.every().day.at("09:05").do(run_daily_summary)
    while True:
        schedule.run_pending()
        await asyncio.sleep(60)  # 1분마다 체크


client.loop.create_task(schedule_daily_summary())
client.run(TOKEN)
