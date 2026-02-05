from typing import List, Optional, Any, Union, Dict
from pydantic import BaseModel, Field

class OPSReference(BaseModel):
    document_id: Any = Field(default=None, alias="document-id")
    
class PublicationReference(OPSReference):
    pass

class ApplicationReference(OPSReference):
    pass

class PriorityClaim(OPSReference):
    pass

class ExchangeDocument(BaseModel):
    country: Optional[str] = Field(default=None, alias="@country")
    doc_number: Optional[str] = Field(default=None, alias="@doc-number")
    kind: Optional[str] = Field(default=None, alias="@kind")
    family_id: Optional[str] = Field(default=None, alias="@family-id")
    bibliographic_data: Any = Field(default=None, alias="bibliographic-data")
    
    # We might need to make this more flexible as XML mapping can be tricky
    model_config = {"extra": "allow"}

class ExchangeDocuments(BaseModel):
    exchange_document: Union[ExchangeDocument, List[ExchangeDocument]] = Field(alias="exchange-document")

class BiblioSearch(BaseModel):
    total_result_count: int = Field(alias="@total-result-count")
    query: Optional[Any] = Field(alias="ops:query", default=None)
    search_result: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = Field(alias="ops:search-result", default=None)
    
class WorldPatentData(BaseModel):
    biblio_search: Optional[BiblioSearch] = Field(alias="ops:biblio-search", default=None)
    # Add other top-level elements as needed
    exchange_documents: Optional[ExchangeDocuments] = Field(alias="exchange-documents", default=None)
    
    model_config = {"extra": "allow"}

class OPSResponse(BaseModel):
    world_patent_data: WorldPatentData = Field(alias="ops:world-patent-data")
