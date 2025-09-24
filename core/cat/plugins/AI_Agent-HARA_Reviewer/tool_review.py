from typing import Dict, Any
from cat.mad_hatter.decorators import hook, tool
from .helpers import run_checklist, run_hara
from cat.convo.messages import CatMessage
from pathlib import Path


print("### helpers.py 30‑07‑2025 LOADED from", __file__)

# Base directory for this plugin
BASE_DIR = Path(__file__).parent

ITEM_ID_PATH = BASE_DIR / 'item_definitions' / 'item_definition.txt'

@tool(return_direct=True)
def run_full_review(tool_input: str, cat) -> Dict[str, Any]:

    """
    Existing review: loads item-definition, runs checklist, then HARA.
    Returns combined report dict.

    Args:
        tool_input: Input from the user (not used in this tool)
        cat: Cheshire Cat instance

        Returns:
            Dict containing:
                - checklist: results from the item-definition checklist
                - hara: results from the HARA analysis
    """

    # 1. Load and run checklist review
    review_result = run_checklist(ITEM_ID_PATH)  # your existing function

    # 2. Run HARA on the reviewed structure
    hara_results = run_hara(review_result)

    print("✅ TOOL CALLED: run_full_review")

    # 3. Combine
    return {
        'checklist': review_result,
        'hara': hara_results
    }
