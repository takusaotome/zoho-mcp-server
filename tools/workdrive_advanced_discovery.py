#!/usr/bin/env python3
"""
Advanced WorkDrive API Discovery Tool
Implements comprehensive exploration of Zoho WorkDrive APIs using discovered patterns
"""

import asyncio
import json
import os
import sys
from typing import Dict, List, Any

# Add the server directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from server.zoho.api_client import ZohoAPIClient
from server.core.config import Settings

class AdvancedWorkDriveDiscovery:
    """Advanced WorkDrive API discovery with comprehensive exploration."""
    
    def __init__(self):
        self.config = Settings()
        self.api_client = ZohoAPIClient()
        self.discovered_endpoints = {}
        self.successful_calls = {}
        self.team_folders_found = []
        self.workspaces_found = []
        
    async def discover_all_patterns(self) -> Dict[str, Any]:
        """Execute comprehensive API discovery using all known patterns."""
        
        print("🔍 Starting Advanced WorkDrive API Discovery...")
        
        results = {
            "user_relationships": await self._explore_user_relationships(),
            "organization_endpoints": await self._explore_organization_endpoints(),
            "admin_endpoints": await self._explore_admin_endpoints(),
            "api_versions": await self._explore_api_versions(),
            "unpublished_patterns": await self._explore_unpublished_patterns(),
            "jsonapi_endpoints": await self._explore_jsonapi_patterns(),
            "team_folder_patterns": await self._explore_team_folder_patterns(),
            "summary": {}
        }
        
        # Aggregate all findings
        all_team_folders = []
        for category, data in results.items():
            if isinstance(data, dict) and "team_folders" in data:
                all_team_folders.extend(data["team_folders"])
        
        results["summary"] = {
            "total_team_folders_discovered": len(all_team_folders),
            "unique_team_folders": len(set(tf.get("id") for tf in all_team_folders if tf.get("id"))),
            "successful_endpoint_categories": sum(1 for k, v in results.items() 
                                                if isinstance(v, dict) and v.get("successful_calls")),
            "discovery_methods_used": len([k for k in results.keys() if k != "summary"])
        }
        
        return results
    
    async def _explore_user_relationships(self) -> Dict[str, Any]:
        """Explore user relationship endpoints from the discovered patterns."""
        
        print("📊 Exploring User Relationship Endpoints...")
        
        user_id = "634783244"  # Known user ID
        endpoints = [
            f"/users/{user_id}/teamfolders",
            f"/users/{user_id}/workspaces", 
            f"/users/{user_id}/teams",
            f"/users/{user_id}/libraries",
            f"/users/{user_id}/organization",
            f"/users/{user_id}/privatefolders",
            f"/users/{user_id}/groups",
            f"/users/{user_id}/collaborators",
            f"/users/{user_id}/favoritedfiles",
            f"/users/{user_id}/recentfiles",
            f"/users/{user_id}/trashedfiles"
        ]
        
        results = {"successful_calls": {}, "team_folders": [], "errors": {}}
        
        for endpoint in endpoints:
            try:
                headers_to_try = [
                    {"Accept": "application/vnd.api+json"},
                    {"Accept": "application/json"},
                    {"Accept": "application/vnd.api+json", "Content-Type": "application/vnd.api+json"}
                ]
                
                for headers in headers_to_try:
                    try:
                        response = await self.api_client.get(
                            endpoint,
                            headers=headers,
                            use_workdrive=True
                        )
                        
                        if response:
                            results["successful_calls"][endpoint] = response
                            
                            # Extract team folders
                            if "teamfolders" in endpoint and "data" in response:
                                for item in response.get("data", []):
                                    if isinstance(item, dict):
                                        results["team_folders"].append({
                                            "id": item.get("id"),
                                            "name": item.get("attributes", {}).get("name", "Unknown"),
                                            "type": item.get("type"),
                                            "source": "user_relationship",
                                            "endpoint": endpoint
                                        })
                            break  # Success with this header
                            
                    except Exception as header_error:
                        continue
                        
            except Exception as e:
                results["errors"][endpoint] = str(e)
        
        print(f"✅ User relationships: {len(results['successful_calls'])} successful, {len(results['team_folders'])} team folders")
        return results
    
    async def _explore_organization_endpoints(self) -> Dict[str, Any]:
        """Explore organization-level endpoints."""
        
        print("🏢 Exploring Organization Endpoints...")
        
        org_id = "ntvsh862341c4d57b4446b047e7f1271cbeaf"
        endpoints = [
            f"/organizations/{org_id}",
            f"/organizations/{org_id}/teamfolders",
            f"/organizations/{org_id}/workspaces",
            f"/organizations/{org_id}/teams",
            f"/organizations/{org_id}/users",
            f"/organizations/{org_id}/groups",
            f"/organizations/{org_id}/libraries"
        ]
        
        results = {"successful_calls": {}, "team_folders": [], "errors": {}}
        
        for endpoint in endpoints:
            try:
                response = await self.api_client.get(
                    endpoint,
                    headers={"Accept": "application/vnd.api+json"},
                    use_workdrive=True
                )
                if response:
                    results["successful_calls"][endpoint] = response
                    
            except Exception as e:
                results["errors"][endpoint] = str(e)
        
        print(f"✅ Organization endpoints: {len(results['successful_calls'])} successful")
        return results
    
    async def _explore_admin_endpoints(self) -> Dict[str, Any]:
        """Explore admin/management endpoints."""
        
        print("👑 Exploring Admin/Management Endpoints...")
        
        endpoints = [
            "/admin/teamfolders",
            "/admin/workspaces",
            "/admin/teams",
            "/admin/users",
            "/management/teamfolders",
            "/management/workspaces",
            "/enterprise/teamfolders",
            "/enterprise/workspaces"
        ]
        
        results = {"successful_calls": {}, "team_folders": [], "errors": {}}
        
        for endpoint in endpoints:
            try:
                response = await self.api_client.get(
                    endpoint,
                    headers={"Accept": "application/vnd.api+json"},
                    use_workdrive=True
                )
                if response:
                    results["successful_calls"][endpoint] = response
                    results["admin_access"] = True
                    
            except Exception as e:
                results["errors"][endpoint] = str(e)
        
        print(f"✅ Admin endpoints: {len(results['successful_calls'])} successful")
        return results
    
    async def _explore_api_versions(self) -> Dict[str, Any]:
        """Explore different API versions."""
        
        print("🔄 Exploring API Versions...")
        
        versions = ["v1", "v2", "v3", "beta", "internal"]
        base_endpoints = ["teamfolders", "workspaces", "teams", "files"]
        
        results = {"successful_calls": {}, "team_folders": [], "errors": {}}
        
        for version in versions:
            for base_endpoint in base_endpoints:
                endpoint = f"/{version}/{base_endpoint}"
                try:
                    response = await self.api_client.get(
                        endpoint,
                        headers={"Accept": "application/vnd.api+json"},
                        use_workdrive=True
                    )
                    if response:
                        results["successful_calls"][endpoint] = response
                        
                except Exception as e:
                    results["errors"][endpoint] = str(e)
        
        print(f"✅ API versions: {len(results['successful_calls'])} successful")
        return results
    
    async def _explore_unpublished_patterns(self) -> Dict[str, Any]:
        """Explore unpublished API patterns discovered in research."""
        
        print("🔓 Exploring Unpublished API Patterns...")
        
        # Based on The Workflow Academy findings
        endpoints = [
            "/teamfolders",  # Direct team folders list
            "/workspaces",   # Direct workspaces list  
            "/teams",        # Direct teams list
            "/folders",      # Generic folders
            "/privatefolders", # Private folders
            "/publicfolders",  # Public folders
            "/sharedfolders",  # Shared folders
            "/links",         # Share links
            "/permissions",   # Permissions
            "/stats",         # Statistics
            "/search",        # Search endpoint
            "/bulk",          # Bulk operations
        ]
        
        results = {"successful_calls": {}, "team_folders": [], "errors": {}}
        
        for endpoint in endpoints:
            try:
                # Try multiple HTTP methods
                for method in ["GET", "POST"]:
                    try:
                        if method == "GET":
                            response = await self.api_client.get(
                                endpoint,
                                headers={"Accept": "application/vnd.api+json"},
                                use_workdrive=True
                            )
                        else:
                            response = await self.api_client.post(
                                endpoint,
                                headers={"Accept": "application/vnd.api+json"},
                                data={},
                                use_workdrive=True
                            )
                            
                        if response:
                            results["successful_calls"][f"{method} {endpoint}"] = response
                            break
                            
                    except Exception as method_error:
                        continue
                        
            except Exception as e:
                results["errors"][endpoint] = str(e)
        
        print(f"✅ Unpublished patterns: {len(results['successful_calls'])} successful")
        return results
    
    async def _explore_jsonapi_patterns(self) -> Dict[str, Any]:
        """Explore JSON:API compliant patterns."""
        
        print("📋 Exploring JSON:API Patterns...")
        
        # JSON:API specific patterns
        endpoints = [
            "/data/teamfolders",
            "/api/data/teamfolders", 
            "/api/v1/data/teamfolders",
            "/resources/teamfolders",
            "/collections/teamfolders",
            "/entities/teamfolders"
        ]
        
        results = {"successful_calls": {}, "team_folders": [], "errors": {}}
        
        jsonapi_headers = {
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json"
        }
        
        for endpoint in endpoints:
            try:
                response = await self.api_client.get(
                    endpoint,
                    headers=jsonapi_headers,
                    use_workdrive=True
                )
                if response:
                    results["successful_calls"][endpoint] = response
                    
            except Exception as e:
                results["errors"][endpoint] = str(e)
        
        print(f"✅ JSON:API patterns: {len(results['successful_calls'])} successful")
        return results
    
    async def _explore_team_folder_patterns(self) -> Dict[str, Any]:
        """Explore different team folder access patterns."""
        
        print("📁 Exploring Team Folder Patterns...")
        
        known_folder_id = "hui9647cb257be9684fe294205f6519388d14"
        
        # Pattern variations for team folders
        patterns = [
            f"/teamfolders/{known_folder_id}",
            f"/teamfolders/{known_folder_id}/children",
            f"/teamfolders/{known_folder_id}/members",
            f"/teamfolders/{known_folder_id}/permissions",
            f"/teamfolders/{known_folder_id}/stats",
            f"/folders/{known_folder_id}",
            f"/files/{known_folder_id}",
            f"/files/{known_folder_id}/files",
            f"/files/{known_folder_id}/folders",
            f"/collections/{known_folder_id}",
            # Alternative ID patterns (try generating similar IDs)
            "/teamfolders/hui9647cb257be9684fe294205f6519388d15",  # +1
            "/teamfolders/hui9647cb257be9684fe294205f6519388d13",  # -1
        ]
        
        results = {"successful_calls": {}, "team_folders": [], "errors": {}}
        
        for pattern in patterns:
            try:
                response = await self.api_client.get(
                    pattern,
                    headers={"Accept": "application/vnd.api+json"},
                    use_workdrive=True
                )
                if response:
                    results["successful_calls"][pattern] = response
                    
            except Exception as e:
                results["errors"][pattern] = str(e)
        
        print(f"✅ Team folder patterns: {len(results['successful_calls'])} successful")
        return results

