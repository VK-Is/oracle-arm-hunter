#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ОПИС СКРИПТА:
Спеціалізована версія скрипта для запуску у середовищі GitHub Actions (CI/CD)
на публічному репозиторії без втрати приватності ключів.

Особливості:
- Усі конфіденційні дані зчитуються виключно через змінні оточення (GitHub Secrets).
- Вбудовані регулярні сповіщення (Heartbeat) у Telegram кожні 60 хв, щоб ви знали, що скрипт активний.
- Робота сесіями по 5 годин (MAX_RUN_TIME_MINUTES) для дотримання лімітів GitHub Actions.
- Автоматичний вихід при успішному створенні сервера або якщо активний сервер вже є.
"""

import os
import sys
import time
import json
import random
import logging
import urllib.request
import urllib.parse
import oci

# === НАЛАШТУВАННЯ ЛОГУВАННЯ ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("GitHubActionsHunter")

# === ЗЧИТУВАННЯ ПАРАМЕТРІВ ЗІ ЗМІННИХ ОТОЧЕННЯ (GITHUB SECRETS) ===
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

COMPARTMENT_ID = os.environ.get("COMPARTMENT_ID", "").strip()
SUBNET_ID = os.environ.get("SUBNET_ID", "").strip()
SSH_PUBLIC_KEY = os.environ.get("SSH_PUBLIC_KEY", "").strip()

OCPUS = float(os.environ.get("OCPUS", "2"))
MEMORY_IN_GBS = float(os.environ.get("MEMORY_IN_GBS", "12"))

CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "60"))
DOMAIN_SWITCH_DELAY = int(os.environ.get("DOMAIN_SWITCH_DELAY", "10"))
TOO_MANY_REQUESTS_BACKOFF = int(os.environ.get("TOO_MANY_REQUESTS_BACKOFF", "120"))

# Тривалість однієї сесії у хвилинах (за замовчуванням 300 хв = 5 годин)
MAX_RUN_TIME_MINUTES = int(os.environ.get("MAX_RUN_TIME_MINUTES", "300"))

# Періодичність контрольних сповіщень у Telegram (у хвилинах, за замовчуванням 60 хв)
HEARTBEAT_MINUTES = int(os.environ.get("HEARTBEAT_MINUTES", "60"))

INSTANCE_DISPLAY_NAME = os.environ.get("INSTANCE_NAME", f"free-arm-ga-{int(time.time())}")

CONFIG_FILE = os.environ.get("OCI_CONFIG_FILE", "/home/runner/.oci/config")
CONFIG_PROFILE = os.environ.get("OCI_CONFIG_PROFILE", "DEFAULT")


def set_github_output(key: str, value: str) -> None:
    """Записує змінну у GITHUB_OUTPUT для наступних кроків workflow."""
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output and os.path.isfile(gh_output):
        try:
            with open(gh_output, "a", encoding="utf-8") as f:
                f.write(f"{key}={value}\n")
        except Exception as e:
            log.warning(f"Не вдалося записати в GITHUB_OUTPUT: {e}")


def send_telegram(message: str) -> None:
    """Відправляє сповіщення у Telegram з автоматичним повтором при збої."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram не налаштовано — сповіщення пропущено.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }).encode("utf-8")

    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, data=payload, method="POST")
            urllib.request.urlopen(req, timeout=15)
            return
        except Exception as e:
            log.warning(f"Telegram помилка відправки (спроба {attempt}/3): {e}")
            if attempt < 3:
                time.sleep(2 ** attempt)


