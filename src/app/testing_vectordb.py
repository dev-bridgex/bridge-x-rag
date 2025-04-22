from app.stores.vectordb.providers import QdrantDBProvider


# --- Example Usage (for demonstration) ---
async def test_qdrant(provider: QdrantDBProvider):
    # Example: Connect to local Qdrant
    
    # Or connect to memory: provider = QdrantDBProvider(db_path=":memory:")

    async with provider: # Uses async context manager (__aenter__ / __aexit__)
        collection_name = "my_async_test_collection"
        embedding_size = 1024 # Example size

        # Create or reset collection
        created = await provider.create_collection(collection_name, embedding_size, do_reset=False)
        print(f"Collection created/reset: {created}")

        if await provider.is_collection_exists(collection_name):
            print("Collection exists.")

            # Insert some data
            await provider.insert_one(collection_name, "This is document 1", [0.1]*embedding_size, {"source": "doc1"})
            await provider.insert_many(
                collection_name,
                texts=["Doc 2 text", "Doc 3 text"],
                vectors=[[0.2]*embedding_size, [0.3]*embedding_size],
                metadatas=[{"source": "doc2"}, {"source": "doc3"}],
                # record_ids provided by caller (or generated if None)
            )

            # Search
            search_results = await provider.search_by_vector(collection_name, [0.15]*embedding_size, limit=2)
            print(f"Search Results: \n {search_results}")
            # for res in search_results:
            #     print(f"  ID: {res['id']}, Score: {res['score']:.4f}, Text: {res['text']}")

            # Get info
            info = await provider.get_collection_info(collection_name)
            if info:
                print(f"Collection Info points_count: {info.points_count}")

            # Delete
            # deleted = await provider.delete_collection(collection_name)
            # print(f"Collection deleted: {deleted}")

