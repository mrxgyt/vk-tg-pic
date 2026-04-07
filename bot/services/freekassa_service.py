import hashlib
import hmac
import logging
import os
import time

import aiohttp

import bot.db as _db

logger = logging.getLogger(__name__)

FREEKASSA_SHOP_ID = os.getenv("FREEKASSA_SHOP_ID", "")
FREEKASSA_SECRET1 = os.getenv("FREEKASSA_SECRET1", "")
FREEKASSA_SECRET2 = os.getenv("FREEKASSA_SECRET2", "")
FREEKASSA_API_KEY = os.getenv("FREEKASSA_API_KEY", "")

CREDIT_PACKAGES = {
    "pack_30": {"credits": 30, "amount": 99.00, "label": "30 кредитов — 99₽"},
    "pack_100": {"credits": 100, "amount": 299.00, "label": "100 кредитов — 299₽"},
    "pack_200": {"credits": 200, "amount": 549.00, "label": "200 кредитов — 549₽"},
}

PAYMENT_METHODS = {
    "card": {"i": 4, "label": "💳 Банковская карта"},
    "sbp": {"i": 13, "label": "🏦 СБП"},
    "mir": {"i": 12, "label": "🇷🇺 МИР"},
    "yoomoney": {"i": 6, "label": "🟣 ЮMoney"},
}

FK_API_URL = "https://api.fk.life/v1"

_nonce_counter = int(time.time())


def _next_nonce() -> int:
    global _nonce_counter
    _nonce_counter += 1
    return _nonce_counter


def _make_api_signature(params: dict) -> str:
    sorted_values = [str(params[k]) for k in sorted(params.keys())]
    msg = "|".join(sorted_values)
    return hmac.new(FREEKASSA_API_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()


def _make_sci_sign(shop_id: str, amount: str, secret: str, currency: str, order_id: str) -> str:
    raw = f"{shop_id}:{amount}:{secret}:{currency}:{order_id}"
    return hashlib.md5(raw.encode()).hexdigest()


def _make_notification_sign(shop_id: str, amount: str, secret2: str, order_id: str) -> str:
    raw = f"{shop_id}:{amount}:{secret2}:{order_id}"
    return hashlib.md5(raw.encode()).hexdigest()


async def create_payment_url(user_id: int, pack_key: str, method: str = "card") -> dict:
    pack = CREDIT_PACKAGES.get(pack_key)
    if not pack:
        return {"ok": False, "error": "Неизвестный пакет"}

    if not FREEKASSA_SHOP_ID:
        return {"ok": False, "error": "Платёжная система не настроена"}

    payment_method = PAYMENT_METHODS.get(method)
    if not payment_method:
        return {"ok": False, "error": "Неизвестный метод оплаты"}

    order_id = f"{user_id}_{pack_key}_{int(time.time())}"
    amount = pack["amount"]

    _db.save_payment(order_id, user_id, pack_key, amount)

    if FREEKASSA_API_KEY:
        result = await _create_via_api(order_id, amount, payment_method["i"], user_id)
        if result["ok"]:
            return result

    pay_url = _create_sci_url(order_id, amount, payment_method["i"])
    logger.info("FreeKassa SCI URL created: order=%s, user=%s, pack=%s, method=%s", order_id, user_id, pack_key, method)
    return {"ok": True, "pay_url": pay_url, "order_id": order_id}


async def _create_via_api(order_id: str, amount: float, payment_system_id: int, user_id: int) -> dict:
    params = {
        "shopId": int(FREEKASSA_SHOP_ID),
        "nonce": _next_nonce(),
        "paymentId": order_id,
        "i": payment_system_id,
        "email": f"user{user_id}@picgenai.com",
        "ip": "127.0.0.1",
        "amount": amount,
        "currency": "RUB",
    }
    params["signature"] = _make_api_signature(params)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{FK_API_URL}/orders/create",
                json=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
                logger.info("FreeKassa API response: %s", data)

                if data.get("type") == "success" and data.get("location"):
                    return {
                        "ok": True,
                        "pay_url": data["location"],
                        "order_id": order_id,
                    }
                else:
                    error_msg = data.get("msg") or data.get("message") or str(data)
                    logger.warning("FreeKassa API error: %s", error_msg)
                    return {"ok": False, "error": error_msg}
    except Exception as e:
        logger.error("FreeKassa API request failed: %s", e)
        return {"ok": False, "error": str(e)}


def _create_sci_url(order_id: str, amount: float, payment_system_id: int) -> str:
    amount_str = f"{amount:.2f}"
    currency = "RUB"
    sign = _make_sci_sign(FREEKASSA_SHOP_ID, amount_str, FREEKASSA_SECRET1, currency, order_id)
    return (
        f"https://pay.fk.money/"
        f"?m={FREEKASSA_SHOP_ID}"
        f"&oa={amount_str}"
        f"&o={order_id}"
        f"&s={sign}"
        f"&currency={currency}"
        f"&i={payment_system_id}"
    )


def verify_notification_sign(data: dict) -> bool:
    merchant_id = str(data.get("MERCHANT_ID", ""))
    amount = str(data.get("AMOUNT", ""))
    order_id = str(data.get("MERCHANT_ORDER_ID", ""))
    received_sign = str(data.get("SIGN", ""))

    if not all([merchant_id, amount, order_id, received_sign]):
        return False

    expected_sign = _make_notification_sign(merchant_id, amount, FREEKASSA_SECRET2, order_id)
    return expected_sign == received_sign
