"""
Test AQL artifact fetch and parsing logic for JFrog vulnerability processing
"""

import pytest
import sys
import os
import responses
from unittest.mock import patch, MagicMock

# Add src and root to path for imports  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.data_loader import JfrogClient
from src.models.product import Product


class TestAqlArtifactFetch:
    """Test AQL artifact fetch and parsing logic"""

    @pytest.fixture
    def jfrog_client(self):
        """Create JfrogClient with test token"""
        return JfrogClient(access_token="test-token")

    @pytest.fixture
    def product(self):
        """Create Product instance for testing parsing methods"""
        return Product(name="test", scm_type="github", organization_id="1")

    def test_parse_artifact_path(self, product):
        """Test artifact path parsing used in JFrog vulnerability processing"""
        # Standard path like cyberint-docker-local/staging/alert-status-update-handler/e9f884d22bfbcff6cb2e91a68815c4b07581e24c/manifest.json
        result = product._parse_artifact_path("cyberint-docker-local/staging/alert-status-update-handler/e9f884d22bfbcff6cb2e91a68815c4b07581e24c/manifest.json")
        assert result is not None
        repo_name, path, name, full_path = result
        assert repo_name == "cyberint-docker-local"
        assert path == "staging/alert-status-update-handler/e9f884d22bfbcff6cb2e91a68815c4b07581e24c"
        assert name == "manifest.json"
        assert full_path == "cyberint-docker-local/staging/alert-status-update-handler/e9f884d22bfbcff6cb2e91a68815c4b07581e24c/manifest.json"
        
        # Another example: hec-docker-local/scheduler-dispatcher/2025-03-19_AV-86175_fedramp_2/manifest.json
        result = product._parse_artifact_path("hec-docker-local/scheduler-dispatcher/2025-03-19_AV-86175_fedramp_2/manifest.json")
        assert result is not None
        repo_name, path, name, full_path = result
        assert repo_name == "hec-docker-local"
        assert path == "scheduler-dispatcher/2025-03-19_AV-86175_fedramp_2"
        assert name == "manifest.json"
        assert full_path == "hec-docker-local/scheduler-dispatcher/2025-03-19_AV-86175_fedramp_2/manifest.json"
        
        # Root level file (just repo/file)
        result = product._parse_artifact_path("test-repo/manifest.json")
        assert result is not None
        repo_name, path, name, full_path = result
        assert repo_name == "test-repo"
        assert path == ""
        assert name == "manifest.json"
        assert full_path == "test-repo/manifest.json"
        
        # Malformed path (missing slash)
        result = product._parse_artifact_path("malformed")
        assert result is None

    def test_is_local_repo(self, product):
        """Test local repository detection"""
        # Local repositories - should return True
        assert product._is_local_repo("cyberint-docker-local") == True
        assert product._is_local_repo("hec-docker-local") == True
        assert product._is_local_repo("test-maven-local") == True
        
        # Remote repositories - should return False
        assert product._is_local_repo("hec-core-ext-pypi-remote") == False
        assert product._is_local_repo("central-maven-remote") == False
        assert product._is_local_repo("npm-remote") == False
        
        # No dash - should return False
        assert product._is_local_repo("nodash") == False
        
        # Cache repositories - should return True (they contain "local")
        assert product._is_local_repo("cache-local") == True

    @responses.activate
    def test_query_aql_full_repo(self, jfrog_client):
        """Test full repository AQL query (this is the method that exists)"""
        mock_response = {
            "results": [
                {
                    "repo": "test-repo",
                    "path": "com/example/app",
                    "name": "manifest.json",
                    "type": "file",
                    "properties": [{"key": "build.name", "value": "test-build"}]
                }
            ]
        }
        
        responses.add(
            responses.POST,
            f"{jfrog_client.base_url}/artifactory/api/search/aql",
            json=mock_response,
            status=200
        )
        
        result = jfrog_client.query_aql_artifacts("test-repo")
        
        # Verify results
        assert len(result["results"]) == 1
        assert result["results"][0]["repo"] == "test-repo"
        
        # Verify AQL query structure (single line format)
        request_body = responses.calls[0].request.body
        assert 'items.find({"repo": {"$eq": "test-repo"}, "type": "file"}).include("property")' in request_body

    @responses.activate
    def test_error_handling(self, jfrog_client):
        """Test error handling in AQL queries"""
        responses.add(
            responses.POST,
            f"{jfrog_client.base_url}/artifactory/api/search/aql",
            json={"error": "Bad syntax"},
            status=400
        )
        
        # Test error handling returns empty results
        result = jfrog_client.query_aql_artifacts("test-repo")
        assert result["results"] == []


