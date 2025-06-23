#!/usr/bin/env python3
"""
Workspace Relationship Explorer
Explores all discovered relationship endpoints for deeper API access
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

class WorkspaceRelationshipExplorer:
    """Explore workspace relationship endpoints for deeper access."""
    
    def __init__(self):
        self.config = Settings()
        self.api_client = ZohoAPIClient()
        self.workspace_id = "hui9647cb257be9684fe294205f6519388d14"
        
    async def explore_all_relationships(self) -> Dict[str, Any]:
        """Explore all discovered relationship endpoints."""
        
        print("🔗 Starting Workspace Relationship Exploration...")
        
        # Discovered relationship endpoints from the workspace
        relationship_endpoints = [
            "folders", "files", "permissions", "links", "tasks", "comments",
            "filequery", "dlpsensitivecontentidentifiers", "records", 
            "instances", "unzip", "performtransition", "accesschartdata",
            "resourceproperty", "shortcut", "importfile", "saveastemplate",
            "copy", "previewzip", "custommetadata", "deletedversions",
            "previewinfo", "approvedversions", "publiclink", "parentfolders",
            "versions", "supportshare", "startjourney", "recordsuggestions",
            "timeline", "accessdata"
        ]
        
        results = {
            "successful_calls": {},
            "team_folders_discovered": [],
            "workspaces_discovered": [],
            "users_discovered": [],
            "high_privilege_access": [],
            "errors": {}
        }
        
        for endpoint in relationship_endpoints:
            await self._explore_endpoint(endpoint, results)
        
        # Explore discovered links for additional workspaces/team folders
        await self._explore_discovered_links(results)
        
        # Summary
        results["summary"] = {
            "successful_endpoints": len(results["successful_calls"]),
            "team_folders_found": len(results["team_folders_discovered"]),
            "workspaces_found": len(results["workspaces_discovered"]),
            "users_found": len(results["users_discovered"]),
            "high_privilege_access": len(results["high_privilege_access"])
        }
        
        return results
    
    async def _explore_endpoint(self, endpoint: str, results: Dict[str, Any]) -> None:
        """Explore a single relationship endpoint."""
        
        full_endpoint = f"/files/{self.workspace_id}/{endpoint}"
        
        try:
            print(f"🔍 Exploring: {full_endpoint}")
            
            headers_to_try = [
                {"Accept": "application/vnd.api+json"},
                {"Accept": "application/json"},
                {"Accept": "application/vnd.api+json", "Content-Type": "application/vnd.api+json"}
            ]
            
            for headers in headers_to_try:
                try:
                    response = await self.api_client.get(
                        full_endpoint,
                        headers=headers,
                        use_workdrive=True
                    )
                    
                    if response:
                        results["successful_calls"][full_endpoint] = response
                        
                        # Analyze response for team folders, workspaces, users
                        await self._analyze_response(endpoint, response, results)
                        
                        print(f"✅ Success: {full_endpoint}")
                        break
                        
                except Exception as header_error:
                    continue
                    
        except Exception as e:
            results["errors"][full_endpoint] = str(e)
            print(f"❌ Failed: {full_endpoint} - {e}")
    
    async def _analyze_response(self, endpoint: str, response: Dict[str, Any], results: Dict[str, Any]) -> None:
        """Analyze response data for interesting discoveries."""
        
        if not isinstance(response, dict):
            return
            
        # Look for data array
        data = response.get("data", [])
        if not isinstance(data, list):
            data = [data] if data else []
        
        for item in data:
            if not isinstance(item, dict):
                continue
                
            item_type = item.get("type", "")
            item_id = item.get("id", "")
            attributes = item.get("attributes", {})
            
            # Discover team folders
            if item_type in ["teamfolders", "workspace", "files"] and "workspace" in attributes.get("type", ""):
                results["team_folders_discovered"].append({
                    "id": item_id,
                    "name": attributes.get("name", attributes.get("display_attr_name", "Unknown")),
                    "type": item_type,
                    "source_endpoint": endpoint,
                    "size": attributes.get("storage_info", {}).get("size", "Unknown"),
                    "files_count": attributes.get("storage_info", {}).get("files_count", 0),
                    "folders_count": attributes.get("storage_info", {}).get("folders_count", 0)
                })
            
            # Discover users with admin privileges
            if item_type == "users" and attributes.get("role_id", 0) <= 2:  # Admin/Organizer roles
                results["high_privilege_access"].append({
                    "user_id": item_id,
                    "name": attributes.get("display_name", "Unknown"),
                    "role_id": attributes.get("role_id"),
                    "email": attributes.get("email_id", ""),
                    "source_endpoint": endpoint
                })
            
            # Discover other workspaces in links/references
            if "workspace" in str(attributes).lower() or "teamfolder" in str(attributes).lower():
                # Look for workspace/team folder IDs in various fields
                for key, value in attributes.items():
                    if isinstance(value, str) and len(value) > 30 and value.startswith(("hui", "wor", "tea")):
                        if value != self.workspace_id:  # Different from current workspace
                            results["workspaces_discovered"].append({
                                "id": value,
                                "discovered_in": f"{endpoint}.{key}",
                                "context": str(value)[:100]
                            })
    
    async def _explore_discovered_links(self, results: Dict[str, Any]) -> None:
        """Explore any discovered workspace/team folder IDs."""
        
        print("🔗 Exploring discovered workspace links...")
        
        for workspace_info in results["workspaces_discovered"]:
            workspace_id = workspace_info["id"]
            
            try:
                # Try to access this workspace directly
                response = await self.api_client.get(
                    f"/files/{workspace_id}",
                    headers={"Accept": "application/vnd.api+json"},
                    use_workdrive=True
                )
                
                if response:
                    print(f"✅ Discovered accessible workspace: {workspace_id}")
                    results["successful_calls"][f"discovered_workspace_{workspace_id}"] = response
                    
                    # Try to get files from this workspace
                    files_response = await self.api_client.get(
                        f"/files/{workspace_id}/files",
                        headers={"Accept": "application/vnd.api+json"},
                        use_workdrive=True
                    )
                    
                    if files_response:
                        results["successful_calls"][f"discovered_workspace_{workspace_id}_files"] = files_response
                        print(f"✅ Got files from workspace: {workspace_id}")
                        
            except Exception as e:
                results["errors"][f"discovered_workspace_{workspace_id}"] = str(e)

async def main():
    """Run the workspace relationship explorer."""
    explorer = WorkspaceRelationshipExplorer()
    
    try:
        results = await explorer.explore_all_relationships()
        
        print("\n" + "="*60)
        print("🔗 WORKSPACE RELATIONSHIP EXPLORATION RESULTS")
        print("="*60)
        
        summary = results["summary"]
        print(f"✅ Successful Endpoints: {summary['successful_endpoints']}")
        print(f"📁 Team Folders Discovered: {summary['team_folders_found']}")
        print(f"🏢 Workspaces Discovered: {summary['workspaces_found']}")
        print(f"👥 Users Discovered: {summary['users_found']}")
        print(f"🔑 High Privilege Access: {summary['high_privilege_access']}")
        
        # Print discovered team folders
        if results["team_folders_discovered"]:
            print(f"\n📁 DISCOVERED TEAM FOLDERS:")
            for tf in results["team_folders_discovered"]:
                print(f"  • {tf['name']} (ID: {tf['id']}) - {tf['size']}, {tf['files_count']} files")
        
        # Print discovered workspaces
        if results["workspaces_discovered"]:
            print(f"\n🏢 DISCOVERED WORKSPACES:")
            for ws in results["workspaces_discovered"]:
                print(f"  • ID: {ws['id']} - Found in: {ws['discovered_in']}")
        
        # Print high privilege users
        if results["high_privilege_access"]:
            print(f"\n🔑 HIGH PRIVILEGE USERS:")
            for user in results["high_privilege_access"]:
                print(f"  • {user['name']} ({user['email']}) - Role: {user['role_id']}")
        
        # Save results
        with open("workspace_relationships_results.json", "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Full results saved to: workspace_relationships_results.json")
        
    except Exception as e:
        print(f"❌ Exploration failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main())) 