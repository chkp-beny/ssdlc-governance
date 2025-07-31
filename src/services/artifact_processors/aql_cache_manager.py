import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AqlCacheManager:
    """
    Handles AQL cache management and build info extraction.
    Extracted from Product class to follow service layer pattern.
    """
    
    @staticmethod
    def load_aql_cache(cache_file_path: str) -> Optional[dict]:
        """
        Load AQL cache from file
        
        Args:
            cache_file_path (str): Path to cache file
            
        Returns:
            Optional[dict]: AQL data or None if not found/invalid
        """
        try:
            if not os.path.exists(cache_file_path):
                return None
            
            with open(cache_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except (OSError, ValueError, KeyError) as e:
            logger.warning("Failed to load AQL cache from %s: %s", cache_file_path, str(e))
            return None
    
    @staticmethod
    def extract_artifact_build_info_from_aql(aql_data: dict, path: str, name: str) -> Optional[tuple]:
        """
        Extract build info (name, number, timestamp, sha256) for artifact in AQL data
        
        Args:
            aql_data (dict): AQL response data
            path (str): Artifact path
            name (str): Artifact name
            
        Returns:
            Optional[tuple]: (build_name, build_number, build_timestamp, sha256) or None if not found
        """
        try:
            results = aql_data.get('results', [])
            for result in results:
                if result.get('path') == path and result.get('name') == name:
                    build_name = None
                    build_number = None
                    build_timestamp = None
                    sha256 = None
                    properties = result.get('properties', [])
                    for prop in properties:
                        if prop.get('key') == 'build.name':
                            build_name_value = prop.get('value')
                            if build_name_value:
                                if '/' in build_name_value:
                                    parts = build_name_value.split('/')
                                    if len(parts) >= 2:
                                        build_name = parts[1]
                                    else:
                                        build_name = parts[0]
                                else:
                                    build_name = build_name_value
                        elif prop.get('key') == 'build.number':
                            build_number = prop.get('value')
                        elif prop.get('key') == 'build.timestamp':
                            build_timestamp = prop.get('value')
                        elif prop.get('key') == 'sha256':
                            sha256 = prop.get('value')
                    return build_name, build_number, build_timestamp, sha256
            return None
        except (ValueError, KeyError, IndexError) as e:
            logger.debug("Error extracting build info in AQL data: %s", str(e))
            return None
    
    @staticmethod
    def save_aql_cache(cache_file_path: str, aql_data: dict) -> bool:
        """
        Save AQL data to cache file
        
        Args:
            cache_file_path (str): Path to cache file
            aql_data (dict): AQL response data to cache
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(cache_file_path), exist_ok=True)
            
            with open(cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(aql_data, f, indent=2)
            return True
        except (OSError, ValueError) as e:
            logger.warning("Failed to save AQL cache to %s: %s", cache_file_path, str(e))
            return False
    
    @staticmethod
    def merge_aql_caches(existing_cache: dict, new_cache: dict) -> dict:
        """
        Merge new AQL cache data with existing cache
        
        Args:
            existing_cache (dict): Existing cache data
            new_cache (dict): New cache data to merge
            
        Returns:
            dict: Merged cache data
        """
        existing_results = existing_cache.get('results', [])
        new_results = new_cache.get('results', [])
        
        # Create a set of existing artifacts for deduplication (path + name combination)
        existing_artifacts = set()
        for result in existing_results:
            key = (result.get('path', ''), result.get('name', ''))
            existing_artifacts.add(key)
        
        # Add new results that don't already exist
        added_count = 0
        for new_result in new_results:
            key = (new_result.get('path', ''), new_result.get('name', ''))
            if key not in existing_artifacts:
                existing_results.append(new_result)
                existing_artifacts.add(key)
                added_count += 1
        
        # Return merged cache
        return {
            'results': existing_results,
            'range': {
                'start_pos': 0,
                'end_pos': len(existing_results),
                'total': len(existing_results)
            },
            'added_count': added_count
        }
