from typing import List, Optional, Any, Dict, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from .client import AsyncClient

class Document:
    """Represents a document/image variant associated with a patent."""
    
    def __init__(
        self, 
        client: 'AsyncClient',
        description: str,
        link: str,
        formats: List[str],
        number_of_pages: Optional[int] = None,
        sections: Optional[List[Dict[str, Any]]] = None
    ):
        self.client = client
        self.description = description
        self.link = link
        self.formats = formats
        self.number_of_pages = number_of_pages
        self.sections = sections or []

    @property
    def name(self) -> str:
        """Alias for description as per user request."""
        return self.description

    @property
    def type(self) -> str:
        """Heuristic type based on description."""
        return self.description.lower()

    async def download(self, document_format: Optional[str] = None, range_position: int = 1) -> bytes:
        """
        Download the document content.
        
        Args:
            document_format: Override the format (e.g. 'application/pdf'). 
                           If None, uses the first available format.
            range_position: The page range/position to download.
        """
        if not document_format:
            document_format = self.formats[0] if self.formats else "application/pdf"
            
        return await self.client.published_data.download_image(
            self.link, 
            range_position=range_position, 
            document_format=document_format
        )

    def __repr__(self) -> str:
        return f"<Document name='{self.name}' pages={self.number_of_pages}>"

class Patent:
    """High-level abstraction for a Patent."""
    
    def __init__(self, client: 'AsyncClient', number: str, format: str = "docdb", type: str = "publication"):
        self.client = client
        self.number = number
        self.format = format
        self.type = type
        self._biblio: Optional[Dict[str, Any]] = None

    async def get_documents(self) -> List[Document]:
        """Fetch all available document instances for this patent."""
        await self.client.published_data.published_data(
            reference_type=self.type, # type: ignore
            input_format=self.format, # type: ignore
            number=self.number,
            endpoint="images"
        )
        
        # We need the raw data to extract document instances easily or update models
        # For now, let's use the raw data from client to build Document objects
        # as the models are still evolving.
        data = await self.client.get_data(
            f"/published-data/{self.type}/{self.format}/{self.number}/images"
        )
        
        root = data.get("ops:world-patent-data", {})
        doc_inquiry = root.get("ops:document-inquiry", {})
        inquiry_res = doc_inquiry.get("ops:inquiry-result", {})
        instances = cast(List[Dict[str, Any]], inquiry_res.get("ops:document-instance", []))
        
        if isinstance(instances, dict):
            instances = [instances]
            
        docs: List[Document] = []
        for inst_raw in instances:
            inst = cast(Dict[str, Any], inst_raw)
                
            formats_raw = inst.get("ops:document-format-options")
            formats_doc = cast(Dict[str, Any], formats_raw) if isinstance(formats_raw, dict) else {}
            formats = formats_doc.get("ops:document-format", [])
            if isinstance(formats, str):
                formats = [formats]
                
            sections_raw = inst.get("ops:document-section", [])
            sections = cast(List[Dict[str, Any]], sections_raw if isinstance(sections_raw, list) else [sections_raw] if isinstance(sections_raw, dict) else [])
                
            docs.append(Document(
                client=self.client,
                description=str(inst.get("@desc", "Unknown")),
                link=cast(str, inst.get("@link")),
                formats=cast(List[str], formats),
                number_of_pages=int(cast(str, inst.get("@number-of-pages"))) if inst.get("@number-of-pages") else None,
                sections=sections
            ))
        return docs

    def __repr__(self) -> str:
        return f"<Patent number='{self.number}'>"