async def main():
    """Run the advanced discovery tool."""
    discovery = AdvancedWorkDriveDiscovery()
    
    try:
        results = await discovery.discover_all_patterns()
        
        print("\n" + "="*60)
        print("🎯 ADVANCED WORKDRIVE DISCOVERY RESULTS")
        print("="*60)
        
        # Print summary
        summary = results["summary"]
        print(f"📊 Total Team Folders Discovered: {summary['total_team_folders_discovered']}")
        print(f"🔢 Unique Team Folders: {summary['unique_team_folders']}")
        print(f"✅ Successful Endpoint Categories: {summary['successful_endpoint_categories']}")
        print(f"🔍 Discovery Methods Used: {summary['discovery_methods_used']}")
        
        # Print detailed results
        for category, data in results.items():
            if category == "summary":
                continue
                
            print(f"\n📂 {category.upper()}:")
            if isinstance(data, dict):
                print(f"  ✅ Successful calls: {len(data.get('successful_calls', {}))}")
                print(f"  ❌ Errors: {len(data.get('errors', {}))}")
                print(f"  📁 Team folders found: {len(data.get('team_folders', []))}")
        
        # Save results to file
        with open("workdrive_discovery_results.json", "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Full results saved to: workdrive_discovery_results.json")
        
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main())) 