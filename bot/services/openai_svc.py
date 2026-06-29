from openai import AsyncOpenAI
from bot.config import settings
from typing import List

class OpenAIService:
    def __init__(self):
        # Embeddings go to OpenAI directly — OpenRouter has no embeddings endpoint.
        self.embedding_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        # Chat completions are routed through OpenRouter (OpenAI-compatible API).
        self.chat_client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
        )
        self.model_chat = "openai/gpt-4.1-mini"
        self.model_embedding = "text-embedding-3-small"

    async def get_embedding(self, text: str) -> List[float]:
        """Generates embedding for the given text."""
        text = text.replace("\n", " ")
        response = await self.embedding_client.embeddings.create(
            input=[text],
            model=self.model_embedding
        )
        return response.data[0].embedding

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a list of texts (batch)."""
        # OpenAI has a limit on batch size, but for this scale it should be fine.
        # Clean newlines
        cleaned_texts = [t.replace("\n", " ") for t in texts]
        response = await self.embedding_client.embeddings.create(
            input=cleaned_texts,
            model=self.model_embedding
        )
        # Ensure order is preserved. response.data is a list of Embedding objects with 'index'
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]

    async def get_answer(self, question: str, context_chunks: List[str]) -> str:
        """
        Generates an answer using RAG.
        """
        context_str = "\n\n".join(context_chunks)
        
        system_prompt = (
            "Ты — дружелюбный и вежливый ассистент судьи Лиги Азии по спортивной мафии. "
            "Твоя задача — отвечать на вопросы, основываясь ИСКЛЮЧИТЕЛЬНО на предоставленном тексте регламента.\n\n"
            "ВАЖНЫЕ ИНСТРУКЦИИ:\n"
            "1. Понимай синонимы и аббревиатуры (ППК, Фол, Удаление и т.д.) исходя ИЗ ТЕКСТА.\n"
            "   ВАЖНО: \"ППК\" — это вид наказания (Присуждение Поражения/Победы), а НЕ просто \"Попытка получить преимущество\". Не путай причину и следствие.\n"
            "2. ЕСЛИ В ОТВЕТЕ ВСТРЕЧАЮТСЯ ССЫЛКИ НА НОМЕРА ПУНКТОВ (например, \"6.9.4\", \"6.10.5\") — ТЫ ОБЯЗАН НАЙТИ И ПРОЦИТИРОВАТЬ ИХ ТЕКСТ.\n"
            "   Рекурсивно раскрывай вложенные ссылки. Если пункт 6.10.5 ссылается на 6.9.4 — напиши, что сказано в 6.9.4.\n"
            "   ПРИМЕР:\n"
            "   Вместо: \"Нарушение п. 6.9.4\"\n"
            "   Пиши: \"Нарушение п. 6.9.4 (Оскорбление...)\"\n"
            "3. Если информации нет, ответь: 'Извините, в регламенте об этом ничего не сказано, может быть вам нужно написать в чат Судей'."
        )
        
        user_prompt = f"Контекст регламента:\n{context_str}\n\nВопрос судьи:\n{question}"

        response = await self.chat_client.chat.completions.create(
            model=self.model_chat,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0  # Strict answers
        )
        
        return response.choices[0].message.content
