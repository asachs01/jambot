# Task ID: 14

**Title:** Persist Active Approval Workflows to Database

**Status:** done

**Dependencies:** 4, 5 ⧖, 13 ✓

**Priority:** high

**Description:** Create database persistence layer for approval workflows to prevent data loss during bot restarts, disconnections, or crashes by storing workflow state in a database table instead of memory-only storage.

**Details:**

PROBLEM ANALYSIS:
Currently, active_workflows is stored as an in-memory Dict in bot.py. When the bot restarts, disconnects, or crashes, all in-progress approval workflows are lost, forcing users to start over even if they've already made song selections.

DATABASE SCHEMA:
Create a new table in database.py:

```sql
CREATE TABLE active_workflows (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    summary_message_id BIGINT UNIQUE NOT NULL,
    original_channel_id BIGINT,
    original_message_id BIGINT,
    song_matches JSONB NOT NULL,  -- array of song match objects
    selections JSONB DEFAULT '{}',  -- song_number -> selected track mapping
    message_ids JSONB DEFAULT '[]',  -- array of DM message IDs
    approver_ids JSONB DEFAULT '[]',  -- array of approver user IDs
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_active_workflows_summary_message ON active_workflows(summary_message_id);
CREATE INDEX idx_active_workflows_guild ON active_workflows(guild_id);
```

IMPLEMENTATION STEPS:

1. **Update database.py schema initialization:**
   - Add active_workflows table creation to the init_db() or schema setup function
   - Include indices for fast lookups on summary_message_id and guild_id
   - Add updated_at trigger or handle in application code

2. **Add CRUD methods to database.py:**
   ```python
   def save_workflow(self, guild_id, summary_message_id, original_channel_id, 
                     original_message_id, song_matches, selections={}, 
                     message_ids=[], approver_ids=[]):
       """Insert new workflow into database"""
       # Convert Python objects to JSON for JSONB columns
       # Use parameterized query to prevent SQL injection
       # Return workflow ID
   
   def get_workflow(self, summary_message_id):
       """Retrieve workflow by summary message ID"""
       # Query by summary_message_id (indexed for performance)
       # Parse JSONB columns back to Python objects
       # Return workflow dict or None
   
   def get_all_active_workflows(self, guild_id=None):
       """Load all active workflows, optionally filtered by guild"""
       # Used during bot startup to restore state
       # Return list of workflow dicts
   
   def update_workflow_selection(self, summary_message_id, song_number, selected_track):
       """Update a single song selection in workflow"""
       # Update selections JSONB field
       # Update updated_at timestamp
       # Use atomic transaction
   
   def update_workflow(self, summary_message_id, **kwargs):
       """Update any workflow fields"""
       # Generic update method for selections, message_ids, approver_ids
       # Update updated_at timestamp
   
   def delete_workflow(self, summary_message_id):
       """Remove completed or cancelled workflow"""
       # Delete by summary_message_id
       # Return success boolean
   ```

3. **Update bot.py on_ready() event handler:**
   ```python
   async def on_ready(self):
       # Existing startup logic...
       
       # Load active workflows from database
       workflows = self.db.get_all_active_workflows()
       for workflow_data in workflows:
           # Reconstruct workflow dict from database record
           self.active_workflows[workflow_data['summary_message_id']] = {
               'guild_id': workflow_data['guild_id'],
               'original_channel_id': workflow_data['original_channel_id'],
               'original_message_id': workflow_data['original_message_id'],
               'song_matches': workflow_data['song_matches'],
               'selections': workflow_data['selections'],
               'message_ids': workflow_data['message_ids'],
               'approver_ids': workflow_data['approver_ids']
           }
       
       self.logger.info(f"Restored {len(workflows)} active workflows from database")
   ```

4. **Update send_approval_workflow() in bot.py:**
   - After creating workflow in memory, immediately persist to database
   ```python
   # After: self.active_workflows[summary_msg.id] = workflow
   self.db.save_workflow(
       guild_id=workflow['guild_id'],
       summary_message_id=summary_msg.id,
       original_channel_id=workflow['original_channel_id'],
       original_message_id=workflow['original_message_id'],
       song_matches=workflow['song_matches'],
       selections=workflow['selections'],
       message_ids=workflow['message_ids'],
       approver_ids=workflow['approver_ids']
   )
   ```

5. **Update reaction handler (on_raw_reaction_add):**
   - When updating selections in memory, also update database
   ```python
   # After updating workflow['selections'][song_number]
   self.db.update_workflow_selection(
       summary_message_id=payload.message_id,
       song_number=song_number,
       selected_track=selected_track
   )
   ```

