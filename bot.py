import os
import discord
from openai import OpenAI
from datetime import datetime, time
import asyncio

# 환경 변수 설정
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
READ_CHANNEL_ID = int(os.getenv("READ_CHANNEL_ID"))
SEND_CHANNEL_ID = int(os.getenv("SEND_CHANNEL_ID"))
AUTHORIZED_USERS = [
    int(id) for id in os.getenv("AUTHORIZED_USERS", "").split(",") if id
]

intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

openai_client = OpenAI(api_key=OPENAI_API_KEY)


@discord_client.event
async def on_ready():
    print(f"{discord_client.user} has connected to Discord!")
    try:
        await asyncio.wait_for(daily_summary(), timeout=300)  # 5분 타임아웃
    except asyncio.TimeoutError:
        print("Daily summary timed out after 5 minutes")
    finally:
        await discord_client.close()


async def summarize_coding_activity(messages, user_id, nickname):
    print(f"Summarizing activity for user: {nickname}")
    user_messages = [m for m in messages if m.author.id == user_id]
    if not user_messages:
        print(f"No messages found for user: {nickname}")
        return f"- {nickname}\n  - 총 0문제"

    combined_messages = "\n".join(
        [f"{m.author.name}: {m.content}" for m in user_messages]
    )

    print(f"Sending request to OpenAI for user: {nickname}")
    try:
        response = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model="gpt-3.5-turbo-0125",
            messages=[
                {
                    "role": "system",
                    "content": f"""당신은 사용자의 코딩 테스트 활동을 요약하는 도우미입니다. 형식은 다음과 같습니다.
                    - {nickname}
                      - 총 X문제
                      - https://school.programmers.co.kr/learn/courses/30/lessons/XXXXX
                      - https://school.programmers.co.kr/learn/courses/30/lessons/XXXXX
                      - https://school.programmers.co.kr/learn/courses/30/lessons/XXXXX
                    """,
                },
                {
                    "role": "user",
                    "content": f"다음 메시지들에서 {nickname}의 코딩 테스트 활동을 요약해주세요:\n\n{combined_messages}",
                },
            ],
        )
        print(f"Received response from OpenAI for user: {nickname}")
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in OpenAI request for user {nickname}: {e}")
        return f"- {nickname}\n  - 오류 발생: {str(e)}"


async def daily_summary():
    print("Starting daily summary...")
    read_channel = discord_client.get_channel(READ_CHANNEL_ID)
    send_channel = discord_client.get_channel(SEND_CHANNEL_ID)

    if read_channel is None or send_channel is None:
        print(
            f"Channel not found. READ_CHANNEL_ID: {READ_CHANNEL_ID}, SEND_CHANNEL_ID: {SEND_CHANNEL_ID}"
        )
        return

    today = datetime.now().date()
    midnight = datetime.combine(today, time.min)
    print("Fetching messages...")
    messages = [msg async for msg in read_channel.history(after=midnight, limit=None)]

    print(f"Number of messages fetched: {len(messages)}")

    summary = f"{today.strftime('%Y.%m.%d')}\n"
    for user_id in AUTHORIZED_USERS:
        member = read_channel.guild.get_member(user_id)
        if member:
            nickname = member.nick if member.nick else member.name
        else:
            user = await discord_client.fetch_user(user_id)
            nickname = user.name
        user_summary = await summarize_coding_activity(messages, user_id, nickname)
        summary += f"{user_summary}\n"

    print("Summary content:")
    print(summary)

    print("Sending summary...")
    await send_channel.send(summary)
    print("Summary sent.")


@discord_client.event
async def on_message(message):
    if message.author == discord_client.user:
        return

    if message.content.startswith("!요약"):
        await daily_summary()


def main():
    discord_client.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
