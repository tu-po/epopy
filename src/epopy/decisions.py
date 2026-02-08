
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Any
import re

from lxml import etree

logger = logging.getLogger(__name__)

@dataclass
class DecisionMetadata:
    decision_id: str
    date_decision: Optional[str]
    board: Optional[str]
    keywords: List[str]
    headnotes: List[str]
    application_num: Optional[str]
    publication_num: Optional[str]
    title: Optional[str]
    ipc_classes: List[str]
    language: Optional[str]
    
@dataclass
class Decision:
    metadata: DecisionMetadata
    full_text: str
    facts: str
    reasons: str
    
class DecisionsParser:
    """
    Parser for EPO Decisions XML files (e.g. EPDecisions_September2025.xml).
    Uses streaming parsing to handle large files.
    """
    def __init__(self, xml_path: str | Path):
        self.xml_path = Path(xml_path)
        if not self.xml_path.exists():
            raise FileNotFoundError(f"XML file not found: {self.xml_path}")

    def parse_decision_code(self, code: str) -> Tuple[str, str, str]:
        """
        Parses a decision code like "T 3069/19" or "T 3069/2019".
        Returns (type_code, number, year).
        Year is normalized to YYYY.
        """
        # Regex to capture Type, Number, Year
        # T 3069/19 -> T, 3069, 19
        match = re.search(r"([A-Z])\s*(\d+)/(\d+)", code.strip())
        if not match:
            # Maybe formatted as T3069/19
             match = re.search(r"([A-Z])(\d+)/(\d+)", code.strip())
        
        if not match:
            raise ValueError(f"Invalid decision code format: {code}. Expected format like 'T 3069/19'")
            
        type_char = match.group(1)
        number = match.group(2)
        year = match.group(3)
        
        # Normalize year
        if len(year) == 2:
            y_int = int(year)
            if y_int > 50: 
                 year = f"19{year}"
            else:
                 year = f"20{year}"
        
        number = number.zfill(4)
        
        return type_char, number, year

    def find_decision(self, decision_code: str) -> Optional[Decision]:
        """
        Searches for a specific decision by its code (e.g. "T 3069/19").
        """
        target_type, target_num, target_year = self.parse_decision_code(decision_code)
        
        logger.info(f"Searching for decision: Type={target_type}, Num={target_num}, Year={target_year}")

        # Streaming parser
        context = etree.iterparse(self.xml_path, events=('end',), tag='ep-appeal-decision')
        
        for _, elem in context:
            try:
                # Check criteria
                
                # Check Case Num
                bib_data = elem.find('ep-appeal-bib-data')
                if bib_data is None: 
                    continue
                    
                case_num_elem = bib_data.find('ep-case-num')
                if case_num_elem is None:
                    continue

                # Code (Type)
                case_type = case_num_elem.get('code')
                
                # ep-appeal-num
                appeal_num = case_num_elem.find('ep-appeal-num')
                appeal_num_text = appeal_num.text if appeal_num is not None else ""
                
                # ep-year
                appeal_year = case_num_elem.find('ep-year')
                appeal_year_text = appeal_year.text if appeal_year is not None else ""
                
                if (case_type == target_type and 
                    appeal_num_text == target_num and 
                    appeal_year_text == target_year):
                    
                    logger.info("Found match!")
                    return self._extract_decision_data(elem, decision_code)
                
            finally:
                # Clear element to save memory
                elem.clear()
                parent = elem.getparent()
                if parent is not None:
                    while elem.getprevious() is not None:
                        del parent[0]
                    
        return None

    def _extract_decision_data(self, elem: Any, decision_id: str) -> Decision:
        # Note: 'elem' is an lxml Element, typed as Any because properly typing lxml is complex without stubs
        bib_data = elem.find('ep-appeal-bib-data')
        
        # Metadata
        date_decision: Optional[str] = None
        date_elem = bib_data.find('.//ep-date-of-decision/date')
        if date_elem is not None:
            date_decision = str(date_elem.text)
            
        board: Optional[str] = None
        board_elem = bib_data.find('ep-board-of-appeal-code')
        if board_elem is not None:
            board = str(board_elem.text)
            
        keywords: List[str] = []
        kw_elem = elem.find('ep-keywords')
        if kw_elem is not None:
            keywords = [str(k.text) for k in kw_elem.findall('keyword') if k.text]
            
        headnotes: List[str] = []
        hn_elem = elem.find('ep-headnote')
        if hn_elem is not None:
             headnotes = ["".join(p.itertext()) for p in hn_elem.findall('p')]
             
        app_num: Optional[str] = None
        app_ref = bib_data.find('application-reference/document-id/doc-number')
        if app_ref is not None:
            app_num = str(app_ref.text)
            
        pub_num: Optional[str] = None
        pub_ref = bib_data.find('publication-reference/document-id/doc-number')
        if pub_ref is not None:
            pub_num = str(pub_ref.text)
            
        title: Optional[str] = None
        title_elem = bib_data.find('invention-title')
        if title_elem is not None:
             title = "".join(title_elem.itertext())
            
        ipc_classes: List[str] = []
        # ipc...
        
        lang: Optional[str] = elem.get('lang')
        
        metadata = DecisionMetadata(
            decision_id=decision_id,
            date_decision=date_decision,
            board=board,
            keywords=keywords,
            headnotes=headnotes,
            application_num=app_num,
            publication_num=pub_num,
            title=title,
            ipc_classes=ipc_classes,
            language=lang
        )
        
        # Content
        # Facts
        summary_elem = elem.find('ep-summary-of-facts')
        facts_text = ""
        if summary_elem is not None:
             facts_text = "\n\n".join(["".join(p.itertext()) for p in summary_elem.findall('p')])
             
        # Reasons
        reasons_elem = elem.find('ep-reasons-for-decision')
        reasons_text = ""
        if reasons_elem is not None:
            reasons_text = "\n\n".join(["".join(p.itertext()) for p in reasons_elem.findall('p')])
            
        full_text = f"SUMMARY OF FACTS\n\n{facts_text}\n\nREASONS FOR THE DECISION\n\n{reasons_text}"
        
        return Decision(metadata=metadata, full_text=full_text, facts=facts_text, reasons=reasons_text)
