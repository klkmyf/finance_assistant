import os
import json
import requests
from datetime import date
from dotenv import load_dotenv
from .prompt import PROMPT

load_dotenv()

URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-20b"

chat_histories = {}
MAX_HISTORY = 12

def ask_grok(message, user_id=None, transactions_context=None):
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        print("ОШИБКА: GROQ_API_KEY не найден в .env")
        return json.dumps({
            "action": "no_financial_action",
            "reply": "Ошибка: API ключ не найден."
        }, ensure_ascii=False)

    today = date.today()

    system_prompt = PROMPT + f"""
        Сегодняшняя дата: {today.isoformat()}.
        Все даты определяй относительно этой даты.

        Если дата операции не указана, используй сегодняшнюю дату.
        Если дата уже известна из истории диалога, сохрани её.

        КОНТЕКСТ ТРАНЗАКЦИЙ ПОЛЬЗОВАТЕЛЯ:
        {json.dumps(transactions_context or [], ensure_ascii=False)}

        Это реальные записи из базы данных текущего пользователя.
        Используй только их transaction_id при редактировании и удалении.
        Никогда не придумывай ID.

        Если запись невозможно определить однозначно, используй ask_clarification.
        При редактировании передавай только поля, которые нужно изменить.
        Не меняй остальные поля транзакции.
        При удалении обязательно укажи transaction_id существующей записи.

        СОХРАНЕНИЕ КОНТЕКСТА:
        - История сообщений ниже относится к одному диалогу.
        - Если ты задал уточняющий вопрос, следующий ответ относится к нему,
        если пользователь явно не сменил тему.
        - Например, после вопроса о сумме ответ "1200" дополняет предыдущую операцию.
        - Не спрашивай повторно уже известную информацию.
        - Не создавай одну операцию повторно.
        - Никогда не выполняй финансовое действие только по собственной инициативе.
        """

    history_key = str(user_id) if user_id is not None else "default"
    history = chat_histories.setdefault(history_key, [])

    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": message}
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }

    try:
        print("Отправляем запрос в Groq...")

        response = requests.post(
            URL,
            headers=headers,
            json=data,
            timeout=60
        )

        print("GROQ STATUS:", response.status_code)
        print("GROQ RESPONSE:", response.text)

        if response.status_code != 200:
            return json.dumps({
                "action": "no_financial_action",
                "reply": "Не удалось получить ответ от ИИ."
            }, ensure_ascii=False)

        result = response.json()
        answer = result["choices"][0]["message"]["content"]


        json.loads(answer)

        history.extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": answer}
        ])

        if len(history) > MAX_HISTORY:
            del history[:-MAX_HISTORY]

        print("Ответ Groq получен!")
        return answer

    except requests.exceptions.Timeout:
        print("ОШИБКА: Groq слишком долго не отвечает")
        return json.dumps({
            "action": "no_financial_action",
            "reply": "ИИ слишком долго отвечает. Попробуйте ещё раз."
        }, ensure_ascii=False)

    except requests.exceptions.ConnectionError:
        print("ОШИБКА: не удалось подключиться к Groq")
        return json.dumps({
            "action": "no_financial_action",
            "reply": "Нет подключения к ИИ."
        }, ensure_ascii=False)

    except (ValueError, KeyError, IndexError, TypeError) as e:
        print("ОШИБКА формата ответа Groq:", e)
        return json.dumps({
            "action": "no_financial_action",
            "reply": "Не удалось обработать ответ ИИ. Попробуйте ещё раз."
        }, ensure_ascii=False)

    except Exception as e:
        print("ОШИБКА:", e)
        return json.dumps({
            "action": "no_financial_action",
            "reply": "Произошла ошибка при обращении к ИИ."
        }, ensure_ascii=False)


def clear_chat_history(user_id):
    chat_histories.pop(str(user_id), None)
