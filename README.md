# 🚀 Oracle Cloud Always Free ARM Hunter (GitHub Actions)

Автоматичний скрипт для пошуку та створення безплатного сервера **ARM Ampere A1 (VM.Standard.A1.Flex)** в Oracle Cloud (до 4 oCPU та 24 GB RAM) у хмарі GitHub Actions.

Працює **цілодобово 24/7** у **GitHub Actions на публічному репозиторії**:
- 🟢 **Безкоштовно та безлімітно**: для публічних репозиторіїв GitHub Actions надає необмежені безкоштовні хвилини.
- 🔒 **100% конфіденційність**: у цьому репозиторії немає жодного реального ключа чи ID. Усі дані зчитуються виключно через зашифровані **GitHub Secrets** і автоматично маскуються в логах (`***`).
- 💓 **Регулярний пульс у Telegram**: щогодини надсилається контрольне повідомлення про стан пошуку та час роботи.
- ♾️ **Обхід 6-годинного ліміту сесії**: скрипт працює сесіями по 5 годин (`MAX_RUN_TIME_MINUTES=300`), після чого чисто завершує роботу та автоматично перезапускається через розклад (cron) або через GitHub API (`GH_PAT`).

---

## 📋 Необхідні секрети в GitHub (Repository Secrets)

Перейдіть у вашому репозиторії на GitHub:  
**Settings** → **Secrets and variables** → **Actions** → натисніть **New repository secret**.

Створіть такі секрети:

| Назва секрету | Опис |
|---|---|
| `OCI_CONFIG` | Текстовий вміст конфігурації OCI (приклад нижче) |
| `OCI_KEY` | Вміст вашого приватного ключа API (`.pem`), включно з `-----BEGIN RSA PRIVATE KEY-----` |
| `COMPARTMENT_ID` | OCID вашого Tenancy / Compartment (`ocid1.tenancy.oc1...`) |
| `SUBNET_ID` | OCID підмережі VCN (`ocid1.subnet.oc1...`) |
| `SSH_PUBLIC_KEY` | Ваш публічний SSH-ключ для доступу до створеного сервера |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram-бота від `@BotFather` |
| `TELEGRAM_CHAT_ID` | Ваш числовий Telegram Chat ID |
| `GH_PAT` *(опціонально)* | GitHub Personal Access Token з правом `workflow` — для миттєвого перезапуску сесій без очікування cron |

---

### Приклад вмісту для секрету `OCI_CONFIG`

У секрет `OCI_CONFIG` вставте текст вашого OCI конфігу, де `key_file` вказує на шлях усередині runner-а:

```ini
[DEFAULT]
user=ocid1.user.oc1..aaaaaaayour_user_ocid
fingerprint=xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx
tenancy=ocid1.tenancy.oc1..aaaaaaayour_tenancy_ocid
region=eu-frankfurt-1
key_file=/home/runner/.oci/oci_api_key.pem
```

---

## ▶️ Як запустити

1. Перейдіть у вкладку **Actions** вашого репозиторію.
2. У списку зліва оберіть **Oracle Cloud ARM Hunter**.
3. Натисніть кнопку **Run workflow** справа → оберіть гілку `main` → **Run workflow**.
4. Скрипт надішле привітання у Telegram і почне регулярний пошук ARM-сервера.
