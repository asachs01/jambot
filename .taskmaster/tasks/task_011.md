# Task ID: 11

**Title:** Implement Modal-Based Configuration System for Jam Leaders and Approvers

**Status:** in-progress

**Dependencies:** 2, 4

**Priority:** medium

**Description:** Replace environment variable configuration for jam leaders and song approvers with a Discord modal-based UI, accessible via a /jambot setup slash command, storing configuration in the database and enforcing admin-only access.

**Details:**

1. Use discord.py v2.x's support for modals and slash commands to implement a /jambot setup command. When invoked, check that the user has administrator permissions in the server (using `interaction.user.guild_permissions.administrator`).

2. On valid invocation, present a modal to the user. The modal should include Discord user select components for configuring multiple jam leaders and song approvers. Use the Discord API's User Select component in modals, allowing up to 25 users per select as per Discord's documented limits[2].

3. On modal submission, extract the selected user IDs for both jam leaders and approvers from the interaction data. Validate that at least one jam leader and one approver are selected.

4. Store the configuration in the database (e.g., a new 'configuration' table or as part of a 'settings' table), associating the selected user IDs with the guild/server ID. Ensure atomic writes and handle concurrent updates safely.

5. Remove any use of environment variables for jam leader and approver configuration. Retain environment variables only for bot token and Spotify credentials.

6. Provide clear feedback to the admin on success or failure of the configuration update, and log all configuration changes for audit purposes.

7. Follow Discord's best practices for modal interaction handling: show the modal as the first response to the slash command interaction, and handle modal submissions in a dedicated event handler[3][5].

8. Ensure code is well-structured, with clear separation between command registration, permission checks, modal construction, submission handling, and database operations.

**Test Strategy:**

1. Register the /jambot setup command and verify it is only accessible to server admins.

2. Invoke the command as an admin and confirm the modal appears with user select components for both jam leaders and approvers, supporting multiple selections.

3. Submit the modal with various valid and invalid combinations (e.g., no selection, duplicate users) and verify correct validation and error handling.

4. Check that the selected user IDs are correctly stored in the database and associated with the correct guild.

5. Attempt to invoke the command as a non-admin and confirm access is denied.

6. Confirm that environment variables for jam leader and approver are no longer used, and that bot token and Spotify credentials remain environment-based.

7. Review logs to ensure all configuration changes are recorded with timestamps and user IDs.

8. Simulate concurrent configuration updates and verify database consistency.

## Subtasks

### 11.1. Register /jambot setup Slash Command with Admin-Only Access

**Status:** done  
**Dependencies:** None  

Implement the /jambot setup slash command using discord.py v2.x, ensuring only server administrators can invoke it.

**Details:**

Use discord.py's app_commands to register the slash command. In the command handler, check interaction.user.guild_permissions.administrator before proceeding. If the user lacks permissions, respond with an error message and do not show the modal.

### 11.2. Design and Present Modal with User Select Components for Jam Leaders and Approvers

**Status:** done  
**Dependencies:** 11.1  

Create a modal dialog that allows admins to select multiple Discord users as jam leaders and song approvers, using Discord's User Select component.

**Details:**

On valid command invocation, present a modal using discord.ui.Modal. Add two user select components, each supporting up to 25 users, for jam leaders and approvers. Ensure the modal is shown as the first response to the interaction.

### 11.3. Handle Modal Submission and Validate Selected Users

**Status:** done  
**Dependencies:** 11.2  

Process modal submissions, extract selected user IDs for jam leaders and approvers, and validate that at least one user is selected for each role.

**Details:**

Implement a callback for modal submission. Extract user IDs from the interaction data. Check that at least one jam leader and one approver are selected. If validation fails, send an error message to the admin.

### 11.4. Store Configuration in Database and Remove Environment Variable Usage

**Status:** done  
**Dependencies:** 11.3  

Persist the selected jam leaders and approvers in the database, associating them with the guild ID, and eliminate environment variable usage for these roles.

**Details:**

Create or update a configuration/settings table in the database to store user IDs for jam leaders and approvers per guild. Ensure atomic writes and safe concurrent updates. Refactor code to remove environment variable checks for these roles, retaining them only for bot token and Spotify credentials.

### 11.5. Provide Feedback, Log Configuration Changes, and Ensure Code Structure

**Status:** done  
**Dependencies:** 11.4  

Send clear feedback to admins on configuration success or failure, log all changes for audit, and maintain separation of concerns in code structure.

**Details:**

After database update, send a success or error message to the admin. Log all configuration changes with timestamp, user, and details. Ensure code is organized with separate modules/functions for command registration, permission checks, modal construction, submission handling, and database operations.
