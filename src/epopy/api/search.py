from typing import List, Optional, Any, Dict, cast
from ..client import AsyncClient
from ..models import OPSResponse

class SearchError(Exception):
    pass

class SearchService:
    def __init__(self, client: AsyncClient):
        self.client = client
        
    async def published_data_search(
        self, 
        cql: str, 
        start: int = 1, 
        end: int = 25, 
        constituents: Optional[str] = None
    ) -> OPSResponse:
        """
        Search for published data.
        
        Args:
            cql: Contextual Query Language string (e.g. 'ti=plastic')
            start: Start index (1-based)
            end: End index
            constituents: Optional constituent (e.g. 'abstract')
        """
        range_header = f"{start}-{end}"
        params = {"q": cql}
        
        url = "/published-data/search"
        if constituents:
            url = f"{url}/{constituents}"
            
        data = await self.client.get_data(
            url, 
            params=params, 
            headers={"Range": range_header}
        )
        
        return OPSResponse(**data)

    async def search_patents(
        self,
        cql: str,
        start: int = 1,
        end: int = 25
    ) -> List[Any]:
        """
        Search and return a list of Patent objects.
        """
        from ..patent import Patent
        response = await self.published_data_search(cql, start=start, end=end)
        
        results: List[Patent] = []
        # Extract results from the search response
        search_res = response.world_patent_data.biblio_search
        if not search_res or not search_res.search_result:
            return results # type: ignore
            
        # The search_result structure can be complex, let's look at the XML mapping
        # In a real scenario, we'd navigate the dict carefully.
        # For now, let's assume we can find the numbers.
        data = cast(Dict[str, Any], search_res.search_result)
        # Navigate to the documents
        docs_raw = data.get("ops:publication-reference", [])
        docs: List[Any] = [docs_raw] if isinstance(docs_raw, dict) else cast(List[Any], docs_raw)
        
        for doc_item in docs:
            doc = cast(Dict[str, Any], doc_item)
            
            doc_id_raw = doc.get("document-id", {})
            doc_id = cast(Dict[str, Any], doc_id_raw[0] if isinstance(doc_id_raw, list) else doc_id_raw)
            
            val_data = doc_id.get("doc-number")
            num: Optional[str] = None
            if isinstance(val_data, dict):
                inner_val = cast(Dict[str, Any], val_data)
                num = cast(Optional[str], inner_val.get("$") or inner_val.get("#text"))
            else:
                num = cast(Optional[str], val_data)
            
            if num:
                cc_raw = doc_id.get("country", {})
                cc: Optional[str] = None
                if isinstance(cc_raw, dict):
                    cc = cast(Optional[str], cast(Dict[str, Any], cc_raw).get("$"))
                else:
                    cc = cast(Optional[str], cc_raw)
                
                kind_raw = doc_id.get("kind", {})
                kind: Optional[str] = None
                if isinstance(kind_raw, dict):
                    kind = cast(Optional[str], cast(Dict[str, Any], kind_raw).get("$"))
                else:
                    kind = cast(Optional[str], kind_raw)
                
                if cc and kind:
                    patent_num = f"{cc}.{num}.{kind}"
                    results.append(Patent(self.client, patent_num))
                else:
                    results.append(Patent(self.client, str(num)))
                    
        return results # type: ignore
