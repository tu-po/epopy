
import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from epopy import AsyncClient
from epopy.decisions import DecisionsParser

# Load credentials from .env
from dotenv import load_dotenv
load_dotenv()

REAL_XML_PATH = "/var/home/quinten/tupo/main/epopy/epo-decisions/EPDecisions_September2025.xml"

async def run_workflow(client: AsyncClient):
    print(f"Initializing Offline Parser with: {REAL_XML_PATH}")
    if not os.path.exists(REAL_XML_PATH):
        print(f"Error: XML file not found at {REAL_XML_PATH}")
        return

    parser = DecisionsParser(REAL_XML_PATH)
    
    target_decision = "T 3069/19"
    print(f"Searching offline for {target_decision}...")
    
    decision = parser.find_decision(target_decision)
    if not decision:
        print(f"Decision {target_decision} NOT found offline.")
        return
        
    print(f"FOUND Decision: {decision.metadata.title}")
    print(f"  App Num: {decision.metadata.application_num}")
    
    # --- NEW SIMPLIFIED API DEMO ---
    print("\n--- NEW SIMPLIFIED API DEMO ---")
    
    # We can search for the patent associated with this application
    query = f"ap={decision.metadata.application_num}"
    print(f"Searching for patent with: {query}")
    
    patents = await client.search.search_patents(query)
    
    if not patents:
        print("No patents found for this application.")
        return
        
    patent = patents[0]
    print(f"Found Patent: {patent.number}")
    
    print(f"Fetching all available documents for patent {patent.number}...")
    docs = await patent.get_documents()
    print(f"Found {len(docs)} documents.")
    
    for doc in docs:
        print(f"  Document: {doc.name}, Pages: {doc.number_of_pages}")
        # Let's download a drawing if available
        if doc.type == "drawing":
            print(f"    Downloading {doc.name}...")
            content = await doc.download()
            
            os.makedirs("outputs", exist_ok=True)
            filename = f"outputs/{patent.number.replace('.', '_')}_drawing.pdf"
            with open(filename, "wb") as f:
                f.write(content)
            print(f"    Saved to {filename} ({len(content)} bytes)")
            break

async def main():
    consumer_key = os.getenv("EPO_CONSUMER_KEY")
    consumer_secret = os.getenv("EPO_CONSUMER_SECRET")
    
    if not consumer_key or not consumer_secret:
        print("Please set EPO_CONSUMER_KEY and EPO_CONSUMER_SECRET in .env")
        return

    async with AsyncClient(consumer_key, consumer_secret) as client:
        await run_workflow(client)

if __name__ == "__main__":
    asyncio.run(main())
