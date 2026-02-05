
import asyncio
import os
import sys
import json
import time
from typing import Dict, Any, List, Union

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from epopy import AsyncClient
from epopy.decisions import DecisionsParser

# Use the credentials if provided in env or hardcoded (for now I'll use the ones provided by user earlier)
CONSUMER_KEY = "GwHfSU69o9zS2JA4VgPvAnoe1QN7tCrcxQA6ArQUoFYCEzXr" 
CONSUMER_SECRET = "qmcqxn56UaMqTljudJcrlOZs214SNK9hslCsTWmqoQp1nrPXcnI6ZoFRsRRxTA5r"
REAL_XML_PATH = "/var/home/quinten/tupo/epopy/epo-decisions/EPDecisions_September2025.xml"

async def main():
    print(f"Initializing Offline Parser with: {REAL_XML_PATH}")
    if not os.path.exists(REAL_XML_PATH):
        print(f"Error: XML file not found at {REAL_XML_PATH}")
        return

    parser = DecisionsParser(REAL_XML_PATH)
    
    target_decision = "T 3069/19"
    print(f"Searching offline for {target_decision}...")
    start_time = time.time()
    
    decision = parser.find_decision(target_decision)
    duration = time.time() - start_time
    print(f"Search took {duration:.2f} seconds")
    
    if not decision:
        print(f"Decision {target_decision} NOT found offline.")
        return
        
    print(f"FOUND Decision!")
    print(f"  ID: {decision.metadata.decision_id}")
    print(f"  Title: {decision.metadata.title}")
    print(f"  App Num: {decision.metadata.application_num}")
    print(f"  Keywords: {decision.metadata.keywords}")
    print("-" * 30)
    print("Full Text Preview (Facts first 200 chars):")
    print(decision.facts[:200])
    print("-" * 30)
    
    # Now use the found application number to query OPS API
    app_num = decision.metadata.application_num
    if not app_num:
        print("No Application Number found in decision metadata, cannot query OPS API.")
        return
        
    # Format app number for OPS: e.g. "14197959" -> Need to check valid format. 
    # Usually OPS expects EP prefix or docdb format.
    # The offline parser extracted "14197959". 
    # Let's try prepending EP if it's purely numeric.
    
    app_num_query = app_num
    # If it looks like a raw number, we might want to query it via CQL or directly.
    # OPS API for search: "q=ap=EP..."
    
    if app_num.isdigit():
        app_num_query = f"EP{app_num}"
        
    print(f"\nQuerying OPS API for Application: {app_num_query} ({app_num})")

    async with AsyncClient(CONSUMER_KEY, CONSUMER_SECRET) as client:
        print("Authenticating...")
        try:
            await client.auth.get_access_token()
            print(f"Authenticated.")
        except Exception as e:
            print(f"Auth failed: {e}")
            return

        # 1. Search for application to get publication details (biblio)
        print(f"Getting data for application {app_num_query}...")
        
        # We can search by application number to get biblio
        try:
            # Using 'search' service
            q = f"ap={app_num_query}"
            res = await client.get_data("/published-data/search", params={"q": q})
            print("Search result received.")
            
            # Simple print of result structure
            biblio: Dict[str, Any] = res.get("ops:world-patent-data", {}).get("ops:biblio-search", {}).get("ops:search-result", {})
            pub_ref: Union[Dict[str, Any], List[Dict[str, Any]]] = biblio.get("ops:publication-reference", {})
            
            # Extract Publication Number to look up Documents/Images
            found_pub_num = None
            found_pub_type = "epodoc"
            
            if isinstance(pub_ref, list):
                pub_ref = pub_ref[0]
            
            # Now pub_ref is definitely a dict
            pub_ref_dict = pub_ref
            doc_ids: Union[Dict[str, Any], List[Dict[str, Any]]] = pub_ref_dict.get("document-id", [])
            if isinstance(doc_ids, dict):
                doc_ids = [doc_ids]
                
            for d in doc_ids:
                dtype = d.get("@document-id-type")
                if dtype == "epodoc":
                    val = d.get("doc-number")
                    found_pub_num = val.get("#text") if isinstance(val, dict) else val
                    found_pub_type = "epodoc"
                    break
                elif dtype == "docdb":
                    # Construct docdb format: CC.Number.Kind
                    cc = d.get("country", {}).get("$") if isinstance(d.get("country"), dict) else d.get("country")
                    num = d.get("doc-number", {}).get("$") if isinstance(d.get("doc-number"), dict) else d.get("doc-number")
                    kind = d.get("kind", {}).get("$") if isinstance(d.get("kind"), dict) else d.get("kind")
                    
                    if cc and num and kind:
                        found_pub_num = f"{cc}.{num}.{kind}"
                        found_pub_type = "docdb"

            print(f"  Found Publication Number: {found_pub_num} (Type: {found_pub_type})")
            
            if found_pub_num:
                 # Get Images/Documents
                 print(f"Getting images for {found_pub_num}...")
                 res_images = await client.get_data(f"/published-data/publication/{found_pub_type}/{found_pub_num}/images")
                 print("  Images info retrieved!")
                 # print(json.dumps(res_images, indent=2)[:1000]) # First 1000 chars
                 
                 # Try to find a download link
                 doc_instances = res_images.get("ops:world-patent-data", {}).get("ops:document-inquiry", {}).get("ops:inquiry-result", {}).get("ops:document-instance", [])
                 if isinstance(doc_instances, dict):
                     doc_instances = [doc_instances]
                     
                 for instance in doc_instances:
                     desc = instance.get("@desc")
                     link = instance.get("@link")
                     print(f"  Found instance: {desc}, Link: {link}")
                     
                     # Try to download the first one (e.g. Drawing or FullDocument)
                     # Determine format
                     formats = instance.get("ops:document-format-options", {}).get("ops:document-format", [])
                     if isinstance(formats, str): formats = [formats]
                     
                     print(f"    Formats: {formats}")
                     
                     if link:
                         print(f"    Attempting download from {link}...")
                         # OPS image download usually requires specific Accept header or just standard GET
                         # If it is 'application/pdf', we expect bytes.
                         
                         try:
                            # Use basic get which returns httpx.Response
                            # Ensure we don't treat it as XML
                            # Note: The link might be relative to rest-services
                            # Must set Accept header to match available formats (e.g. application/pdf)
                            # Also often requires Range param for images
                            dl_res = await client.get(link, headers={"Accept": "application/pdf"}, params={"Range": "1"})
                            print(f"    Download Status: {dl_res.status_code}")
                            print(f"    Content Type: {dl_res.headers.get('content-type')}")
                            print(f"    Content Length: {len(dl_res.content)} bytes")
                            
                            if dl_res.status_code == 200:
                                print("    SUCCESS! Downloaded bytes.")
                                break # Stop after one success
                         except Exception as e:
                            print(f"    Download failed: {e}")

        except Exception as e:
            print(f"OPS API Query failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
