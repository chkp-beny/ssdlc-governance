import pandas as pd
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class HRDBClient:
    def __init__(self, hrdb_path: str = "data/HROPS-3719.csv"):
        try:
            self.df = pd.read_csv(hrdb_path)
            # Convert username to lowercase for consistent lookup
            self.df['Username'] = self.df['Username'].str.lower()
        except Exception as e:
            logger.error("Failed to load HRDB: %s", e)
            self.df = pd.DataFrame()

    def get_user_data(self, username: str) -> Dict[str, Optional[str]]:
        """
        Given a username (e.g., 'simam'), returns a dict with all available HR data:
        {
            'general_manager': ...,
            'vp': ...,
            'title': ...,
            'department': ...,
            'manager_name': ...,
            'director': ...,
            'vp2': ...,
            'c_level': ...,
            'worker_id': ...,
            'full_name': ...
        }
        If not found, values are empty strings.
        """
        username_lower = username.lower()
        row = self.df[self.df['Username'] == username_lower]
        if not row.empty:
            record = row.iloc[0]
            
            # Handle VP with fallback logic: VP1 -> VP2 if VP1 is missing/NaN
            vp1 = record.get('VP 1', '')
            vp2 = record.get('VP 2', '')
            
            # Check if VP1 is valid (not NaN, not empty)
            if pd.isna(vp1) or str(vp1).strip() in ['', 'nan', 'NaN']:
                # Fall back to VP2 if VP1 is missing
                if pd.isna(vp2) or str(vp2).strip() in ['', 'nan', 'NaN']:
                    vp_value = ''
                else:
                    vp_value = str(vp2).strip()
            else:
                vp_value = str(vp1).strip()
            
            # Helper function to safely convert and handle NaN values
            def safe_str(value):
                if pd.isna(value):
                    return ''
                str_val = str(value).strip()
                return '' if str_val in ['nan', 'NaN'] else str_val
            
            return {
                'general_manager': safe_str(record.get('Sr. Manager (GM/CM)', '')),
                'vp': vp_value,
                'title': safe_str(record.get('Title', '')),
                'department': safe_str(record.get('Department Desc', '')),
                'manager_name': safe_str(record.get('Manager Name', '')),
                'director': safe_str(record.get('Director', '')),
                'vp2': safe_str(record.get('VP 2', '')),
                'c_level': safe_str(record.get('C Level', '')),
                'worker_id': safe_str(record.get('Worker ID', '')),
                'full_name': safe_str(record.get('Full Name', ''))
            }
        else:
            logger.warning("HRDB: No match for username %s", username_lower)
            return {
                'general_manager': '',
                'vp': '',
                'title': '',
                'department': '',
                'manager_name': '',
                'director': '',
                'vp2': '',
                'c_level': '',
                'worker_id': '',
                'full_name': ''
            }
