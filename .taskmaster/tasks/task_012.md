# Task ID: 12

**Title:** Fix Workflow Cleanup Bug: Preserve Active Workflows When Missing Songs Detected

**Status:** done

**Dependencies:** 6, 8

**Priority:** high

**Description:** Fix the bug where re-adding ✅ reaction after fixing missing song selections doesn't trigger playlist creation because the workflow is prematurely cleaned up in the finally block.

**Details:**

ROOT CAUSE: The create_playlist_from_workflow() function in src/bot.py (lines 764-772) has a try/finally block where cleanup_workflow() is unconditionally called in the finally clause. When missing songs are detected (lines 641-664), the function returns early but the finally block still executes, removing the workflow from self.active_workflows. When users later fix missing songs and re-add ✅, on_raw_reaction_add() can't find the workflow and silently ignores the reaction.

IMPLEMENTATION STEPS:
1. Remove cleanup_workflow() from the finally block (lines 764-772) in create_playlist_from_workflow()
2. Add explicit cleanup_workflow() call at the end of successful playlist creation path (after playlist is created and posted)
3. Ensure cleanup_workflow() is called in the cancellation handler (❌ reaction path)
4. Do NOT call cleanup_workflow() when returning early due to missing songs (lines 641-664) - the workflow must remain active
5. Add logging statements to track workflow lifecycle:
   - Log when workflow is created/added to active_workflows
   - Log when missing songs are detected (workflow should remain active)
   - Log when workflow is successfully completed (before cleanup)
   - Log when workflow is cancelled (before cleanup)
   - Log when cleanup_workflow() is called with workflow_id

SPECIFIC CODE CHANGES:
- src/bot.py lines 764-772: Remove the finally block entirely or remove cleanup_workflow() from it
- src/bot.py lines 641-664: Add logging statement confirming workflow remains active when missing songs detected
- src/bot.py: Add cleanup_workflow() call after successful playlist creation (after posting to Discord)
- src/bot.py lines 565-624: Verify on_raw_reaction_add() properly handles re-triggering for existing workflows
- src/bot.py: Add cleanup_workflow() to cancellation (❌) reaction handler if not already present
- Add debug logging throughout workflow lifecycle for troubleshooting

EDGE CASES TO HANDLE:
- Multiple missing song detection cycles (user adds ✅ multiple times before fixing all songs)
- User cancels (❌) after missing songs detected - should still clean up
- Concurrent reactions on same workflow
- Workflow timeout scenarios (if implemented)

**Test Strategy:**

1. MISSING SONGS WORKFLOW TEST:
   - Trigger setlist detection with intentionally incomplete song selections
   - Add ✅ reaction and verify error message is sent indicating missing songs
   - Check logs to confirm workflow remains in active_workflows (not cleaned up)
   - Select the missing songs using number reactions
   - Remove and re-add ✅ reaction
   - Verify playlist creation is successfully triggered
   - Confirm workflow is cleaned up after successful creation

2. SUCCESSFUL CREATION TEST:
   - Complete full workflow with all songs selected
   - Add ✅ reaction
   - Verify playlist is created and posted
   - Check logs to confirm cleanup_workflow() is called
   - Verify workflow is removed from active_workflows

3. CANCELLATION TEST:
   - Start workflow with missing songs
   - Add ✅ to trigger missing songs error
   - Add ❌ reaction to cancel
   - Verify workflow is cleaned up
   - Check logs to confirm cleanup_workflow() was called

4. MULTIPLE MISSING SONGS CYCLES:
   - Add ✅ with some songs missing
   - Select some (but not all) missing songs
   - Re-add ✅ and verify still shows missing songs error
   - Workflow should still be active
   - Complete all selections and re-add ✅
   - Verify successful playlist creation

5. LOGGING VERIFICATION:
   - Review logs for all test scenarios
   - Confirm workflow lifecycle is properly tracked (creation, missing songs detection, completion, cleanup)
   - Verify no silent failures or orphaned workflows

6. REGRESSION TEST:
   - Run through normal happy path workflow to ensure no functionality was broken
   - Verify all existing approval scenarios still work correctly
