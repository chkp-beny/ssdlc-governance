#!/usr/bin/env python3
"""
Test script for AQL optimization feature
Tests the new query_aql_specific_artifacts method
"""

import os
import sys
import json
import tempfile
import logging
from unittest.mock import MagicMock, patch

# Add the project root to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_aql_specific_artifacts():
    """Test the new query_aql_specific_artifacts method"""
    
    # Mock the JfrogClient
    from src.services.data_loader import JfrogClient
    
    # Create a mock client
    with patch('src.services.data_loader.requests.post') as mock_post:
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {
                    'repo': 'cyberint-docker-local',
                    'path': 'staging/frontend-socket-service/4196b1fe9ce9a517d7dc310f204e439c1d13e78e',
                    'name': 'manifest.json',
                    'properties': [
                        {'key': 'build.name', 'value': 'frontend-socket-service'},
                        {'key': 'build.number', 'value': '123'}
                    ]
                },
                {
                    'repo': 'cyberint-docker-local',
                    'path': 'staging/github-commit-monitor/b3fe09940b745944ce8d1aabada170513f8bc17f',
                    'name': 'manifest.json',
                    'properties': [
                        {'key': 'build.name', 'value': 'github-commit-monitor'},
                        {'key': 'build.number', 'value': '456'}
                    ]
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # Create client instance
        client = JfrogClient('fake_token')
        
        # Test the specific artifacts query
        artifact_paths = [
            ('staging/frontend-socket-service/4196b1fe9ce9a517d7dc310f204e439c1d13e78e', 'manifest.json'),
            ('staging/github-commit-monitor/b3fe09940b745944ce8d1aabada170513f8bc17f', 'manifest.json')
        ]
        
        result = client.query_aql_specific_artifacts('cyberint-docker-local', artifact_paths)
        
        # Verify the call was made with the correct AQL query
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check that the AQL query contains the $or operator
        aql_query = call_args[1]['data']  # data parameter
        print(f"Generated AQL query: {aql_query}")
        
        # Verify the query structure
        assert 'cyberint-docker-local' in aql_query
        assert '$or' in aql_query
        assert 'staging/frontend-socket-service/4196b1fe9ce9a517d7dc310f204e439c1d13e78e' in aql_query
        assert 'staging/github-commit-monitor/b3fe09940b745944ce8d1aabada170513f8bc17f' in aql_query
        assert 'manifest.json' in aql_query
        
        # IMPORTANT: Verify the result contains the expected data
        assert result is not None, "Result should not be None"
        assert isinstance(result, dict), "Result should be a dictionary"
        assert 'results' in result, "Result should contain 'results' key"
        
        results = result['results']
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        
        # Verify each result has the expected structure
        for i, artifact_result in enumerate(results):
            assert 'repo' in artifact_result, f"Result {i} missing 'repo' field"
            assert 'path' in artifact_result, f"Result {i} missing 'path' field"
            assert 'name' in artifact_result, f"Result {i} missing 'name' field"
            assert 'properties' in artifact_result, f"Result {i} missing 'properties' field"
            
            # Verify specific values
            assert artifact_result['repo'] == 'cyberint-docker-local'
            assert artifact_result['name'] == 'manifest.json'
            assert isinstance(artifact_result['properties'], list)
            
            # Verify build.name property exists
            build_name_found = False
            for prop in artifact_result['properties']:
                if prop.get('key') == 'build.name':
                    build_name_found = True
                    assert prop.get('value') in ['frontend-socket-service', 'github-commit-monitor']
                    break
            assert build_name_found, f"build.name property not found in result {i}"
        
        # Verify that the paths match what we requested
        result_paths = [r['path'] for r in results]
        expected_paths = [
            'staging/frontend-socket-service/4196b1fe9ce9a517d7dc310f204e439c1d13e78e',
            'staging/github-commit-monitor/b3fe09940b745944ce8d1aabada170513f8bc17f'
        ]
        
        for expected_path in expected_paths:
            assert expected_path in result_paths, f"Expected path {expected_path} not found in results"
        
        print("✅ AQL specific artifacts query test passed!")
        
def test_cache_merging():
    """Test the cache merging functionality"""
    
    # Create temporary cache file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        existing_cache = {
            'results': [
                {
                    'repo': 'cyberint-docker-local',
                    'path': 'staging/existing-service/hash1',
                    'name': 'manifest.json',
                    'properties': [
                        {'key': 'build.name', 'value': 'existing-service'}
                    ]
                }
            ]
        }
        json.dump(existing_cache, temp_file, indent=2)
        temp_file_path = temp_file.name
    
    try:
        # Simulate new AQL results
        new_results = {
            'results': [
                {
                    'repo': 'cyberint-docker-local',
                    'path': 'staging/new-service/hash2',
                    'name': 'manifest.json',
                    'properties': [
                        {'key': 'build.name', 'value': 'new-service'}
                    ]
                }
            ]
        }
        
        # Load existing cache
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            existing_cache = json.load(f)
        
        # Merge new results
        existing_results = existing_cache.get('results', [])
        new_results_list = new_results.get('results', [])
        
        # Create deduplication set
        existing_artifacts = set()
        for result in existing_results:
            key = (result.get('path', ''), result.get('name', ''))
            existing_artifacts.add(key)
        
        # Add new results
        added_count = 0
        for new_result in new_results_list:
            key = (new_result.get('path', ''), new_result.get('name', ''))
            if key not in existing_artifacts:
                existing_results.append(new_result)
                existing_artifacts.add(key)
                added_count += 1
        
        # Verify results
        assert len(existing_results) == 2, f"Expected 2 results after merge, got {len(existing_results)}"
        assert added_count == 1, f"Expected 1 new artifact added, got {added_count}"
        
        # Verify both services are present
        services = []
        for result in existing_results:
            for prop in result.get('properties', []):
                if prop.get('key') == 'build.name':
                    services.append(prop.get('value'))
        
        assert 'existing-service' in services, "existing-service not found in merged results"
        assert 'new-service' in services, "new-service not found in merged results"
        
        # Test deduplication (try to add the same artifact again)
        duplicate_results = {
            'results': [
                {
                    'repo': 'cyberint-docker-local',
                    'path': 'staging/existing-service/hash1',
                    'name': 'manifest.json',
                    'properties': [
                        {'key': 'build.name', 'value': 'existing-service'}
                    ]
                }
            ]
        }
        
        # Try to add duplicate
        duplicate_results_list = duplicate_results.get('results', [])
        initial_count = len(existing_results)
        
        for duplicate_result in duplicate_results_list:
            key = (duplicate_result.get('path', ''), duplicate_result.get('name', ''))
            if key not in existing_artifacts:
                existing_results.append(duplicate_result)
                existing_artifacts.add(key)
                added_count += 1
        
        # Should still be 2 results (no duplicates added)
        assert len(existing_results) == initial_count, "Duplicate artifact was incorrectly added"
        
        print("✅ Cache merging test passed!")
        
    finally:
        # Clean up
        os.unlink(temp_file_path)

def test_empty_artifact_paths():
    """Test behavior with empty artifact paths"""
    
    from src.services.data_loader import JfrogClient
    
    with patch('src.services.data_loader.requests.post') as mock_post:
        client = JfrogClient('fake_token')
        
        # Test with empty list
        result = client.query_aql_specific_artifacts('cyberint-docker-local', [])
        
        # Should return empty dict and not make API call
        assert result == {}, "Empty artifact paths should return empty dict"
        mock_post.assert_not_called()
        
        print("✅ Empty artifact paths test passed!")

def main():
    """Run all tests"""
    try:
        logger.info("Starting AQL optimization tests...")
        
        test_aql_specific_artifacts()
        test_cache_merging()
        test_empty_artifact_paths()
        
        logger.info("🎉 All tests passed!")
        
    except (ValueError, KeyError, OSError, AssertionError) as e:
        logger.error("❌ Test failed: %s", str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
