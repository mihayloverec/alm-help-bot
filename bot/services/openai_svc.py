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
            "КАК ОТВЕЧАТЬ (главное):\n"
            "1. Отвечай ПО СУТИ и КОНКРЕТНО на заданный вопрос. Не пересказывай весь контекст — "
            "выбери только те пункты, которые НАПРЯМУЮ относятся к вопросу, и дай прямой ответ.\n"
            "2. В контексте может быть лишний текст, не относящийся к вопросу, — ИГНОРИРУЙ его. "
            "Если несколько пунктов конкурируют, опирайся на наиболее точно подходящий к вопросу.\n"
            "3. Сначала дай короткий прямой ответ (1–3 предложения), затем при необходимости — "
            "ссылку на пункт(ы) и краткую цитату. Не лей воду.\n\n"
            "ТОЧНОСТЬ:\n"
            "4. Понимай синонимы и аббревиатуры (ППК, Фол, Удаление и т.д.) исходя ИЗ ТЕКСТА.\n"
            "   ВАЖНО: \"ППК\" — это вид наказания (Присуждение Поражения/Победы), а НЕ просто \"Попытка получить преимущество\". Не путай причину и следствие.\n"
            "5. ЕСЛИ В ОТВЕТЕ ВСТРЕЧАЮТСЯ ССЫЛКИ НА НОМЕРА ПУНКТОВ (например, \"6.9.4\", \"6.10.5\") и их текст есть в контексте — процитируй их суть.\n"
            "   ПРИМЕР: вместо \"Нарушение п. 6.9.4\" пиши \"Нарушение п. 6.9.4 (Оскорбление...)\".\n"
            "6. НИЧЕГО НЕ ВЫДУМЫВАЙ. Если в контексте нет ответа, напиши: "
            "'Извините, в регламенте об этом ничего не сказано, может быть вам нужно написать в чат Судей'."
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
