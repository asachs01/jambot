# Task ID: 3

**Title:** Setlist Message Parsing and Extraction

**Status:** pending

**Dependencies:** 2

**Priority:** high

**Description:** Parse detected setlist messages, extract jam date, time, and song list, allowing for minor intro text variations.

**Details:**

Use regular expressions to match setlist patterns, extracting date, time, and numbered song titles (strip key info). Implement robust parsing to handle minor variations in intro text. Validate extracted data and log warnings for unrecognized formats. Store parsed setlist in memory for further processing.

**Test Strategy:**

Test with multiple setlist message formats. Validate extraction accuracy against acceptance criteria. Log and skip unrecognized formats.
