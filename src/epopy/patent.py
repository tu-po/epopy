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
        """
        Initialize a Document instance.

        Args:
            client: The AsyncClient instance.
            description: Description of the document (e.g., 'FullDocument', 'Drawing').
            link: API link to the document content.
            formats: List of available formats (e.g., ['application/pdf', 'image/tiff']).
            number_of_pages: Total number of pages in the document.
            sections: Optional list of specific sections within the document.
        """
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

    async def download(self, document_format: Optional[str] = None, range_position: Optional[int | str] = None) -> bytes:
        """
        Download the document content.
        
        Args:
            document_format: Override the format (e.g. 'application/pdf'). 
                           If None, uses the first available format.
            range_position: The page range/position to download. 
                          If None, defaults to "1-{number_of_pages}" if known, else "1".
        """
        if not document_format:
            document_format = self.formats[0] if self.formats else "application/pdf"
            
        # Case 1: Loop and Merge if full document requested and we have > 1 pages
        if range_position is None and self.number_of_pages and self.number_of_pages > 1 and "pdf" in document_format.lower():
            import asyncio
            from io import BytesIO
            from pypdf import PdfWriter, PdfReader
            
            # Sequential download with small delay and retries to avoid 403 Forbidden
            pages_content = []
            for i in range(1, self.number_of_pages + 1):
                # Basic retry logic for transient errors or rate limits
                last_exc = None
                for attempt in range(3):
                    try:
                        page_bytes = await self.client.published_data.download_image(
                            self.link, 
                            range_position=i,
                            document_format=document_format  # type: ignore
                        )
                        pages_content.append(page_bytes)
                        break
                    except Exception as e:
                        last_exc = e
                        # If we hit RobotDetected, we need a LONG wait
                        wait_time = 2 ** (attempt + 1)
                        if "RobotDetected" in str(e):
                            # Fair use block usually requires a significant pause
                            wait_time = 60 
                        
                        import asyncio
                        await asyncio.sleep(wait_time)
                else:
                    if last_exc:
                        raise last_exc
                
                # Base delay to respect Fair Use Policy
                await asyncio.sleep(2.0)
            
            # Merge
            merger = PdfWriter()
            for page_bytes in pages_content:
                try:
                    merger.append(PdfReader(BytesIO(page_bytes)))
                except Exception:
                    # Skip corrupt/empty pages to keep the final doc readable
                    pass
            
            output = BytesIO()
            merger.write(output)
            return output.getvalue()

        # Case 2: Standard single request (default or specific range)
        # Determine range
        final_range: int | str = 1
        if range_position is not None:
             final_range = range_position
            
        return await self.client.published_data.download_image(
            self.link, 
            range_position=final_range, 
            document_format=document_format
        )

    def __repr__(self) -> str:
        """Return a string representation of the Document."""
        return f"<Document name='{self.name}' pages={self.number_of_pages}>"

class Patent:
    """High-level abstraction for a Patent."""
    
    def __init__(self, client: 'AsyncClient', number: str, format: str = "docdb", type: str = "publication"):
        """
        Initialize a Patent instance.

        Args:
            client: The AsyncClient instance.
            number: The patent number (e.g., 'EP1234567').
            format: The number format ('docdb', 'epodoc', 'original').
            type: The reference type ('publication', 'application', 'priority').
        """
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
