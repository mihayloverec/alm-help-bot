import logging
from bot.config import settings
from bot.services.gdocs import GDocsLoader
from bot.services.splitter import TextSplitter
from bot.services.openai_svc import OpenAIService
from bot.services.qdrant import QdrantService

logger = logging.getLogger(__name__)

class IndexerService:
    def __init__(self, qdrant: QdrantService, openai: OpenAIService, cache: "CacheService"):
        self.qdrant = qdrant
        self.openai = openai
        self.cache = cache
        self.loader = GDocsLoader(
            doc_id=settings.GOOGLE_DOC_ID,
            credentials_json=settings.GOOGLE_SERVICE_ACCOUNT_JSON
        )
        self.splitter = TextSplitter(chunk_size=3000, overlap=500)

    async def run_indexing(self):
        logger.info("Starting indexing process...")
        
        # 1. Load Text
        try:
            text = self.loader.load_text()
            logger.info(f"Loaded {len(text)} characters from GDocs.")
            await self.cache.set_full_text(text)
        except Exception as e:
            logger.error(f"Failed to load GDoc: {e}")
            return

        # 2. Split
        chunks = self.splitter.split_text(text)
        logger.info(f"Split text into {len(chunks)} chunks.")
        
        if not chunks:
            logger.warning("No chunks to index.")
            return

        # 3. Embed & Upsert
        try:
            # Recreate collection to remove old stale chunks
            await self.qdrant.recreate_collection()
            
            # Process in batches if needed, but for now simple all-in-one
            vectors = await self.openai.get_embeddings(chunks)
            await self.qdrant.upsert_chunks(chunks, vectors)
            logger.info("Indexing completed successfully.")
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
