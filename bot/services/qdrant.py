from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from bot.config import settings
from typing import List, Dict

class QdrantService:
    def __init__(self):
        self.client = AsyncQdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY,  # None => no auth (unchanged)
        )
        self.collection_name = "regulations"
        self.vector_size = 1536  # text-embedding-3-small dimension

    async def ensure_collection(self):
        """Creates collection if it doesn't exist."""
        collections = await self.client.get_collections()
        exists = any(c.name == self.collection_name for c in collections.collections)
        
        if not exists:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE
                )
            )

    async def recreate_collection(self):
        """Deletes and recreates the collection for a fresh start."""
        collections = await self.client.get_collections()
        exists = any(c.name == self.collection_name for c in collections.collections)
        
        if exists:
            await self.client.delete_collection(self.collection_name)
            
        await self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.vector_size,
                distance=models.Distance.COSINE
            )
        )

    async def upsert_chunks(self, chunks: List[str], vectors: List[List[float]]):
        """Upserts text chunks and their vectors."""
        points = [
            models.PointStruct(
                id=idx,  # Simple integer ID for now, or hash
                vector=vector,
                payload={"text": chunk}
            )
            for idx, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]
        
        # Batch upsert
        if points:
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

    async def search(self, query_vector: List[float], limit: int = 5) -> List[str]:
        """Searches for similar chunks."""
        results = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit
        )
        return [hit.payload["text"] for hit in results]
