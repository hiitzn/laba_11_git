**Дисциплина:** Методы и технологии программирования  
**Выполнил:** Симбирева Анастасия Андреевна  
**Группа:** 220032-11  
**Лабораторная работа №11:** " Контейнеризация мультиязычных приложений"  
**Вариант:** 1  

### Практические задания

#### Средняя сложность
Задание 1. Написать Dockerfile для Python-приложения

В репозитории изначально был прикреплен готовый REST API для управления меню кофейни. Построен на Flask + SQLite, покрыт тестами, готов к запуску в Docker.

| Слой | Технология |
|---|---|
| Framework | Flask 3.x |
| База данных | SQLite (stdlib) |
| Валидация | Dataclasses + кастомные схемы |
| Тесты | pytest |
| Контейнер | Docker (python:3.11-slim) |

---
## Быстрый старт
### Локально
```bash
pip install -r requirements.txt
python app.py
```
### Docker
```bash
docker build -t coffee__api .

# Без сохранения данных
docker run -p 5000:5000 coffee__api

# С volume (БД сохраняется между перезапусками)
docker run -p 5000:5000 -v coffee_data:/app/data coffee__api
```
Скриншот выполнения:
![Успешная сборка Docker образа](screenshots/ex_1_assemble_container.jpg)
Скриншот выполнения:
![Отображение запущенного контейнера в Docker Desktop](screenshots/ex_1_docker_desktop.png)
API доступен на `http://localhost:5000`.

---

## Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `DATABASE_URL` | `/app/data/coffee.db` | Путь к файлу SQLite |

---

## Эндпоинты

| Метод | URL | Описание |
|---|---|---|
| `GET` | `/drinks/` | Список всех напитков (новые первые) |
| `POST` | `/drinks/` | Создать напиток |
| `PUT` | `/drinks/<id>` | Обновить цену и/или описание |
| `DELETE` | `/drinks/<id>` | Удалить напиток |

### Формат запроса

**POST /drinks/**
```json
{ "name": "Espresso", "price": 2.5, "description": "Short and strong" }
```
`description` — опционально.

**PUT /drinks/\<id\>**
```json
{ "price": 3.0 }
```
Достаточно одного поля: `price` и/или `description`.

### Формат ответа

```json
{
  "status": "success",
  "data": { "id": 1, "name": "Espresso", "price": 2.5, "description": null, "created_at": "...", "updated_at": "..." },
  "error": ""
}
```

При ошибке `status` = `"error"`, `data` = `{}`, `error` содержит сообщение.
