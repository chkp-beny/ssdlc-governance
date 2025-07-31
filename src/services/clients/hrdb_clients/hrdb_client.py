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

    def _get_vp_with_fallback(self, record) -> str:
        """VP Logic: VP 2 -> VP 1 -> C Level -> ''"""
        def is_empty(value):
            if pd.isna(value):
                return True
            str_val = str(value).strip()
            return str_val == '' or str_val in ['nan', 'NaN']
        
        vp2 = record.get('VP 2', '')
        if not is_empty(vp2):
            return str(vp2).strip()
        
        vp1 = record.get('VP 1', '')
        if not is_empty(vp1):
            return str(vp1).strip()
        
        c_level = record.get('C Level', '')
        if not is_empty(c_level):
            return str(c_level).strip()
        
        return ''

    def _get_director_with_fallback(self, record) -> str:
        """Director Logic: Director -> Sr. Manager (GM/CM) -> ''"""
        def is_empty(value):
            if pd.isna(value):
                return True
            str_val = str(value).strip()
            return str_val == '' or str_val in ['nan', 'NaN']
        
        director = record.get('Director', '')
        if not is_empty(director):
            return str(director).strip()
        
        sr_manager = record.get('Sr. Manager (GM/CM)', '')
        if not is_empty(sr_manager):
            return str(sr_manager).strip()
        
        return ''

    def _get_group_manager_with_fallback(self, record) -> str:
        """Group Manager Logic: Sr. Manager (GM/CM) -> Manager 2 -> Manager Name -> ''"""
        def is_empty(value):
            if pd.isna(value):
                return True
            str_val = str(value).strip()
            return str_val == '' or str_val in ['nan', 'NaN']
        
        sr_manager = record.get('Sr. Manager (GM/CM)', '')
        if not is_empty(sr_manager):
            return str(sr_manager).strip()
        
        manager2 = record.get('Manager 2', '')
        if not is_empty(manager2):
            return str(manager2).strip()
        
        manager_name = record.get('Manager Name', '')
        if not is_empty(manager_name):
            return str(manager_name).strip()
        
        return ''

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
            
            # Helper function to safely convert and handle NaN values
            def safe_str(value):
                if pd.isna(value):
                    return ''
                str_val = str(value).strip()
                return '' if str_val in ['nan', 'NaN'] else str_val
            
            # Use fallback functions for hierarchy fields
            return {
                'general_manager': self._get_group_manager_with_fallback(record),
                'vp': self._get_vp_with_fallback(record),
                'title': safe_str(record.get('Title', '')),
                'department': safe_str(record.get('Department Desc', '')),
                'manager_name': safe_str(record.get('Manager Name', '')),
                'director': self._get_director_with_fallback(record),
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
