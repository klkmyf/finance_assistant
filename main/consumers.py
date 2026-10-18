import json
from datetime import date
from decimal import Decimal, InvalidOperation
from django.db import transaction
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .ai import ask_grok
from .models import UserProfile, Category, Transaction


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("WebSocket подключен!")

    async def disconnect(self, close_code):
        print("WebSocket отключен")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get("message", "").strip()
            telegram_id = data.get("telegram_id")

            if not message:
                await self.send_reply("Напишите сообщение.")
                return

            if not telegram_id:
                await self.send_reply("Не удалось определить пользователя.")
                return

            telegram_id = int(telegram_id)

            user, transactions_context = await sync_to_async(
                self.load_user_context
            )(telegram_id)

            answer = await sync_to_async(ask_grok)(
                message,
                user_id=telegram_id,
                transactions_context=transactions_context
            )
            print("Ответ AI:", answer)
            ai_data = json.loads(answer)

            action = ai_data.get("action")
            reply = ai_data.get("reply", "Хорошо!")

            if action == "create_transaction":
                await sync_to_async(self.create_transactions)(
                    telegram_id,
                    ai_data.get("transactions", []),
                    message
                )

            elif action == "update_transaction":
                transaction_id = ai_data.get("transaction_id")
                updates = ai_data.get("updates", {})

                if not transaction_id or not updates:
                    reply = (
                        "Уточните, какую запись нужно изменить "
                        "и какие данные исправить."
                    )
                else:
                    result = await sync_to_async(
                        self.update_transaction
                    )(
                        telegram_id,
                        transaction_id,
                        updates
                    )
                    if result:
                        reply = result

            elif action == "delete_transaction":
                import re

                delete_command = re.search(
                    r"\b(удал\w*|убер\w*|сотр\w*|отмен\w*|"
                    r"аннулиру\w*|не записывай)\b",
                    message.lower()
                )

                transaction_id = ai_data.get("transaction_id")
                if not delete_command:
                    reply = (
                        "Для удаления записи нужно явно попросить "
                        "меня удалить её."
                    )
                elif not transaction_id:
                    reply = (
                        "Не удалось определить нужную запись. "
                        "Уточните, какую транзакцию удалить."
                    )
                else:
                    result = await sync_to_async(
                        self.delete_transaction
                    )(
                        telegram_id,
                        transaction_id
                    )
                    if result:
                        reply = result

            await self.send_reply(reply)

        except (ValueError, TypeError):
            await self.send_reply("Проверьте данные сообщения.")

        except json.JSONDecodeError:
            print("ОШИБКА: получен невалидный JSON")
            await self.send_reply(
                "Не удалось обработать ответ ИИ. Попробуйте ещё раз."
            )

        except Exception as e:
            print("ОШИБКА:", e)
            await self.send_reply(
                "Произошла ошибка при обработке сообщения."
            )

    async def send_reply(self, message):
        await self.send(text_data=json.dumps({
            "message": message
        }, ensure_ascii=False))

    def load_user_context(self, telegram_id):
        user = UserProfile.objects.filter(
            telegram_id=telegram_id
        ).first()

        if not user:
            return None, []

        transactions = Transaction.objects.filter(
            user=user
        ).select_related("category").order_by(
            "-date", "-created_at"
        )[:20]

        context = []

        for item in transactions:
            context.append({
                "transaction_id": item.id,
                "type": item.transaction_type,
                "amount": str(item.amount),
                "category": item.category.name if item.category else "Другое",
                "date": item.date.isoformat(),
                "raw_text": item.raw_text or ""
            })
        return user, context

    def create_transactions(self, telegram_id, items, message):
        if not items:
            return

        user, _ = UserProfile.objects.get_or_create(
            telegram_id=telegram_id
        )
        with transaction.atomic():
            for item in items:
                transaction_type = item.get("type")
                if transaction_type not in ("income", "expense"):
                    continue

                try:
                    amount = Decimal(str(item["amount"]))
                    operation_date = date.fromisoformat(item["date"])
                except (KeyError, ValueError, InvalidOperation, TypeError):
                    continue

                if not amount.is_finite() or amount <= 0:
                    continue

                category = self.get_category(
                    item.get("category", "other")
                )

                Transaction.objects.create(
                    user=user,
                    transaction_type=transaction_type,
                    amount=amount,
                    category=category,
                    raw_text=message,
                    date=operation_date
                )
                print(
                    "Транзакция сохранена:",
                    transaction_type,
                    amount,
                    category.name if category else "Другое"
                )

    def update_transaction(self, telegram_id, transaction_id, updates):
        allowed_fields = {
            "amount", "type", "category", "date"
        }
        if not isinstance(updates, dict):
            return "Не удалось определить, какие данные изменить."

        if not set(updates).issubset(allowed_fields) or not updates:
            return "Получены недопустимые поля для изменения."

        try:
            transaction_id = int(transaction_id)
        except (ValueError, TypeError):
            return "Не удалось определить номер транзакции."

        item = Transaction.objects.filter(
            user__telegram_id=telegram_id,
            pk=transaction_id
        ).first()

        if not item:
            return "Транзакция не найдена."

        with transaction.atomic():
            if "amount" in updates:
                try:
                    amount = Decimal(str(updates["amount"]))
                    if not amount.is_finite() or amount <= 0:
                        return "Сумма должна быть больше нуля."
                    item.amount = amount
                except (InvalidOperation, ValueError, TypeError):
                    return "Не удалось распознать новую сумму."

            if "type" in updates:
                if updates["type"] not in ("income", "expense"):
                    return "Не удалось распознать тип операции."
                item.transaction_type = updates["type"]

            if "category" in updates:
                item.category = self.get_category(updates["category"])

            if "date" in updates:
                try:
                    item.date = date.fromisoformat(updates["date"])
                except (ValueError, TypeError):
                    return "Не удалось распознать дату."

            item.save()
        return "Транзакция успешно изменена."

    def delete_transaction(self, telegram_id, transaction_id):
        try:
            transaction_id = int(transaction_id)
        except (ValueError, TypeError):
            return "Не удалось определить номер транзакции."

        item = Transaction.objects.filter(
            user__telegram_id=telegram_id,
            pk=transaction_id
        ).first()

        if not item:
            return "Транзакция не найдена."

        amount = item.amount
        category = item.category.name if item.category else "Другое"
        operation_date = item.date

        item.delete()
        return (
            f"Транзакция удалена: {category}, "
            f"{amount} ₸ от {operation_date:%d.%m.%Y}."
        )
    def get_category(self, category_name):
        categories = {
            "food": "Продукты питания",
            "restaurants": "Рестораны и кафе",
            "transport": "Транспорт",
            "taxi": "Такси",
            "shopping": "Покупки",
            "clothing": "Одежда",
            "beauty": "Красота",
            "health": "Здоровье",
            "housing": "Жильё",
            "utilities": "Коммунальные услуги",
            "entertainment": "Развлечения",
            "travel": "Путешествия",
            "education": "Образование",
            "subscriptions": "Подписки",
            "communication": "Связь",
            "electronics": "Электроника",
            "gifts": "Подарки",
            "sport": "Спорт",
            "pets": "Животные",
            "finance": "Финансовые расходы",
            "salary": "Зарплата",
            "other": "Другое"
        }
        name = categories.get(category_name, "Другое")
        category = Category.objects.filter(name=name).first()
        if category is None:
            category, _ = Category.objects.get_or_create(name="Другое")
        return category
