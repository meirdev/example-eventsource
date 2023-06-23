import asyncio
import json
import uuid
from typing import AsyncIterable

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse


app = FastAPI()

_redis: redis.Redis


async def read_messages(username: str) -> AsyncIterable[str]:
    async with _redis.pubsub() as pubsub:
        await pubsub.subscribe(f"user:{username}")

        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
            if message is not None:
                data = json.dumps(message["data"].decode())

                yield "id: "
                yield str(uuid.uuid4())
                yield "event: message"
                yield "\n"
                yield f"data: {data}"
                yield "\n\n"


async def send_messages():
    while True:
        for channel in await _redis.pubsub_channels():
            if channel.startswith(b"user:"):
                user = channel.split(b":")[1].decode()
                await _redis.publish(channel, f"Hi {user}")
        await asyncio.sleep(3)


@app.on_event("startup")
async def startup():
    global _redis

    _redis = redis.Redis()

    asyncio.create_task(send_messages())


@app.on_event("shutdown")
async def shutdown():
    await _redis.close()


@app.get("/stream/{username}")
def stream(username: str):
    return StreamingResponse(read_messages(username), media_type="text/event-stream")


@app.get("/")
def index():
    with open("index.html") as fp:
        return HTMLResponse(fp.read())
