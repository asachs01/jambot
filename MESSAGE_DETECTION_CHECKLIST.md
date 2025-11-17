# Message Detection Checklist

Your bot is **ONLINE** ✅ but not detecting messages. Work through this checklist:

## 1. Message Content Intent (START HERE)

**This is almost always the issue.**

- [ ] Go to https://discord.com/developers/applications
- [ ] Select your Jambot application
- [ ] Click "Bot" in the sidebar
- [ ] Scroll to "Privileged Gateway Intents"
- [ ] **Verify "Message Content Intent" is ON (blue toggle)**
- [ ] Click "Save Changes" if you made changes
- [ ] Run: `docker compose down && docker compose up -d`

## 2. User ID Verification

- [ ] Your user ID should be: **616276609514733619**
- [ ] In Discord: Settings → Advanced → Enable "Developer Mode"
- [ ] Right-click your username → Copy User ID
- [ ] Verify it matches the ID above

## 3. Channel Access

- [ ] Open the channel where you want to post setlists
- [ ] Look at the member list (right side)
- [ ] Verify **jambot** appears in the list
- [ ] If not, add the bot with "View Channel" permission

## 4. Test Message

Post this exact message in the channel:

```
Here's the setlist for the 7pm jam on November 20th.

1. Will the Circle Be Unbroken
2. Rocky Top
3. Man of Constant Sorrow
```

**Requirements**:
- Must include "here's the setlist for the [TIME] jam on [DATE]**.**" (period required!)
- Songs must be numbered "1. Song Title"
- Posted from user ID 616276609514733619

## 5. Check Logs

Run:
```bash
docker compose logs -f
```

**You should see**:
```
jambot | INFO - Received message from <yourname> (ID: 616276609514733619)
jambot | INFO - Message content preview: Here's the setlist for the 7pm jam...
jambot | INFO - Detected setlist message from jam leader in channel 123456789
```

## 6. Diagnosis Table

| What the logs show | The problem is |
|-------------------|----------------|
| Nothing when you post | ⚠️ Message Content Intent not enabled OR bot can't see channel |
| "Received message" with different user ID | Wrong Discord account posting the message |
| "Received message" but not "Detected setlist" | Message format doesn't match the pattern |
| "Detected setlist message" | ✅ **IT'S WORKING!** Check for DM from bot |

## Current Status

Bot Status: **ONLINE** ✅
- Bot logged in as: jambot#5019 (ID: 1438934867021795358)
- Monitoring user ID: 616276609514733619
- Logs show: Bot successfully connected to Discord Gateway

Next Step: **Check Message Content Intent** (Step 1 above)

## Still Not Working?

See full troubleshooting guide: `TROUBLESHOOTING.md`
