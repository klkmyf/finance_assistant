import json
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
        data = json.loads(text_data)
        message = data["message"]

        try:
            answer = await sync_to_async(ask_grok)(
                message,
                user_id=self.scope["user"].id
            )

            print("Ответ AI:", answer)
            ai_data = json.loads(answer)

            action = ai_data.get("action")
            reply = ai_data.get("reply", "Хорошо!")

            if action == "create_transaction":

                transactions = ai_data.get("transactions", [])

                telegram_id = data.get("telegram_id")

                if not telegram_id:
                    print("ОШИБКА: telegram_id не передан")
                    reply = "Не удалось определить пользователя."

                else:
                    user, created = await sync_to_async(
                        UserProfile.objects.get_or_create
                    )(
                        telegram_id=telegram_id
                    )

                    for item in transactions:
                        category_name = item.get("category", "other")
                        category = await sync_to_async(
                            self.get_category
                        )(category_name)

                        await sync_to_async(
                            Transaction.objects.create
                        )(
                            user=user,
                            transaction_type=item["type"],
                            amount=item["amount"],
                            category=category,
                            raw_text=message,
                            date=item["date"]
                        )

                        print(
                            "Транзакция сохранена:",
                            item["type"],
                            item["amount"],
                            category.name
                        )

            await self.send(
                text_data=json.dumps({
                    "message": reply
                })
            )

        except json.JSONDecodeError:
            print("ОШИБКА: Groq вернул невалидный JSON")
            print("Ответ:", answer)

            await self.send(
                text_data=json.dumps({
                    "message": "ИИ вернул неправильный формат ответа."
                })
            )

        except Exception as e:

            print("ОШИБКА:", e)

            await self.send(
                text_data=json.dumps({
                    "message": "Ошибка: " + str(e)
                })
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
            category = Category.objects.get(name="Другое")

        return category
