# Telegram + VK Image Generation Bot

## Overview
An asynchronous multi-platform bot (Telegram + VK) for AI image generation using Google Gemini / Vertex AI. Built with Python 3.12, aiogram 3.x (Telegram), and vkbottle (VK).

## Architecture
- **Entry point**: `start_all.py` — runs Telegram bot, VK bot, and a web server concurrently via asyncio
- **Web server**: aiohttp on port 5000 (required for Replit preview)
- **Bot logic**: `bot/` — Telegram handlers, middlewares, services
- **VK logic**: `vk_bot/` — VK handlers
- **Shared services**: `bot/services/vertex_ai_service.py` — Google Gemini AI client
- **Config**: `bot/config.py` — pydantic-settings from environment variables
- **Data**: `data/` — JSON files for API keys and user settings

## Required Secrets
- `TELEGRAM_BOT_TOKEN` — Bot token from @BotFather (optional if using VK only)
- `VK_BOT_TOKEN` — VK community token (optional if using Telegram only)
- `GOOGLE_CLOUD_API_KEY` — Google Cloud API key with Vertex AI access (required for AI features)

## Running
- Workflow: "Start application" runs `python start_all.py` on port 5000
- Bots start automatically if their respective tokens are set
- API keys can also be managed via the in-bot admin panel (`/adminmrxgyt <password>`)

## Key Features
- Text prompt → image generation
- Photo + description → image editing
- Creative mode (step-by-step AI image series)
- Model selection: Flash (fast) / Pro (quality)
- API key rotation on 429 errors
- Image upscale up to 4K via Pillow

## Dependencies
Managed via `requirements.txt` with pip. Key packages:
- aiogram>=3.15, vkbottle>=4.8, google-genai>=1.9
- pydantic-settings>=2.7, Pillow>=11.0, aiohttp>=3.9