def check_telegram_connection() -> bool:
    """Перевіряє доступність бота та вітає користувача при старті."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.error("❌ Відсутні TELEGRAM_BOT_TOKEN або TELEGRAM_CHAT_ID!")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
    try:
        response = urllib.request.urlopen(url, timeout=15)
        data = json.loads(response.read().decode("utf-8"))
        if data.get("ok"):
            bot_name = data["result"].get("username", "bot")
            log.info(f"✅ Telegram-бот @{bot_name} на зв'язку.")
            send_telegram(
                f"🚀 <b>[GitHub Actions] Полювання на ARM розпочато!</b>\n"
                f"• Конфігурація: <code>{int(OCPUS)} oCPU / {int(MEMORY_IN_GBS)} GB RAM</code>\n"
                f"• Ліміт поточної сесії: <code>{MAX_RUN_TIME_MINUTES} хв</code>\n"
                f"• Інтервал перевірок: <code>{CHECK_INTERVAL}с</code>\n"
                f"🔔 <i>Контрольні звіти про роботу надсилатимуться щогодини.</i>"
            )
            return True
    except Exception as e:
        log.error(f"❌ Помилка підключення до Telegram: {e}")
    return False


# === ПЕРЕВІРКА ОБОВ'ЯЗКОВИХ ПАРАМЕТРІВ ===
def validate_inputs() -> None:
    missing = []
    if not COMPARTMENT_ID:
        missing.append("COMPARTMENT_ID")
    if not SUBNET_ID:
        missing.append("SUBNET_ID")
    if not SSH_PUBLIC_KEY:
        missing.append("SSH_PUBLIC_KEY")

    if missing:
        err = f"❌ [GitHub Actions] Відсутні обов'язкові секрети: {', '.join(missing)}"
        log.critical(err)
        send_telegram(err)
        set_github_output("instance_created", "false")
        sys.exit(1)


validate_inputs()

# === ІНІЦІАЛІЗАЦІЯ OCI КЛІЄНТІВ ===
log.info(f"Завантаження OCI конфігурації з: {CONFIG_FILE}")
try:
    config = oci.config.from_file(file_location=CONFIG_FILE, profile_name=CONFIG_PROFILE)
    compute_client = oci.core.ComputeClient(config)
    identity_client = oci.identity.IdentityClient(config)
except Exception as e:
    err = f"❌ [GitHub Actions] Помилка ініціалізації OCI: {e}"
    log.critical(err)
    send_telegram(err)
    set_github_output("instance_created", "false")
    sys.exit(1)


def get_ubuntu_arm_image_id() -> str:
    """Знаходить найсвіжіший сумісний ARM-образ Ubuntu."""
    log.info("Шукаємо ARM-образ Canonical Ubuntu...")
    images = compute_client.list_images(
        compartment_id=COMPARTMENT_ID,
        operating_system="Canonical Ubuntu",
        shape="VM.Standard.A1.Flex",
        sort_by="TIMECREATED",
        sort_order="DESC",
        limit=10,
    ).data

    if not images:
        raise RuntimeError("Не знайдено жодного образу Ubuntu для VM.Standard.A1.Flex!")

    for img in images:
        if "minimal" in img.display_name.lower():
            log.info(f"✅ Знайдено Minimal образ: {img.display_name} ({img.id})")
            return img.id

    img = images[0]
    log.info(f"✅ Знайдено образ: {img.display_name} ({img.id})")
    return img.id


def check_existing_instances() -> bool:
    """Перевіряє, чи не створено вже активний ARM-інстанс."""
    log.info("Перевірка наявних ARM-інстансів...")
    try:
        instances = compute_client.list_instances(compartment_id=COMPARTMENT_ID).data
        active = [
            i for i in instances
            if i.shape == "VM.Standard.A1.Flex"
            and i.lifecycle_state in ("RUNNING", "PROVISIONING", "STARTING")
        ]
        if active:
            names = [f"{i.display_name} ({i.lifecycle_state})" for i in active]
            msg = f"🎉 <b>[GitHub Actions] Знайдено вже існуючий активний ARM-інстанс!</b>\n{', '.join(names)}\nПодальший пошук зупинено."
            log.info(msg)
            send_telegram(msg)
            return True
    except oci.exceptions.ServiceError as e:
        log.warning(f"Не вдалося перевірити список інстансів: {e.message}")
    return False


def try_launch_instance(image_id: str, ad_names: list) -> bool:
    """Перебирає Availability Domains і робить спробу створення сервера."""
    for ad_name in ad_names:
        log.info(f"Спроба створення у домені {ad_name}...")

        launch_details = oci.core.models.LaunchInstanceDetails(
            compartment_id=COMPARTMENT_ID,
            availability_domain=ad_name,
            display_name=INSTANCE_DISPLAY_NAME,
            shape="VM.Standard.A1.Flex",
            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=float(OCPUS),
                memory_in_gbs=float(MEMORY_IN_GBS),
            ),
            image_id=image_id,
            create_vnic_details=oci.core.models.CreateVnicDetails(
                subnet_id=SUBNET_ID,
                assign_public_ip=True,
            ),
            metadata={"ssh_authorized_keys": SSH_PUBLIC_KEY},
            source_details=oci.core.models.InstanceSourceViaImageDetails(
                image_id=image_id,
                source_type="image",
                boot_volume_size_in_gbs=50,
            ),
        )

        max_retries = 3
        retry_delay = 5

        for attempt in range(1, max_retries + 1):
            try:
                response = compute_client.launch_instance(launch_details)
                instance = response.data
                msg = (
                    f"🎉🎉🎉 <b>[GitHub Actions] УСПІХ! ARM-СЕРВЕР СТВОРЕНО!</b>\n\n"
                    f"<b>ID:</b> <code>{instance.id}</code>\n"
                    f"<b>Домен:</b> <code>{ad_name}</code>\n"
                    f"<b>Конфігурація:</b> {int(OCPUS)} oCPU, {int(MEMORY_IN_GBS)} GB RAM\n"
                    f"<b>Стан:</b> <code>{instance.lifecycle_state}</code>\n\n"
                    f"Сервер піднімається, публічна IP з'явиться за пару хвилин в консолі Oracle."
                )
                log.info(msg)
                send_telegram(msg)
                set_github_output("instance_created", "true")
                return True

            except oci.exceptions.ServiceError as e:
                status = e.status
                code = str(e.code)
                msg_txt = str(e.message)

                # Немає ємності (нормальний статус дефіциту)
                if status == 500 or "Out of capacity" in msg_txt or "InternalError" in code:
                    log.info(f"  → Немає ємності в {ad_name} (HTTP {status}: {code}).")
                    break

                # Вичерпано квоту
                elif status == 400 and "LimitExceeded" in code:
                    err = (
                        "❌ <b>[GitHub Actions] LimitExceeded:</b> вичерпано ліміт акаунта на Always Free ARM!\n"
                        "Перевірте консоль Oracle."
                    )
                    log.critical(err)
                    send_telegram(err)
                    set_github_output("instance_created", "false")
                    sys.exit(1)

                # TooManyRequests
                elif status == 429:
                    wait = TOO_MANY_REQUESTS_BACKOFF + random.randint(0, 30)
                    log.warning(f"  → 429 TooManyRequests. Очікування {wait}с...")
                    time.sleep(wait)
                    continue

                else:
                    log.warning(f"  → Помилка (спроба {attempt}/{max_retries}) [{status}:{code}]: {msg_txt}")
                    if attempt < max_retries:
                        jitter = random.randint(0, 3)
                        time.sleep(retry_delay + jitter)
                        retry_delay *= 2

            except Exception as net_err:
                log.warning(f"  → Мережева помилка (спроба {attempt}/{max_retries}): {net_err}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    retry_delay *= 2

        jitter = random.randint(0, 5)
        time.sleep(DOMAIN_SWITCH_DELAY + jitter)

    return False


if __name__ == "__main__":
    log.info("=" * 60)
    log.info("  Oracle Cloud ARM Hunter (GitHub Actions Runner)")
    log.info("=" * 60)

    # 1. Перевірка Telegram
    check_telegram_connection()

    # 2. Пошук образу
    try:
        IMAGE_ID = get_ubuntu_arm_image_id()
    except Exception as e:
        err = f"❌ Не вдалося отримати ARM-образ: {e}"
        log.critical(err)
        send_telegram(err)
        set_github_output("instance_created", "false")
        sys.exit(1)

    # 3. Список доменів
    try:
        ads = identity_client.list_availability_domains(compartment_id=COMPARTMENT_ID).data
        AD_NAMES = [ad.name for ad in ads]
        log.info(f"Знайдено домени: {AD_NAMES}")
    except Exception as e:
        err = f"❌ Не вдалося отримати список доменів: {e}"
        log.critical(err)
        send_telegram(err)
        set_github_output("instance_created", "false")
        sys.exit(1)

    if not AD_NAMES:
        log.critical("Список доменів порожній!")
        set_github_output("instance_created", "false")
        sys.exit(1)

    # 4. Перевірка на вже створений сервер
    if check_existing_instances():
        set_github_output("instance_created", "true")
        sys.exit(0)

    log.info(f"Параметри: {OCPUS} oCPU, {MEMORY_IN_GBS} GB, пауза {CHECK_INTERVAL}с")
    log.info(f"Ліміт сесії: {MAX_RUN_TIME_MINUTES} хв. Heartbeat сповіщення кожні {HEARTBEAT_MINUTES} хв.")

    cycle = 0
    start_time = time.time()
    last_heartbeat_time = start_time

    # 5. Цикл моніторингу
    while True:
        cycle += 1
        now = time.time()
        elapsed = int(now - start_time)
        h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
        log.info(f"--- Цикл #{cycle} | Час роботи сесії: {h:02d}:{m:02d}:{s:02d} ---")

        # Відправка періодичного Heartbeat у Telegram (наприклад, щогодини)
        if (now - last_heartbeat_time) >= (HEARTBEAT_MINUTES * 60):
            send_telegram(
                f"💓 <b>[GitHub Actions] Моніторинг активний</b>\n"
                f"• Час роботи: <code>{h:02d} год {m:02d} хв</code>\n"
                f"• Пройдено циклів: <code>#{cycle}</code>\n"
                f"• Статус: <i>Всі 3 домени опитуються кожні {CHECK_INTERVAL}с. Вільних слотів поки немає, пошук триває невпинно...</i>"
            )
            last_heartbeat_time = now

        # Перевірка на досягнення ліміту поточної сесії (5 годин)
        if (now - start_time) >= (MAX_RUN_TIME_MINUTES * 60):
            log.info(f"⏱ Досягнуто ліміт сесії ({MAX_RUN_TIME_MINUTES} хв).")
            send_telegram(
                f"🔄 <b>[GitHub Actions] Сесію {MAX_RUN_TIME_MINUTES // 60} год завершено</b>\n"
                f"Пройдено <code>#{cycle}</code> циклів. Передаю чергу наступному запуску..."
            )
            set_github_output("instance_created", "false")
            sys.exit(0)

        success = try_launch_instance(IMAGE_ID, AD_NAMES)

        if success:
            log.info("🎉 Сервер успішно створено!")
            set_github_output("instance_created", "true")
            sys.exit(0)

        log.info(f"Усі домени зайняті. Наступна спроба через {CHECK_INTERVAL}с...")
        time.sleep(CHECK_INTERVAL)

