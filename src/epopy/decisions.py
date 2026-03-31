
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, List, Optional, Tuple, Any
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
    applicants: List[str] = field(default_factory=list)
    opponents: List[str] = field(default_factory=list)

@dataclass
class Decision:
    metadata: DecisionMetadata
    full_text: str
    facts: str
    reasons: str

class DecisionsParser:
    """
    Parser for EPO Decisions XML files (e.g. EPDecisions_March2026.xml).
    Uses streaming parsing to handle large files.
    """
    def __init__(self, xml_path: str | Path):
        self.xml_path = Path(xml_path)
        if not self.xml_path.exists():
            raise FileNotFoundError(f"XML file not found: {self.xml_path}")

    def parse_decision_code(self, code: str) -> Tuple[str, str, str]:
        """
        Parses a decision code like "T 3069/19" or "T 3069/2019".
        Returns (type_code, zero_padded_number, normalized_4digit_year).
        """
        match = re.search(r"([A-Z])\s*(\d+)/(\d+)", code.strip())
        if not match:
            match = re.search(r"([A-Z])(\d+)/(\d+)", code.strip())

        if not match:
            raise ValueError(f"Invalid decision code format: {code}. Expected format like 'T 3069/19'")

        type_char = match.group(1)
        number = match.group(2)
        year = match.group(3)

        if len(year) == 2:
            y_int = int(year)
            year = f"19{year}" if y_int > 50 else f"20{year}"

        number = number.zfill(4)
        return type_char, number, year

    def find_decision(self, decision_code: str) -> Optional[Decision]:
        """
        Searches for a specific decision by its code (e.g. "T 3069/19").
        """
        target_type, target_num, target_year = self.parse_decision_code(decision_code)
        logger.info(f"Searching for decision: Type={target_type}, Num={target_num}, Year={target_year}")

        context = etree.iterparse(self.xml_path, events=('end',), tag='ep-appeal-decision')
        for _, elem in context:
            try:
                bib_data = elem.find('ep-appeal-bib-data')
                if bib_data is None:
                    continue
                case_num_elem = bib_data.find('ep-case-num')
                if case_num_elem is None:
                    continue

                case_type = case_num_elem.get('code')
                appeal_num = case_num_elem.find('ep-appeal-num')
                appeal_num_text = appeal_num.text if appeal_num is not None else ""
                appeal_year = case_num_elem.find('ep-year')
                appeal_year_text = appeal_year.text if appeal_year is not None else ""

                if (case_type == target_type and
                        appeal_num_text == target_num and
                        appeal_year_text == target_year):
                    logger.info("Found match!")
                    return self._extract_decision_data(elem, decision_code)
            finally:
                elem.clear()
                parent = elem.getparent()
                if parent is not None:
                    while elem.getprevious() is not None:
                        del parent[0]

        return None

    def search_decisions(
        self,
        *,
        article: Optional[str] = None,
        applicant: Optional[str] = None,
        opponent: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        case_type: str = "T",
        limit: Optional[int] = None,
    ) -> Iterator[Decision]:
        """
        Streaming search through the XML. Yields Decision objects matching all
        supplied filters. All filters are ANDed together.

        Args:
            article:   EPC article string to find in keywords or full text,
                       e.g. "123(2)" or "56".
            applicant: Substring to match against applicant names (case-insensitive).
                       Also falls back to searching full bib-data text.
            opponent:  Substring to match against opponent names (case-insensitive).
            year_from: Minimum decision year (inclusive), based on ep-date-of-decision.
            year_to:   Maximum decision year (inclusive), based on ep-date-of-decision.
            case_type: Case type code, default "T" (technical appeals).
            limit:     Stop after yielding this many results.
        """
        article_re = re.compile(re.escape(article), re.IGNORECASE) if article else None
        applicant_re = re.compile(re.escape(applicant), re.IGNORECASE) if applicant else None
        opponent_re = re.compile(re.escape(opponent), re.IGNORECASE) if opponent else None

        yielded = 0
        context = etree.iterparse(self.xml_path, events=('end',), tag='ep-appeal-decision')

        for _, elem in context:
            try:
                if limit is not None and yielded >= limit:
                    break

                bib_data = elem.find('ep-appeal-bib-data')
                if bib_data is None:
                    continue

                case_num_elem = bib_data.find('ep-case-num')
                if case_num_elem is None:
                    continue

                # Filter by case type
                if case_num_elem.get('code') != case_type:
                    continue

                # Build canonical case ID
                appeal_num_elem = case_num_elem.find('ep-appeal-num')
                appeal_year_elem = case_num_elem.find('ep-year')
                if appeal_num_elem is None or appeal_year_elem is None:
                    continue
                appeal_num = appeal_num_elem.text or ""
                appeal_year = appeal_year_elem.text or ""
                decision_id = f"{case_type} {int(appeal_num)}/{appeal_year[-2:]}"

                # Filter by decision date year
                if year_from is not None or year_to is not None:
                    date_elem = bib_data.find('.//ep-date-of-decision/date')
                    if date_elem is None or not date_elem.text:
                        continue
                    try:
                        dec_year = int(date_elem.text[:4])
                    except ValueError:
                        continue
                    if year_from is not None and dec_year < year_from:
                        continue
                    if year_to is not None and dec_year > year_to:
                        continue

                # Filter by applicant (structured names first, full-text fallback)
                if applicant_re is not None:
                    app_names = [
                        "".join(n.itertext())
                        for n in bib_data.findall(
                            './/ep-applicant-addresses/ep-applicant-address/addressbook/name'
                        )
                    ]
                    if not any(applicant_re.search(n) for n in app_names):
                        # Fallback: search whole bib text (catches older entries)
                        if not applicant_re.search("".join(bib_data.itertext())):
                            continue

                # Filter by opponent
                if opponent_re is not None:
                    opp_names = [
                        "".join(n.itertext())
                        for n in bib_data.findall(
                            './/ep-opponent-addresses/ep-opponent-address/addressbook/name'
                        )
                    ]
                    if not any(opponent_re.search(n) for n in opp_names):
                        if not opponent_re.search("".join(bib_data.itertext())):
                            continue

                # Filter by article — check keywords first (fast), then full text
                if article_re is not None:
                    matched_article = False
                    kw_elem = elem.find('ep-keywords')
                    if kw_elem is not None and article_re.search("".join(kw_elem.itertext())):
                        matched_article = True
                    if not matched_article:
                        for section_tag in ('ep-summary-of-facts', 'ep-reasons-for-decision'):
                            section = elem.find(section_tag)
                            if section is not None and article_re.search("".join(section.itertext())):
                                matched_article = True
                                break
                    if not matched_article:
                        continue

                decision = self._extract_decision_data(elem, decision_id)
                yield decision
                yielded += 1

            finally:
                elem.clear()
                parent = elem.getparent()
                if parent is not None:
                    while elem.getprevious() is not None:
                        del parent[0]

    def _extract_decision_data(self, elem: Any, decision_id: str) -> Decision:
        """Extract all data from a matched ep-appeal-decision element."""
        bib_data = elem.find('ep-appeal-bib-data')

        # Date
        date_decision: Optional[str] = None
        date_elem = bib_data.find('.//ep-date-of-decision/date')
        if date_elem is not None:
            date_decision = str(date_elem.text)

        # Board
        board: Optional[str] = None
        board_elem = bib_data.find('ep-board-of-appeal-code')
        if board_elem is not None:
            board = str(board_elem.text)

        # Keywords
        keywords: List[str] = []
        kw_elem = elem.find('ep-keywords')
        if kw_elem is not None:
            keywords = [str(k.text) for k in kw_elem.findall('keyword') if k.text]

        # Headnotes
        headnotes: List[str] = []
        hn_elem = elem.find('ep-headnote')
        if hn_elem is not None:
            headnotes = ["".join(p.itertext()) for p in hn_elem.findall('p')]

        # Application number
        app_num: Optional[str] = None
        app_ref = bib_data.find('application-reference/document-id/doc-number')
        if app_ref is not None:
            app_num = str(app_ref.text)

        # Publication number
        pub_num: Optional[str] = None
        pub_ref = bib_data.find('publication-reference/document-id/doc-number')
        if pub_ref is not None:
            pub_num = str(pub_ref.text)

        # Title
        title: Optional[str] = None
        title_elem = bib_data.find('invention-title')
        if title_elem is not None:
            title = "".join(title_elem.itertext())

        # IPC classes
        ipc_classes: List[str] = []
        for cls in bib_data.findall('.//classifications-ipcr/classification-ipcr'):
            parts = [cls.findtext(t) or "" for t in ('section', 'class', 'subclass', 'main-group', 'subgroup')]
            ipc_str = f"{parts[0]}{parts[1]}{parts[2]}{parts[3]}/{parts[4]}".strip("/")
            if ipc_str:
                ipc_classes.append(ipc_str)

        # Applicants
        applicants: List[str] = [
            "".join(n.itertext()).strip()
            for n in bib_data.findall('.//ep-applicant-addresses/ep-applicant-address/addressbook/name')
        ]

        # Opponents
        opponents: List[str] = [
            "".join(n.itertext()).strip()
            for n in bib_data.findall('.//ep-opponent-addresses/ep-opponent-address/addressbook/name')
        ]

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
            language=lang,
            applicants=applicants,
            opponents=opponents,
        )

        # Full text
        summary_elem = elem.find('ep-summary-of-facts')
        facts_text = ""
        if summary_elem is not None:
            facts_text = "\n\n".join(["".join(p.itertext()) for p in summary_elem.findall('p')])

        reasons_elem = elem.find('ep-reasons-for-decision')
        reasons_text = ""
        if reasons_elem is not None:
            reasons_text = "\n\n".join(["".join(p.itertext()) for p in reasons_elem.findall('p')])

        full_text = f"SUMMARY OF FACTS\n\n{facts_text}\n\nREASONS FOR THE DECISION\n\n{reasons_text}"

        return Decision(metadata=metadata, full_text=full_text, facts=facts_text, reasons=reasons_text)