6. **Update handle_dm_message() for manual song submissions:**
   - When user replies with Spotify URL, update database
   ```python
   # After: workflow['selections'][song_number] = track_data
   self.db.update_workflow_selection(
       summary_message_id=workflow_key,
       song_number=song_number,
       selected_track=track_data
   )
   ```

7. **Update cleanup_workflow() in bot.py:**
   - Delete from database when workflow completes or is cancelled
   ```python
   def cleanup_workflow(self, summary_message_id):
       if summary_message_id in self.active_workflows:
           del self.active_workflows[summary_message_id]
       
       # Delete from database
       self.db.delete_workflow(summary_message_id)
       self.logger.info(f"Cleaned up workflow {summary_message_id}")
   ```

8. **Error Handling:**
   - Wrap all database operations in try/except blocks
   - Log database errors but don't crash the bot
   - If DB write fails, keep in-memory state and retry on next update
   - Consider adding a background task to sync memory to DB periodically

9. **Migration Considerations:**
   - Add schema migration script or use Alembic
   - Handle existing in-memory workflows during deployment (optional: persist before shutdown)
   - Add database version tracking

TECHNICAL CONSIDERATIONS:
- Use parameterized queries to prevent SQL injection
- Ensure atomic transactions for all workflow updates
- Handle JSON serialization/deserialization carefully (datetime objects, etc.)
- Consider adding workflow expiration (auto-cleanup after 24-48 hours)
- Add logging for all database operations for debugging
- Test with SQLite's JSONB support (or JSON for older versions)

**Test Strategy:**

1. **Schema Validation:**
   - Run database initialization and verify active_workflows table is created
   - Confirm all columns, data types, and constraints are correct
   - Verify indices exist on summary_message_id and guild_id
   - Check JSONB columns can store and retrieve complex objects

2. **CRUD Operations Test:**
   - Test save_workflow() with complete workflow data
   - Test get_workflow() retrieves correct workflow by summary_message_id
   - Test get_all_active_workflows() returns all workflows, filtered by guild
   - Test update_workflow_selection() updates specific song selection
   - Test delete_workflow() removes workflow from database
   - Verify all operations use parameterized queries (check SQL logs)

3. **Bot Startup Restoration Test:**
   - Create 2-3 active workflows with different states (some with selections, some without)
   - Verify workflows are persisted to database
   - Restart the bot (simulate disconnect/crash)
   - Confirm on_ready() loads all workflows from database into memory
   - Verify self.active_workflows dict matches database state
   - Check logs confirm number of restored workflows

4. **End-to-End Workflow Persistence Test:**
   - Trigger setlist detection to create new workflow
   - Verify workflow is saved to database immediately
   - Make song selections via reactions
   - Query database and confirm selections are updated
   - Reply to DM with manual Spotify URL
   - Verify database reflects manual selection
   - Complete workflow with ✅ reaction
   - Confirm workflow is deleted from database after completion

5. **Bot Restart During Active Workflow Test:**
   - Start approval workflow and make partial song selections
   - Query database to confirm workflow and selections are persisted
   - Restart bot while workflow is active
   - Verify workflow is restored to memory on startup
   - Continue making selections and verify they update in database
   - Complete workflow and verify it's cleaned up from database

6. **Concurrent Workflow Test:**
   - Create multiple workflows simultaneously (different setlists/guilds)
   - Verify each workflow has unique summary_message_id
   - Update selections in different workflows
   - Confirm database maintains separate state for each workflow
   - Complete one workflow, verify others remain in database

7. **Error Handling Test:**
   - Simulate database connection failure during workflow save
   - Verify bot logs error but doesn't crash
   - Simulate database failure during selection update
   - Confirm in-memory state is maintained
   - Test recovery when database connection is restored

8. **Data Integrity Test:**
   - Create workflow with complex song_matches (multiple tracks, metadata)
   - Verify JSONB serialization preserves all data
   - Retrieve workflow and confirm all fields match original
   - Test with special characters, Unicode, and edge cases in song data

9. **Cleanup and Expiration Test:**
   - Create workflow and complete it
   - Verify delete_workflow() removes it from database
   - Create workflow and cancel it (if cancellation feature exists)
   - Confirm cancelled workflows are also cleaned up
   - Query database to ensure no orphaned workflow records

10. **Performance Test:**
    - Create 10+ workflows and measure get_workflow() query time
    - Verify index on summary_message_id provides fast lookups (<10ms)
    - Test get_all_active_workflows() with multiple guilds
    - Confirm queries scale reasonably with workflow count
