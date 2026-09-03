from pathlib import Path
import sys

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.voteringar import VOTING_LIST_URL

URL = VOTING_LIST_URL #hämtar databasen från src.ingest.voteringar filen