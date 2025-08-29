# Athletic Manager — інсталяція з нуля (локальний запуск)

Ці інструкції відтворювані та точні. Вони встановлюють проект локально на SQLite, зі збіркою стилів Tailwind і роботою OTP через Gmail API.

## 1. Необхідне ПЗ
- Python 3.12
- Node.js 18
- npm (постачається з Node.js)
- gettext (для i18n: `xgettext`, `msgfmt` у PATH)
- Git

## 2. Клонування репозиторію
```bash
git clone <URL_ВАШОГО_РЕПО> AthleticManager
cd AthleticManager
```

## 3. Віртуальне середовище та залежності
### Windows PowerShell
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```
### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Node-залежності (Tailwind)
```bash
npm install
```

## 5. Файл середовища
Створи файл `.env` у корені проєкту з **точно** таким вмістом (заміни `CHANGE_ME` на випадковий рядок мінімум 50 символів):
```env
DJANGO_SECRET_KEY=CHANGE_ME_______________________________________________
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

TIME_ZONE=America/Chicago
LANGUAGE_CODE=uk
USE_I18N=True

STATIC_URL=/static/
MEDIA_URL=/media/
```
> Цей проєкт використовує SQLite за замовчуванням. Додаткові БД не налаштовуються в цій інструкції.

## 6. Міграції та суперкористувач
```bash
python manage.py migrate
python manage.py createsuperuser
```

## 7. Авторизація OTP через Gmail API
1. Відкрий **Google Cloud Console** → створити проект → **APIs & Services** → **Enable APIs and Services** → увімкнути **Gmail API**.
2. **OAuth consent screen**: тип **External** → додай свою Gmail-адресу у **Test users**.
3. **Credentials** → **Create Credentials** → **OAuth client ID** → тип **Desktop app**.
4. Завантаж `credentials.json` і поклади **у корінь репозиторію**.
5. Перший запуск надсилання коду ініціює OAuth-авторизацію і створить `token.json` поряд із `credentials.json`.
6. Обидва файли залишаються локальними та **не комітяться у git**.

## 8. Збірка стилів (сервер стилів у режимі розробки)
У **окремому** терміналі:
```bash
npm run dev
```

## 9. Компіляція локалізацій
```bash
django-admin makemessages -l uk -l en
django-admin compilemessages
```

## 10. Запуск сервера
```bash
python manage.py runserver
```
Відкрий: `http://127.0.0.1:8000/`  
Адмінка: `http://127.0.0.1:8000/admin/`

---

## Примітки, що стосуються коду
- Проєкт використовує JWT (SimpleJWT) для виставлення куків у `dashboard/views.py`. Залежності вже у `requirements.txt`.
- Не використовуй змінну `_` як «заглушку» (наприклад, `user, created = ...`), оскільки `_` — це alias перекладача.
