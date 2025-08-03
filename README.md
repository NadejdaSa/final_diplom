# 🛒 Marketplace API - Backend-приложение для автоматизации закупок

**Marketplace API** — серверная часть для маркетплейса, где магазины могут импортировать/экспортировать товары в YAML-формате, а пользователи — оформлять заказы.

## 🚀 Возможности

- Регистрация, подтверждение email, вход по токену
- Импорт товаров из YAML по ссылке
- Экспорт товаров в YAML по запросу
- Корзина и оформление заказов
- Celery + Redis для фоновых задач
- REST API (удобно тестировать через Postman)

## ⚙️ Технологии

- Python + Django  
- Django REST Framework  
- Celery + Redis  
- PostgreSQL  
- Docker + Docker Compose  
- YAML

## 🐳 Запуск через Docker Compose

```bash
git clone https://github.com/NadejdaSa/final_diplom
cd final_diplom

# Настрой .env (email, БД и т.д.)
docker-compose up --build

# Выполни миграции и создай суперпользователя
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser

## 🔗 Postman

[Коллекция для Postman](https://nadejdadawydowa.postman.co/workspace/Nadejda-Dawydowa%27s-Workspace~a3735341-1244-49e8-8e51-93ebcb29f92a/collection/46898581-d6b5e879-63c2-4960-992f-9f47a82ec5b1?action=share&creator=46898581) — все доступные запросы API