class TestAqlRealIntegration:
    """Test AQL functionality with real JFrog calls"""
    
    @pytest.fixture
    def real_jfrog_client(self):
        """Create JfrogClient with real environment token"""
        from dotenv import load_dotenv
        load_dotenv()
        
        token = os.getenv('CYBERINT_JFROG_ACCESS_TOKEN')
        if not token:
            pytest.skip("CYBERINT_JFROG_ACCESS_TOKEN not found in environment")
        
        return JfrogClient(access_token=token)
    
    def test_real_aql_full_repo_query(self, real_jfrog_client):
        """Test real AQL query against a JFrog repository"""
        # Use cyberint-docker-local as it's known to exist
        repo_name = "cyberint-docker-local"
        
        # Print the AQL query that will be used (matches actual implementation)
        expected_query = f'items.find({{"repo": {{"$eq": "{repo_name}"}}, "type": "file"}}).include("property")'
        print(f"AQL Query being used: {expected_query}")
        
        result = real_jfrog_client.query_aql_artifacts(repo_name)
        
        # Save the full result to a file for investigation
        import json
        output_file = f"aql_response_{repo_name}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        print(f"Full AQL response saved to: {output_file}")
        
        # Verify we get a valid response structure
        assert isinstance(result, dict)
        assert "results" in result
        assert isinstance(result["results"], list)
        
        # Log the count for visibility
        print(f"Found {len(result['results'])} artifacts in {repo_name}")
        
        # Print first few artifacts for debugging
        if result["results"]:
            print("First 3 artifacts:")
            for i, artifact in enumerate(result["results"][:3]):
                print(f"  {i+1}. {artifact}")
            
            first_artifact = result["results"][0]
            assert "repo" in first_artifact
            assert "name" in first_artifact
            assert "type" in first_artifact
            assert first_artifact["repo"] == repo_name
            
            # Check if properties are included
            if "properties" in first_artifact:
                assert isinstance(first_artifact["properties"], list)
                print(f"Sample artifact properties: {first_artifact['properties'][:3]}")
        else:
            print("No artifacts returned - this might indicate an issue with the query or repository access")
    
    def test_real_aql_error_handling(self, real_jfrog_client):
        """Test AQL error handling with invalid repository"""
        # Test with non-existent repository
        result = real_jfrog_client.query_aql_artifacts("non-existent-repo")
        
        # Should return empty results for non-existent repo
        assert isinstance(result, dict)
        assert "results" in result
        assert isinstance(result["results"], list)
        # May return empty results or actual error - both are valid handling
        
        print(f"Error handling test returned {len(result['results'])} artifacts")


class TestProductVulnerabilityParsing:
    """Test Product class methods used for JFrog vulnerability processing"""
    
    @pytest.fixture
    def product(self):
        """Create Product instance for testing"""
        return Product(name="test", scm_type="github", organization_id="1")
    
    def test_find_build_name_in_aql(self, product):
        """Test finding build name in AQL response data"""
        aql_data = {
            "results": [
                {
                    "repo": "test-repo",
                    "path": "staging/alert-service",
                    "name": "manifest.json",
                    "type": "file",
                    "properties": [
                        {"key": "build.name", "value": "alert-service"},
                        {"key": "build.number", "value": "123"}
                    ]
                },
                {
                    "repo": "test-repo", 
                    "path": "staging/another-service",
                    "name": "manifest.json",
                    "type": "file",
                    "properties": [
                        {"key": "build.name", "value": "another-service"},
                        {"key": "build.number", "value": "456"}
                    ]
                }
            ]
        }
        
        # Test finding existing build name
        build_name = product._find_build_name_in_aql(aql_data, "staging/alert-service", "manifest.json")
        assert build_name == "alert-service"
        
        # Test finding different build name
        build_name = product._find_build_name_in_aql(aql_data, "staging/another-service", "manifest.json")
        assert build_name == "another-service"
        
        # Test not finding build name (wrong path)
        build_name = product._find_build_name_in_aql(aql_data, "wrong/path", "manifest.json")
        assert build_name is None
        
        # Test not finding build name (wrong file name)
        build_name = product._find_build_name_in_aql(aql_data, "staging/alert-service", "wrong.json")
        assert build_name is None
    
    def test_match_build_name_to_repo(self, product):
        """Test matching build name to repository"""
        repo_build_names_map = {
            "alert-service": {"alert-service", "alert-service-v2"},
            "scoring-manager": {"scoring-manager", "scoring-manager-beta"},
            "user-service": {"user-service"}
        }
        
        # Test exact match
        repo_name = product._match_build_name_to_repo("alert-service", repo_build_names_map)
        assert repo_name == "alert-service"
        
        # Test match in different repo
        repo_name = product._match_build_name_to_repo("scoring-manager-beta", repo_build_names_map)
        assert repo_name == "scoring-manager"
        
        # Test no match
        repo_name = product._match_build_name_to_repo("non-existent-build", repo_build_names_map)
        assert repo_name is None
