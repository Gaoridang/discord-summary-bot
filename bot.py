import os
import discord
import openai
from datetime import datetime, time
import asyncio

# 환경 변수 설정
TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
READ_CHANNEL_ID = int(os.getenv("READ_CHANNEL_ID"))
SEND_CHANNEL_ID = int(os.getenv("SEND_CHANNEL_ID"))
AUTHORIZED_USERS = [
    int(id) for id in os.getenv("AUTHORIZED_USERS", "").split(",") if id
]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

openai.api_key = OPENAI_API_KEY


@client.event
async def on_ready():
    print(f"{client.user} has connected to Discord!")
    await daily_summary()
    await client.close()


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
    print("Starting daily summary...")
    read_channel = client.get_channel(READ_CHANNEL_ID)
    send_channel = client.get_channel(SEND_CHANNEL_ID)

    if read_channel is None:
        print(f"Read channel not found. READ_CHANNEL_ID: {READ_CHANNEL_ID}")
        return
    if send_channel is None:
        print(f"Send channel not found. SEND_CHANNEL_ID: {SEND_CHANNEL_ID}")
        return

    print("Channels found. Fetching messages...")

    today = datetime.now().date()
    midnight = datetime.combine(today, time.min)
    messages = [msg async for msg in read_channel.history(after=midnight, limit=None)]

    summary = "오늘의 코딩 테스트 활동 요약:\n\n"
    for user_id in AUTHORIZED_USERS:
        user = await client.fetch_user(user_id)
        user_summary = await summarize_coding_activity(messages, user_id)
        if user_summary:
            summary += f"{user.name}의 활동:\n{user_summary}\n\n"

    if summary == "오늘의 코딩 테스트 활동 요약:\n\n":
        summary += "오늘은 인증된 유저들의 코딩 테스트 활동이 없었습니다."

    print("Sending summary...")
    await send_channel.send(summary)
    print("Summary sent.")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!요약"):
        await daily_summary()


async def main():
    try:
        await client.start(TOKEN)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
