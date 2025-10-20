# chunking.py (in src/)
from pathlib import Path
import re
import os
from typing import List, Dict, Callable, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter

SRC = Path(__file__).resolve().parent          # .../yourproj/src
ROOT = SRC.parent                               # .../yourproj

class Text_Chunking:
    def __init__(self):
        self.documents = []
        self.ids = []
        self.metadata = []
        self.embeddings = []
        self.drive_dir = ROOT / "g-drive-docs"

    def execute_chunking(self):
        self.slide_chunks = self.chunk_slides()
        self.doc_chunks = self.chunk_docs()
    
    def embedding(self, text):
        # Function to get embeddings using Hugging Face model
        from transformers import AutoTokenizer, AutoModel
        import torch
        tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
        model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
        inputs = tokenizer(text, padding=True, truncation=True, return_tensors="pt")
        with torch.no_grad():
            embeddings = model(**inputs).last_hidden_state.mean(dim=1)
        return embeddings
        # Index documents

    @staticmethod
    def normalize(text: str) -> str:
        """Normalize text by collapsing newlines and removing trailing spaces."""
        text = re.sub(r"\n{3,}", "\n\n", text)  # collapse 3+ newlines → 2
        text = re.sub(r"[ \t]+\n", "\n", text)  # strip trailing spaces before newline
        return text.strip()

    def _process_directory(
        self,
        subdir: str,
        chunk_processor: Callable[[str, Path, str], List[Dict]]
    ) -> List[Dict]:
        """
        Generic method to process files in a directory.
        
        Args:
            subdir: Subdirectory name ('docs' or 'presentations')
            chunk_processor: Function that takes (text, path, filename) and returns chunks
        """
        base = (self.drive_dir / subdir).resolve()
        if not base.is_dir():
            raise FileNotFoundError(f"{subdir.capitalize()} folder not found: {base}")

        chunks = []
        for root_path, _, files in os.walk(base):
            root_path = Path(root_path)
            for name in files:
                if not name.lower().endswith(".txt"):
                    continue
                path = root_path / name
                try:
                    text = path.read_text(encoding="utf-8")
                    text = self.normalize(text)
                    chunks.extend(chunk_processor(text, path, name))
                except Exception as e:
                    print(f"⚠️  Skipping {path}: {e}")
        
        return chunks

    def chunk_slides(self) -> List[Dict]:
        """Chunk slides based on '=== Slide N ===' separators."""
        def process_slides(text: str, path: Path, filename: str) -> List[Dict]:
            # Split by slide markers
            slide_sections = re.split(r"=== Slide \d+ ===", text)
            
            for i, section in enumerate(slide_sections):
                section = section.strip()
                if not section:  # Skip empty sections
                    continue
                self.ids.append(f"{path}:{i}")
                self.documents.append(section)
                self.embeddings.append(get_embedding(section))
                self.metadata.append({
                        "file_path": str(path),
                        "chunk_index": i,
                        "chunk_total": len(slide_sections),
                        "filename": filename
                    })


        self._process_directory("presentations", process_slides)

    def chunk_docs(self) -> List[Dict]:
        """Chunk documents using RecursiveCharacterTextSplitter."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            add_start_index=True,
            separators=[""],
            keep_separator=False,
            strip_whitespace=True,
        )
        
        def process_docs(text: str, path: Path, filename: str) -> List[Dict]:
            text_chunks = splitter.split_text(text)
            
            for i, chunk in enumerate(text_chunks):
                self.ids.append(f"{path}:{i}")
                self.documents.append(text_chunks)
                self.embeddings.append(get_embedding(chunk))
                self.metadata.append({
                        "file_path": str(path),
                        "chunk_index": i,
                        "chunk_total": len(text_chunks),
                        "filename": filename
                    })

        
        self._process_directory("docs", process_docs)

def get_embedding(self, text):
        # Function to get embeddings using Hugging Face model
        from transformers import AutoTokenizer, AutoModel
        import torch
        tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
        model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
        inputs = tokenizer(text, padding=True, truncation=True, return_tensors="pt")
        with torch.no_grad():
            embeddings = model(**inputs).last_hidden_state.mean(dim=1)
        return embeddings
        # Index documents

if __name__ == "__main__":
    tc = Text_Chunking()
    tc.execute_chunking()   
    breakpoint()
    print(f"Produced {len(tc.doc_chunks) + len(tc.slide_chunks)} chunks")   