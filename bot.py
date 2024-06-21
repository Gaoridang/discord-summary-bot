import os
import discord
import openai
from datetime import datetime, time

# 환경 변수 설정
TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
AUTHORIZED_USERS = [
    int(id) for id in os.getenv("AUTHORIZED_USERS", "").split(",") if id
]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

openai.api_key = OPENAI_API_KEY


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
    for user_id in AUTHORIZED_USERS:
        user = await client.fetch_user(user_id)
        user_summary = await summarize_coding_activity(messages, user_id)
        if user_summary:
            summary += f"{user.name}의 활동:\n{user_summary}\n\n"

    if summary == "오늘의 코딩 테스트 활동 요약:\n\n":
        summary += "오늘은 인증된 유저들의 코딩 테스트 활동이 없었습니다."

    await channel.send(summary)


async def main():
    await client.login(TOKEN)
    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        print("Channel not found")
        return

    await daily_summary()
    await client.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
