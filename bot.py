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
    try:
        await asyncio.wait_for(daily_summary(), timeout=300)  # 5분 타임아웃
    except asyncio.TimeoutError:
        print("Daily summary timed out after 5 minutes")
    finally:
        await client.close()


async def summarize_coding_activity(messages, user_id):
    print(f"Summarizing activity for user ID: {user_id}")
    user_messages = [m for m in messages if m.author.id == user_id]
    if not user_messages:
        print(f"No messages found for user ID: {user_id}")
        return None

    combined_messages = "\n".join(
        [f"{m.author.name}: {m.content}" for m in user_messages]
    )

    print(f"Sending request to OpenAI for user ID: {user_id}")
    try:
        response = await asyncio.wait_for(
            openai.ChatCompletion.acreate(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 사용자의 코딩 테스트 활동을 요약하는 도우미입니다. 메시지 내용을 분석하여 사용자가 풀은 코딩 문제의 수와 문제 목록을 불렛 포인트로 요약해주세요. 링크나 문제 번호만 있는 경우에도 하나의 문제로 간주합니다.",
                    },
                    {
                        "role": "user",
                        "content": f"다음 메시지들에서 코딩 테스트 활동을 요약해주세요:\n\n{combined_messages}",
                    },
                ],
            ),
            timeout=60,
        )
        print(f"Received response from OpenAI for user ID: {user_id}")
        return response.choices[0].message["content"]
    except asyncio.TimeoutError:
        print(f"OpenAI request timed out for user ID: {user_id}")
        return "OpenAI 요청 시간 초과"
    except Exception as e:
        print(f"Error in OpenAI request for user ID {user_id}: {e}")
        return f"오류 발생: {str(e)}"


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

    print(f"Read channel found: {read_channel.name} (ID: {read_channel.id})")
    print(f"Send channel found: {send_channel.name} (ID: {send_channel.id})")

    today = datetime.now().date()
    midnight = datetime.combine(today, time.min)
    print("Fetching messages...")
    messages = [msg async for msg in read_channel.history(after=midnight, limit=None)]

    print(f"Number of messages fetched: {len(messages)}")
    for msg in messages:
        print(f"Message from {msg.author.name}: {msg.content[:50]}...")

    print("Authorized users:")
    for user_id in AUTHORIZED_USERS:
        try:
            user = await client.fetch_user(user_id)
            print(f"  - {user.name} (ID: {user.id})")
        except discord.NotFound:
            print(f"  - Unknown user (ID: {user_id})")
    print(f"Total number of authorized users: {len(AUTHORIZED_USERS)}")

    summary = "오늘의 코딩 테스트 활동 요약:\n\n"
    for user_id in AUTHORIZED_USERS:
        user = await client.fetch_user(user_id)
        user_summary = await summarize_coding_activity(messages, user_id)
        if user_summary:
            summary += f"{user.name}의 활동:\n{user_summary}\n\n"
        else:
            print(f"No activity summary for user {user.name}")

    if summary == "오늘의 코딩 테스트 활동 요약:\n\n":
        summary += "오늘은 인증된 유저들의 코딩 테스트 활동이 없었습니다."

    print("Summary content:")
    print(summary)

    print("Sending summary...")
    await send_channel.send(summary)
    print("Summary sent.")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!요약"):
        await daily_summary()


def main():
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.start(TOKEN))
    except KeyboardInterrupt:
        loop.run_until_complete(client.close())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
