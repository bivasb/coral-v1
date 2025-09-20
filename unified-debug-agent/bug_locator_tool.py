# Direct import compatibility for bug_locator_tool
# This allows "import bug_locator_tool" to work

from tools.bug_locator.bug_locator_tool import bug_locator_tool, BugLocatorTool

# Alias for compatibility with Unified Debug Agent
async def locate_bug_in_repository(bug_description: str, repository_name: str, similarity_threshold: float = 0.7, max_results: int = 10):
    """
    Compatibility wrapper for Unified Debug Agent.
    Maps to the bug_locator_tool function.
    """
    return await bug_locator_tool(
        bug_description=bug_description,
        repository_name=repository_name,
        similarity_threshold=similarity_threshold,
        max_results=max_results
    )

# Make the function and class available at module level
__all__ = ['bug_locator_tool', 'BugLocatorTool', 'locate_bug_in_repository']