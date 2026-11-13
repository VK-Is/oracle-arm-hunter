# 🚀 Oracle Cloud Always Free ARM Hunter

Автоматичний пошук та створення безплатного сервера **ARM Ampere A1 (VM.Standard.A1.Flex)** в Oracle Cloud (до 4 oCPU та 24 GB RAM).

У проекті доступні **два незалежні скрипти**:
1. **`deploy_arm.py`** — для локального запуску на вашому комп'ютері.
2. **`deploy_arm_actions.py`** — спеціальна хмарна версія для запуску через **GitHub Actions** (24/7 без потреби тримати ПК увімкненим, із щогодинними звітами у Telegram).

---

## ⚡ Огляд GitHub Actions версії (`deploy_arm_actions.py`)

- 🟢 **Безкоштовно та безлімітно**: на публічних репозиторіях GitHub Actions не обмежує кількість хвилин.
- 🔒 **100% захист секретів**: у коді немає жодних ключів. Усі чутливі дані завантажуються з **GitHub Secrets** і маскуються в логах (`***`).
- 💓 **Щогодинні сповіщення у Telegram (Heartbeat)**: щогодини бот звітує, що скрипт активний, скільки годин працює та скільки циклів перевірки пройдено.
- 🔄 **Безперервна робота 24/7**: скрипт працює сесіями по 5 годин (`MAX_RUN_TIME_MINUTES=300`) для дотримання лімітів GitHub Actions, після чого чисто передає естафету наступному запуску за розкладом cron або через `GH_PAT`.
- 🏁 **Автоматична зупинка**: щойно сервер створено (або якщо активний інстанс вже існує) — скрипт вітає в Telegram та зупиняє пошук.

---

## 📋 Необхідні секрети в GitHub (Repository Secrets)

Перейдіть у вашому репозиторії на GitHub:
**Settings** → **Secrets and variables** → **Actions** → натисніть **New repository secret**.

Створіть наступні секрети:

| Назва секрету | Що вставляти |
|---|---|
| `OCI_CONFIG` | Повний текстовий вміст конфігураційного файлу OCI (зверніть увагу на `key_file`) |
| `OCI_KEY` | Повний вміст приватного ключа API (`oci_api_key.pem`, включно з `-----BEGIN RSA PRIVATE KEY-----`) |
| `COMPARTMENT_ID` | OCID вашого Tenancy / Compartment (`ocid1.tenancy.oc1...`) |
| `SUBNET_ID` | OCID підмережі VCN (`ocid1.subnet.oc1...`) |
| `SSH_PUBLIC_KEY` | Публічний SSH-ключ для підключення до сервера (`ssh-rsa AAAAB3...`) |
| `TELEGRAM_BOT_TOKEN` | Токен вашого Telegram-бота від `@BotFather` |
| `TELEGRAM_CHAT_ID` | Ваш числовий Telegram Chat ID (наприклад, `296511752`) |
| `GH_PAT` *(опціонально)* | GitHub Personal Access Token (з правами `workflow` або `repo`) — дозволяє запускати наступний цикл миттєво без очікування розкладу cron |

---

### Приклад вмісту для секрету `OCI_CONFIG`

У секрет `OCI_CONFIG` вставте наступний текст (замініть на ваші ID), де `key_file` обов'язково вказує на `/home/runner/.oci/oci_api_key.pem`:

```ini
[DEFAULT]
user=ocid1.user.oc1..aaaaaaaayafoh34dopavkimcza3hyqxwinerzidj4dhjcxenqmqolc2wzu2a
fingerprint=77:d9:d2:76:9c:8a:26:4a:04:23:f9:49:cf:49:d8:5a
tenancy=ocid1.tenancy.oc1..aaaaaaaanjwixx543a3zwpygf7pagvhf5alsbudpx3nup3ianp3smymmuqca
region=eu-frankfurt-1
key_file=/home/runner/.oci/oci_api_key.pem
```

---

## ▶️ Як запустити в GitHub Actions

1. Перейдіть у вкладку **Actions** вашого репозиторію.
2. У списку зліва оберіть **Oracle Cloud ARM Hunter**.
3. Натисніть кнопку **Run workflow** справа → оберіть гілку `master` → **Run workflow**.
4. Скрипт почне моніторити домени Oracle.
5. Розклад у `.github/workflows/deploy_arm.yml` автоматично запускатиме перевірку кожні кілька годин, або скрипт сам перейде на наступне коло, якщо налаштовано `GH_PAT`.
6. Як тільки Oracle звільнить ARM-слот — сервер буде створено, а ви отримаєте сповіщення в Telegram!

---

## 💻 Локальний запуск (опціонально)

Якщо ви хочете запустити скрипт локально на своєму комп'ютері:
1. Створіть файл `.env` (скопіюйте з `.env.example`) та заповніть ваші змінні.
2. Запустіть:
   ```bash
   pip install -r requirements.txt
   python deploy_arm.py
   ```
Файл `.env` вже додано до `.gitignore`, тому він ніколи не потрапить у публічний репозиторій.

