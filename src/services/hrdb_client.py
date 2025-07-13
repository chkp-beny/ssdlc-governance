import pandas as pd
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class HRDBClient:
    def __init__(self, hrdb_path: str = "HRDB.csv"):
        try:
            self.df = pd.read_csv(hrdb_path)
            self.df['EMAIL'] = self.df['EMAIL'].str.lower()
            logger.info(f"Loaded HRDB from {hrdb_path} with {len(self.df)} records.")
        except Exception as e:
            logger.error(f"Failed to load HRDB: {e}")
            self.df = pd.DataFrame()

    def get_manager_vp(self, username: str) -> Dict[str, Optional[str]]:
        """
        Given a username (e.g., 'simam'), returns a dict with:
        {
            'general_manager': ...,
            'vp': ...
        }
        If not found, values are empty strings.
        """
        email = f"{username.lower()}@checkpoint.com"
        row = self.df[self.df['EMAIL'] == email]
        if not row.empty:
            return {
                'general_manager': row.iloc[0].get('Senior Manager', ''),
                'vp': row.iloc[0].get('VP', '')
            }
        else:
            logger.warning(f"HRDB: No match for email {email}")
            return {
                'general_manager': '',
                'vp': ''
            }
