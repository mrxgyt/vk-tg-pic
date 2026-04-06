# PicGenAI — Telegram + VK Image Generation Bot

## Overview
An asynchronous multi-platform bot (Telegram + VK) for AI image generation using Google Gemini / Vertex AI. Built with Python 3.12, aiogram 3.x (Telegram), and vkbottle (VK). Includes a credit-based monetization system with Pally.info payment integration.

## Architecture
- **Entry point**: `start_all.py` — runs Telegram bot, VK bot, and a web server concurrently via asyncio
- **Web server**: aiohttp on port 5000 — landing page, payment success/fail pages, Pally webhooks
- **Bot logic**: `bot/` — Telegram handlers, middlewares, services
- **VK logic**: `vk_bot/` — VK handlers
- **Shared services**: `bot/services/vertex_ai_service.py` — Google Gemini AI client
- **Payment**: `bot/services/payment_service.py` — Pally.info API integration
- **Web pages**: `web/templates/` — landing (index.html), success.html, fail.html
- **Webhooks**: `bot/web_server.py` — payment webhook handler with signature verification, idempotency
- **Config**: `bot/config.py` — pydantic-settings from environment variables
- **Database**: `bot/db.py` — PostgreSQL persistence (users, API keys, payments)

## Required Secrets
- `TELEGRAM_BOT_TOKEN` — Bot token from @BotFather
- `VK_BOT_TOKEN` — VK community token
- `GOOGLE_CLOUD_API_KEY` — Google Cloud API key with Vertex AI access

## Optional Secrets (Payment)
- `PALLY_SHOP_ID` — Pally.info shop ID
- `PALLY_TOKEN` — Pally.info API token
- `BASE_URL` — Public URL for webhooks (e.g. https://your-domain.com)
- `DATABASE_URL` — PostgreSQL connection string (for persistent storage)

## Running
- Workflow: "Start application" runs `python start_all.py` on port 5000
- Bots start automatically if their respective tokens are set
- Admin panel: `/adminmrxgyt` command in Telegram

## Web Endpoints
- `GET /` — Landing page (PicGenAI)
- `GET /payment/success` — Payment success redirect
- `GET /payment/fail` — Payment failure redirect
- `POST /webhook/pally` — Pally.info payment webhook (signature-verified)
- `POST /webhook/pally/refund` — Refund webhook
- `POST /webhook/pally/chargeback` — Chargeback webhook

## Credits System
- 30 free credits on registration
- 1 credit per generation, 2 credits for 4K
- Packages: 30 credits (99₽), 99 credits (299₽)

## PostgreSQL Tables
- `bot_user_settings` — user_id BIGINT PK, data TEXT
- `bot_api_keys` — id SERIAL PK, key TEXT UNIQUE
- `bot_payments` — order_id TEXT PK, payment_id, user_id, pack_key, amount, status, timestamps

## Bot Links
- Telegram: https://t.me/PicGenAI_26_bot
- VK: https://vk.ru/picgenai
- Support: https://t.me/ShadowsockTM

## Dependencies
Managed via `requirements.txt` with pip. Key packages:
- aiogram>=3.15, vkbottle>=4.8, google-genai>=1.9
- pydantic-settings>=2.7, Pillow>=11.0, aiohttp>=3.9
- psycopg2-binary>=2.9
