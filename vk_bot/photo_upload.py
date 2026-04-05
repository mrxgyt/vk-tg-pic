from __future__ import annotations

import asyncio
import io
import json
import logging
from typing import Any

import aiohttp
from PIL import Image

logger = logging.getLogger(__name__)

MAX_RETRIES = 3

async def upload_photo_to_vk(api: Any, peer_id: int, image_bytes: bytes) -> str:
    # Отправляем оригинальные байты от нейросети напрямую, без урезаний и "пережевывания" через Pillow
    filename = "image.png"
    content_type = "image/png"

    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            upload_server = await api.photos.get_messages_upload_server(peer_id=peer_id)
            upload_url = upload_server.upload_url
            logger.info("VK upload URL obtained (attempt %d), uploading %d bytes...", attempt + 1, len(jpg_bytes))

            form = aiohttp.FormData()
            form.add_field(
                "photo",
                io.BytesIO(image_bytes),
                filename=filename,
                content_type=content_type,
            )

            async with aiohttp.ClientSession() as session:
                async with session.post(upload_url, data=form) as resp:
                    raw_text = await resp.text()
                    logger.info("VK upload raw response (attempt %d): status=%d, body=%s", attempt + 1, resp.status, raw_text[:500])
                    result = json.loads(raw_text)

            photo_field = result.get("photo", "")
            if not photo_field or photo_field == "[]":
                raise ValueError(f"VK upload returned empty photo field: {result}")

            saved = await api.photos.save_messages_photo(
                photo=result["photo"],
                server=result["server"],
                hash=result["hash"],
            )

            photo = saved[0]
            access = f"_{photo.access_key}" if photo.access_key else ""
            attachment = f"photo{photo.owner_id}_{photo.id}{access}"
            logger.info("VK photo saved: %s", attachment)
            return attachment

        except Exception as exc:
            last_err = exc
            logger.warning("VK photo upload attempt %d failed: %s", attempt + 1, exc)
            if attempt < 2:
                await asyncio.sleep(0.5)

    raise last_err


async def download_vk_photo(api: Any, photo_sizes: list) -> bytes:
    best = max(photo_sizes, key=lambda s: s.width * s.height)
    url = best.url

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.read()
