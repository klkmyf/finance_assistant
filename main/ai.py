
import os
import requests
from datetime import date, timedelta
from dotenv import load_dotenv
from .prompt import PROMPT

load_dotenv()

URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-20b"

# История диалогов: отдельная для каждого пользователя
chat_histories = {}
MAX_HISTORY = 12


def ask_grok(message, user_id=None):
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        print("ОШИБКА: GROQ_API_KEY не найден в .env")
        return "Ошибка: API ключ не найден."

    today = date.today()
    system_prompt = PROMPT + f"""

Сегодняшняя дата: {today.isoformat()}.
Вычисляй относительные даты относительно этой даты.
Если пользователь не указал дату операции, используй сегодняшнюю дату.

ОБЯЗАТЕЛЬНО СОХРАНЯЙ КОНТЕКСТ:
- История сообщений ниже является частью одного диалога.
- Если ты задал уточняющий вопрос, следующий ответ пользователя
  относится к этому вопросу, если пользователь явно не сменил тему.
- Например: «Вчера потратился на такси» → вопрос о сумме →
  «1200» означает расход на такси в размере 1200 за вчера.
- Не спрашивай повторно уже известную информацию.
- После получения недостающих данных объедини их с предыдущими
  данными и создай транзакцию, если информации достаточно.
- Не создавай одну и ту же транзакцию повторно.
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
        "temperature": 0.2
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
            return "Ошибка Groq. Подробности смотрите в консоли."

        result = response.json()
        answer = result["choices"][0]["message"]["content"]

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
        return "Ошибка: Groq слишком долго не отвечает."

    except requests.exceptions.ConnectionError:
        print("ОШИБКА: не удалось подключиться к Groq")
        return "Ошибка: нет подключения к Groq."

    except Exception as e:
        print("ОШИБКА:", e)
        return "Ошибка подключения к ИИ."

def clear_chat_history(user_id):
    chat_histories.pop(str(user_id), None)