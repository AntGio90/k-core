import re
import logging
from typing import List
from langchain.schema.document import Document
from langchain.text_splitter import TextSplitter, MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
import tiktoken
from cat.mad_hatter.decorators import hook

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def count_tokens(text: str) -> int:
    return len(tiktoken.get_encoding("cl100k_base").encode(text))

class ISO26262MarkdownSplitter(TextSplitter):
    def __init__(self, chunk_size=1000, chunk_overlap=200, part="ISO 26262-3"):
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.part = part

        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ],
            strip_headers=False,
        )

        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["#", "##", "###"],
            length_function=lambda x: len(self.tokenizer.encode(x)),
        ) 
        
    def _extract_section_info(self, header: str) -> tuple[str, str]:
        """
        Extract section number (e.g. '5.3.2') and keep full header as section_title.
        """
        clean_header = header.strip()
        match = re.search(r'(\d+(?:\.\d+)*)', clean_header)
    
        if match:
            section_number = match.group(1)
        else:
            section_number = "unknown"

        return section_number, clean_header

    def _split_keeping_tables(self, text: str) -> list[str]:
        table_block_pattern = r'(?:\|.*\n)+\|.*'
        parts, last_index = [], 0

        for match in re.finditer(table_block_pattern, text):
            start, end = match.span()
            if start > last_index:
                parts.append(text[last_index:start])
            parts.append(text[start:end])
            last_index = end
        if last_index < len(text):
            parts.append(text[last_index:])

        final_chunks = []
        for part in parts:
            if re.match(table_block_pattern, part):
                final_chunks.append(part.strip())
            else:
                final_chunks.extend(self.recursive_splitter.split_text(part))
        return final_chunks

    def split_text(self, text: str) -> list[str]:
        # This is required to fulfill the abstract base class requirement
        return self.recursive_splitter.split_text(text)

    def split_documents(self, documents: List[Document]) -> List[Document]:
        result = []
        for doc in documents:
            sections = self.markdown_splitter.split_text(doc.page_content)

            for section in sections:
                header = section.metadata.get("Header 2") or section.metadata.get("Header 3") or section.metadata.get("Header 1", "")
                section_number, section_title = self._extract_section_info(header)

                metadata = {
                    **doc.metadata,
                    "section_number": section_number,
                    "section_title": section_title,
                    "part": self.part,
                }

                if len(self.tokenizer.encode(section.page_content)) <= self._chunk_size:
                    document = Document(page_content=section.page_content, metadata=metadata)
                    log.info("*** \n Chunk (short):\n%s\nMetadata: %s\n **** \n", section.page_content[:300], metadata)
                    result.append(document)
                else:
                    sub_chunks = self._split_keeping_tables(section.page_content)
                    for i, chunk in enumerate(sub_chunks):
                        document = Document(page_content=chunk, metadata=metadata)
                        log.info("*** \n  Chunk %d:\n%s\nMetadata: %s\n **** \n ", i + 1, chunk[:300], metadata)
                        result.append(document)

        return result
    
# Cheshire Cat will call this to get the splitter
@hook  # default priority = 1
def rabbithole_instantiates_splitter(text_splitter, cat) -> TextSplitter:
    return ISO26262MarkdownSplitter(chunk_size=2000, chunk_overlap=800)                 