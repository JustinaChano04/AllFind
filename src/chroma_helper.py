# chroma_helper.py

import chromadb
from src.chunking import get_embedding
# Initialize Chroma DB
client = chromadb.Client()
collection = client.create_collection("document_collection")

def insert_db(ids: list, documents: list, embeddings: list):
    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings
    )

def query_db(question, collection, top_k=3):
     q_embeddings = get_embedding([question])
     results = collection.query(query_embeddings=q_embeddings.numpy().tolist(), n_results=top_k)
     return ''.join(results["documents"][0])


if __name__ == "__main__":
    from chunking import Text_Chunking
    tc = Text_Chunking()
    tc.execute_chunking()   
    embedding = get_embedding(tc.doc_chunks[0]["text"])

    question = "How to load dataset?"
    context = query_db(question, collection)
    breakpoint()