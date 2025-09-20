#!/usr/bin/env python3
"""
Unified Debug Solver - Consolidated orchestration logic for complete debugging workflow
Combines functionality from Debug Orchestrator and BugLocator agents into a single solver
"""

import os
import sys
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Add tools to path
tools_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools')
sys.path.append(tools_path)

load_dotenv()


class UnifiedDebugSolver:
    """
    Unified debug solver that handles the complete debugging workflow using direct tool calls.
    Eliminates the need for agent-to-agent communication by using tools directly.
    """
    
    def __init__(self):
        self.conversation_history = []
        self.workflow_state = {}
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"🔧 UnifiedDebugSolver initialized with session: {self.session_id}")
    
    async def debug_repository_issue(self, bug_description: str, repository_name: str = None, 
                                   auto_edit_mode: bool = False) -> str:
        """
        Complete debugging workflow using direct tool calls instead of agent communication.
        
        Args:
            bug_description: The bug description to debug
            repository_name: Optional repository name to target specific codebase
            auto_edit_mode: If True, automatically apply fixes without human approval
            
        Returns:
            JSON string with comprehensive workflow results
        """
        workflow_id = f"unified_debug_{self.session_id}_{len(self.conversation_history)}"
        print(f"🎯 Starting unified debugging workflow: {workflow_id}")
        
        # Initialize workflow state
        workflow_state = {
            "workflow_id": workflow_id,
            "bug_description": bug_description,
            "repository_name": repository_name,
            "auto_edit_mode": auto_edit_mode,
            "start_time": datetime.now().isoformat(),
            "steps": [],
            "status": "in_progress",
            "tools_used": []
        }
        
        try:
            # Step 1: Analyze and separate bugs if needed
            bugs = await self._analyze_and_separate_bugs(bug_description, workflow_state)
            workflow_state["total_bugs"] = len(bugs)
            
            # Step 2: Process each bug sequentially using direct tool calls
            results = []
            for i, bug in enumerate(bugs, 1):
                print(f"🐛 Processing bug {i}/{len(bugs)}: {bug[:100]}...")
                
                bug_result = await self._process_bug_with_tools(
                    bug, 
                    repository_name,
                    auto_edit_mode, 
                    workflow_state,
                    bug_index=i
                )
                results.append(bug_result)
                workflow_state["bugs_processed"] = i
            
            # Step 3: Finalize workflow
            workflow_state["status"] = "completed"
            workflow_state["end_time"] = datetime.now().isoformat()
            workflow_state["results"] = results
            
            # Add to conversation history
            self.conversation_history.append(workflow_state)
            
            return json.dumps(workflow_state, indent=2)
            
        except Exception as e:
            print(f"❌ Unified workflow failed: {str(e)}")
            workflow_state["status"] = "failed"
            workflow_state["error"] = str(e)
            workflow_state["end_time"] = datetime.now().isoformat()
            
            return json.dumps(workflow_state, indent=2)
    
    async def _analyze_and_separate_bugs(self, bug_description: str, workflow_state: Dict[str, Any]) -> List[str]:
        """Analyze the bug description and separate multiple bugs if needed."""
        step = {
            "step_name": "bug_analysis",
            "start_time": datetime.now().isoformat(),
            "status": "in_progress"
        }
        workflow_state["steps"].append(step)
        
        try:
            # Simple heuristic to detect multiple bugs
            separators = [
                " and ", " also ", " additionally ", " furthermore ",
                "1.", "2.", "3.", "4.", "5.",
                "- ", "* ", "• "
            ]
            
            bugs = []
            current_bug = bug_description.strip()
            
            # Check if description contains multiple bugs
            has_multiple = any(sep in current_bug.lower() for sep in separators[:4])
            has_numbered = any(sep in current_bug for sep in separators[4:8])
            has_bullets = any(sep in current_bug for sep in separators[8:])
            
            if has_numbered or has_bullets:
                # Split by numbered lists or bullets
                import re
                parts = re.split(r'\n?\s*(?:\d+\.|\s*[-*•]\s*)', current_bug)
                bugs = [part.strip() for part in parts if part.strip()]
            elif has_multiple:
                # Split by conjunctions
                for sep in separators[:4]:
                    if sep in current_bug.lower():
                        parts = current_bug.lower().split(sep)
                        bugs = [part.strip() for part in parts if part.strip()]
                        break
            else:
                bugs = [current_bug]
            
            # Filter out very short or empty descriptions
            bugs = [bug for bug in bugs if len(bug.strip()) > 10]
            
            if len(bugs) > 1:
                print(f"🔍 Detected {len(bugs)} separate bugs")
            
            step["status"] = "completed"
            step["end_time"] = datetime.now().isoformat()
            step["bugs_detected"] = len(bugs)
            
            return bugs
            
        except Exception as e:
            step["status"] = "failed"
            step["error"] = str(e)
            step["end_time"] = datetime.now().isoformat()
            raise
    
    async def _process_bug_with_tools(self, bug_description: str, repository_name: str, 
                                    auto_edit_mode: bool, workflow_state: Dict[str, Any], 
                                    bug_index: int) -> Dict[str, Any]:
        """Process a single bug using direct tool calls instead of agent communication."""
        bug_result = {
            "bug_index": bug_index,
            "bug_description": bug_description,
            "repository_name": repository_name,
            "steps": [],
            "status": "in_progress"
        }
        
        try:
            # Step 1: Bug Localization using BugLocator tool directly
            localization_result = await self._call_bug_locator_tool(bug_description, repository_name, bug_result)
            workflow_state["tools_used"].append("bug_locator_tool")
            
            # Step 2: Code Fix Generation (if relevant code found)
            total_found = localization_result.get("search_stats", {}).get("total_found", 0)
            if total_found > 0:
                fix_result = await self._call_codestral_tool(localization_result, bug_result)
                workflow_state["tools_used"].append("codestral_tool")
                
                # Step 3: Human Review (if not auto-edit mode)
                if not auto_edit_mode:
                    review_result = await self._call_human_review_tool(fix_result, bug_result)
                    workflow_state["tools_used"].append("human_review_tool")
                    if not review_result.get("approved", False):
                        bug_result["status"] = "rejected_by_human"
                        return bug_result
                
                # Step 4: Apply Patch
                patch_result = await self._call_git_patch_tool(fix_result, bug_result)
                workflow_state["tools_used"].append("git_patch_tool")
                
                bug_result["status"] = "completed"
            else:
                bug_result["status"] = "no_relevant_code_found"
            
            return bug_result
            
        except Exception as e:
            bug_result["status"] = "failed"
            bug_result["error"] = str(e)
            return bug_result
    
    async def _call_bug_locator_tool(self, bug_description: str, repository_name: str, bug_result: Dict[str, Any]) -> Dict[str, Any]:
        """Call the BugLocator tool directly."""
        step = {
            "step_name": "bug_localization",
            "start_time": datetime.now().isoformat(),
            "status": "in_progress"
        }
        bug_result["steps"].append(step)
        
        try:
            from bug_locator_tool import locate_bug_in_repository
            
            print("📍 Running bug localization...")
            localization_result_str = await locate_bug_in_repository(
                bug_description=bug_description,
                repository_name=repository_name,
                similarity_threshold=0.7,
                max_results=10
            )
            
            # Parse JSON string to dictionary for downstream processing
            localization_result = json.loads(localization_result_str)
            
            step["status"] = "completed"
            step["end_time"] = datetime.now().isoformat()
            step["result"] = localization_result_str  # Store original string in step result
            
            return localization_result
            
        except Exception as e:
            step["status"] = "failed"
            step["error"] = str(e)
            step["end_time"] = datetime.now().isoformat()
            raise
    
    async def _call_codestral_tool(self, localization_result: Dict[str, Any], bug_result: Dict[str, Any]) -> Dict[str, Any]:
        """Call the Codestral API tool directly."""
        step = {
            "step_name": "code_fix_generation",
            "start_time": datetime.now().isoformat(),
            "status": "in_progress"
        }
        bug_result["steps"].append(step)
        
        try:
            from codestral_api.codestral_tool import CodestralAPITool
            
            print("🤖 Generating code fixes...")
            codestral_tool = CodestralAPITool()
            fix_result = await codestral_tool.generate_fix(localization_result)
            
            step["status"] = "completed"
            step["end_time"] = datetime.now().isoformat()
            step["result"] = fix_result
            
            return fix_result
            
        except Exception as e:
            step["status"] = "failed"
            step["error"] = str(e)
            step["end_time"] = datetime.now().isoformat()
            raise
    
    async def _call_human_review_tool(self, fix_result: Dict[str, Any], bug_result: Dict[str, Any]) -> Dict[str, Any]:
        """Call the Human Review tool directly."""
        step = {
            "step_name": "human_review",
            "start_time": datetime.now().isoformat(),
            "status": "in_progress"
        }
        bug_result["steps"].append(step)
        
        try:
            from human_review.human_review_tool import HumanReviewTool
            
            print("👤 Requesting human review...")
            review_tool = HumanReviewTool()
            review_result = await review_tool.request_approval(fix_result)
            
            step["status"] = "completed"
            step["end_time"] = datetime.now().isoformat()
            step["result"] = review_result
            
            return review_result
            
        except Exception as e:
            step["status"] = "failed"
            step["error"] = str(e)
            step["end_time"] = datetime.now().isoformat()
            raise
    
    async def _call_git_patch_tool(self, fix_result: Dict[str, Any], bug_result: Dict[str, Any]) -> Dict[str, Any]:
        """Call the Git Patch Manager tool directly."""
        step = {
            "step_name": "patch_application",
            "start_time": datetime.now().isoformat(),
            "status": "in_progress"
        }
        bug_result["steps"].append(step)
        
        try:
            from git_patch_manager.git_patch_tool import GitPatchTool
            
            print("🔧 Applying patches...")
            patch_tool = GitPatchTool()
            patch_result = await patch_tool.apply_patch(fix_result)
            
            step["status"] = "completed"
            step["end_time"] = datetime.now().isoformat()
            step["result"] = patch_result
            
            return patch_result
            
        except Exception as e:
            step["status"] = "failed"
            step["error"] = str(e)
            step["end_time"] = datetime.now().isoformat()
            raise
    
    async def index_repository(self, repo_path: str, repo_name: str) -> str:
        """Index a repository using the repo indexer tool directly."""
        try:
            from repo_indexer.repo_indexer_tool import RepoIndexerTool
            
            print(f"📚 Indexing repository: {repo_name}")
            indexer = RepoIndexerTool()
            result = await indexer.index_repository(repo_path, repo_name)
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(error_result, indent=2)
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history for context."""
        return self.conversation_history
    
    def clear_conversation_history(self) -> None:
        """Clear the conversation history."""
        self.conversation_history = []
        print("🧹 Conversation history cleared")
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current solver configuration."""
        return {
            "session_id": self.session_id,
            "conversation_history_length": len(self.conversation_history),
            "tools_available": [
                "bug_locator_tool",
                "codestral_tool", 
                "human_review_tool",
                "git_patch_tool",
                "repo_indexer_tool"
            ]
        }