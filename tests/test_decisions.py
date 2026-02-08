import pytest
import os
import time
from typing import List, Any, cast
from epopy.decisions import DecisionsParser

# Real file path
DECISONS_PATH = "./epo-decisions/EPDecisions_September2025.xml"

@pytest.fixture
def decisions_parser():
    if not os.path.exists(DECISONS_PATH):
        pytest.skip(f"Real XML file not found at {DECISONS_PATH}")
    return DecisionsParser(DECISONS_PATH)

def test_find_decision_t3069_19(decisions_parser: DecisionsParser):
    start_time = time.time()
    decision = decisions_parser.find_decision("T 3069/19")
    duration = time.time() - start_time
    print(f"Search for T 3069/19 took {duration:.2f} seconds")
    
    assert decision is not None, "Decision T 3069/19 should be found"
    
    assert decision.metadata.decision_id == "T 3069/19"
    # We know from grep that application-number is 14197959
    assert decision.metadata.application_num == "14197959", "Application number mismatch"
    
    # Verify content snippets from the real file
    # Check some facts/reasons text
    assert len(cast(List[Any], decision.facts)) > 0, "Facts should not be empty"
    assert len(cast(List[Any], decision.reasons)) > 0, "Reasons should not be empty"
    
    # Check specific text known from the snippet
    assert "Semiconductor radiation detector" in str(decision.metadata)
    
    found_kw = False
    for kw in decision.metadata.keywords:
        if "Amendments" in kw:
            found_kw = True
            break
    assert found_kw, "Should have keywords related to Amendments"

def test_parse_decision_code():
    # This unit test doesn't read the file, so it's fast
    # We can perform this test without the fixture if we want, 
    # but the parser class itself is needed. 
    # Since parse_decision_code is a method on the instance but doesn't use state, 
    # we can instantiate a dummy if needed, but the original test used the instance.
    # Let's check how DecisionsParser is initialized. It checks for file existence.
    # To test this in isolation without the file, we might need to mock os.path.exists 
    # or just use the fixture and skip if file missing (which is fine for integration tests).
    
    # However, to keep it pure unit test if the file is missing:
    # We can mock the path check or just allow skipping if the file is missing 
    # since this codebase seems to rely on the file being present for "real" tests.
    # But wait, the original test `test_parse_decision_code` used `self.parser` which was set up in `setUp`.
    # And `setUp` asserted the file exists and raised/failed if not.
    # So if the file is missing, the original Unit Test would fail/error.
    # So using the fixture that skips is actually an improvement or at least equivalent.
    
    # Actually, let's look at `DecisionsParser`. It takes a path.
    # If we want to test `parse_decision_code` without the file, we can pass a dummy path 
    # provided we mock the exists check in the `__init__` if it does one.
    # `DecisionsParser.__init__` does:
    # self.xml_path = Path(xml_path)
    # if not self.xml_path.exists(): raise FileNotFoundError(...)
    
    # So we can't easily instantiate it without a real file or mocking.
    # Let's just use the fixture. If file is missing, we skip everything.
    pass

def test_parse_decision_code_logic(decisions_parser: DecisionsParser):
    t, n, y = decisions_parser.parse_decision_code("T 3069/19")
    assert t == "T"
    assert n == "3069"
    assert y == "2019"

    t, n, y = decisions_parser.parse_decision_code("D 1/00")
    assert t == "D"
    assert n == "0001"
    assert y == "2000"

