# SkillSwap API

Отдельный Django REST Framework бэкенд для React-приложения SkillSwap.
Стандартная модель Django `User` хранит email в полях `username` и `email`;
остальные данные пользователя находятся в связанной записи `Profile`.
Навыки, избранное, заявки и уведомления хранятся в SQLite.
Изображения хранятся в `media/`; в базе сохраняются относительные пути к ним.

## Локальный запуск

Нужен Python 3.12. В корне проекта:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

`migrate` создаёт таблицы **и загружает 15 городов, 6 категорий и 42 подкатегории**
через `api/migrations/0002_reference_data.py`. Команда
`python manage.py seed_reference` повторно сверяет эти справочники, не создавая дубликаты.
Проверка сервера: `GET http://127.0.0.1:8000/health/`.

Для админки: `python manage.py createsuperuser`, затем `/admin/`.
На запрос `Username` введите email и повторите его в поле `Email`.
Новых обычных пользователей создавайте через API регистрации.

## Авторизация

API использует только DRF `TokenAuthentication`. После входа или регистрации
фронт получает `token` и добавляет к защищённым запросам заголовок:

```http
Authorization: Token <token>
```

Для API не используются cookie-сессии и CSRF-заголовок. Админка Django работает
со своей сессией. Встроенный DRF-токен один на пользователя: выход удаляет его,
после следующего входа выдаётся новый. Для проверки командой используйте
отдельные учётные записи. В продакшене используйте HTTPS.

## API

Все пути начинаются с `/api/` и заканчиваются `/`. JSON используется везде,
кроме запросов с файлами, где нужен `multipart/form-data`.

| Метод | Путь | Авторизация | Результат |
| --- | --- | --- | --- |
| POST | `auth/register/` | нет | Пользователь, его навык и токен |
| POST | `auth/login/` | нет | `{token, user}` |
| POST | `auth/logout/` | да | Удалить токен |
| GET, PATCH | `me/` | да | Свой профиль, включая `has_unread_notifications` |
| GET | `cities/` | нет | Список городов |
| GET | `categories/` | нет | Категории с подкатегориями |
| GET | `users/` | нет | Все карточки пользователей с их единственным навыком |
| GET | `users/{user_id}/` | нет | Детальная страница пользователя |
| GET, POST, PATCH | `me/skill/` | да | Просмотреть, создать или изменить свой единственный навык |
| POST | `me/skill/images/` | да | Добавить фотографию навыка |
| DELETE | `me/skill/images/{id}/` | да | Удалить свою фотографию |
| GET | `favorites/` | да | Предложения избранных пользователей |
| PUT | `favorites/{user_id}/` | да | Установить `is_favorite: true/false` |
| POST | `exchange-requests/` | да | Предложить обмен пользователю |
| GET | `notifications/` | да | Все свои уведомления, новые первыми |
| POST | `notifications/read-all/` | да | Отметить все новые прочитанными |
| POST | `notifications/clear/` | да | Без тела; физически удалить только прочитанные |

Регистрация собирает три шага формы в **один заключительный запрос**:

```json
{
  "email": "anna@example.com",
  "password": "password123",
  "name": "Анна",
  "birth_date": "1998-04-21",
  "gender": "female",
  "city_id": 1,
  "about": "Люблю фотографию",
  "wanted_subcategory_ids": [1, 9],
  "teach_subcategory_id": 23,
  "skill_title": "Портретная фотография",
  "skill_description": "Научу снимать портреты"
}
```

Значения `gender`: `male`, `female`, `unspecified`. Для формы регистрации
загрузите города через `GET /api/cities/`, а категории и вложенные в них
подкатегории — через `GET /api/categories/`.

### Выбор категории и подкатегории на фронте

Используйте ответ `GET /api/categories/` как единственный источник списка
подкатегорий в форме. У каждой подкатегории в этом ответе есть `category_id`.

1. Один раз загрузите категории с вложенными подкатегориями.
2. Пока категория не выбрана, показывайте все подкатегории.
3. При выборе категории показывайте только её подкатегории. Если ранее
   выбранная подкатегория относится к другой категории, сбросьте её.
4. При выборе подкатегории найдите её `category_id` и автоматически выберите
   соответствующую категорию.

В состоянии каждой пары полей храните `categoryId` для отображения и
`subcategoryId` для отправки. В запрос регистрации отправляйте только ID
подкатегории: для навыка «Хочу научиться» —
`wanted_subcategory_ids: [subcategoryId]`, для навыка «Могу научить» —
`teach_subcategory_id: subcategoryId`. ID категории отправлять не нужно:
сервер определит её по подкатегории.

При отправке файлов используйте
`FormData`: добавьте `avatar`, повторите поле `skill_images` для каждой
фотографии и `wanted_subcategory_ids` для каждого ID. Не задавайте
`Content-Type` вручную: браузер добавит границу multipart. Допустимы JPG,
PNG, WebP до 5 МБ за файл. Количество фотографий навыка не ограничено.

При загрузке файлов весь запрос передаётся как один `FormData`, включая
текстовые поля. JSON отправляется только когда файлов нет:

```js
const body = new FormData();
body.append('email', email);
body.append('password', password);
body.append('name', name);
body.append('birth_date', birthDate);
body.append('gender', gender);
body.append('city_id', String(cityId));
body.append('about', about);
body.append('teach_subcategory_id', String(teachSubcategoryId));
body.append('skill_title', skillTitle);
body.append('skill_description', skillDescription);
for (const id of wantedSubcategoryIds) {
  body.append('wanted_subcategory_ids', String(id));
}
if (avatar) body.append('avatar', avatar);
for (const file of skillImages) body.append('skill_images', file);

await fetch(`${API_URL}/auth/register/`, { method: 'POST', body });
```

Для этого запроса не задавайте заголовок `Content-Type` вручную.

Ответ `GET /api/users/{user_id}/` содержит данные пользователя, его навык,
фотографии, `likes_count`, `is_favorite_by_me` и
`exchange_offered_by_me`. В `GET /api/users/` возвращаются те же поля для
всех пользователей с предложением навыка.
Авторизованный фронт должен передавать токен и в GET-запросах, чтобы два
последних поля отражали состояние текущего пользователя. У гостя они `false`.
Список пользователей, уведомлений, избранного и все справочники возвращаются
**целиком, без серверной пагинации**.

```json
{"target_user_id": 42}
```

Это тело `POST /api/exchange-requests/`. Запись об обмене связывает отправителя
и адресата. Первый запрос создаёт уведомление **отправителю** и возвращает 201.
Повторный возвращает 200 без новой заявки и без нового уведомления. При
открытии колокольчика `GET /api/notifications/` не помечает сообщения
прочитанными. Каждое уведомление об обмене содержит `target_user_id`:
кнопка «Перейти» открывает детальную страницу именно этого пользователя.
Если фронт сохраняет маршрут `/skill/:id`, параметром `:id` в нём служит
**ID пользователя**; данные страницы загружаются через `/api/users/{id}/`.
Красная точка исчезает после `read-all/`; `POST /api/notifications/clear/`
без тела удаляет только
прочитанные записи. `/api/me/` возвращает вычисленное поле
`has_unread_notifications`, отдельный запрос для точки не нужен.

Пример элемента `items` из `GET /api/notifications/`:

```json
{"id": 7, "type": "exchange_offered", "message": "Вы предложили обмен Ивану", "target_user_id": 42, "is_read": false}
```
