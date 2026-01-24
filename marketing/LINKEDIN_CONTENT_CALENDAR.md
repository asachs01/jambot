# JamBot LinkedIn Social Media Calendar (90 Days)

A content strategy for sharing the JamBot story with engineers, open source enthusiasts, and musicians who code.

## Target Audience

- Engineers interested in niche open source projects
- Discord bot developers
- Musicians who code
- Open source community members

## Key Themes

1. **Building a niche open source project** that solves a real problem
2. **Discord bot architecture** and patterns
3. **Database design decisions** (SQLite → PostgreSQL migration)
4. **OAuth/API integration patterns** (Spotify, Discord)
5. **Community-driven development**

## Content Guidelines

### Post Format
- **Hook**: First line must grab attention (question, surprising fact, or relatable pain)
- **Length**: 150-250 words optimal for LinkedIn
- **Code snippets**: Use images (Carbon or similar) - LinkedIn doesn't render code well
- **Hashtags**: #OpenSource #DiscordBot #Python #MusicTech #SoftwareEngineering
- **CTA**: End with question or invitation to engage

### Content Creation Workflow
1. Draft post in markdown
2. Create any code snippet images (Carbon or similar)
3. Schedule via LinkedIn or Buffer
4. Engage with comments within 2 hours of posting

---

## Month 1: Introduction & Problem Space (Weeks 1-4)

### Week 1

#### Post 1 (Story)
**Topic**: "Why I built a Discord bot for my bluegrass jam group"

**Hook**: "I spent 2 hours every week manually creating Spotify playlists from jam session setlists. Then I built a bot to do it in 30 seconds."

**Key Points**:
- Personal story about the manual playlist creation pain
- Weekly jam sessions generate setlists that need playlists
- The friction of searching each song individually
- How automation improved the jam experience

**CTA**: "What repetitive tasks have you automated away?"

---

#### Post 2 (Technical)
**Topic**: "The problem with shared Spotify API credentials at scale"

**Hook**: "Using one Spotify API key for 50+ Discord servers? You'll hit rate limits fast. Here's the pattern I use instead."

**Key Points**:
- Shared credentials lead to rate limiting
- Per-guild credential pattern
- How OAuth tokens are stored per-server
- The security implications of multi-tenant credential storage

**CTA**: "How do you handle API credentials in multi-tenant applications?"

---

### Week 2

#### Post 3 (Story)
**Topic**: "How a side project became essential infrastructure for 50+ musicians"

**Hook**: "My jam group can't imagine doing setlists without the bot now. What started as a weekend project now handles hundreds of songs."

**Key Points**:
- Community adoption story
- Feature requests from real users
- The feeling of building something people depend on
- Open source as community building

**CTA**: "What side project unexpectedly became important to someone?"

---

#### Post 4 (Technical)
**Topic**: "Designing a bot that remembers: Song version memory in Discord bots"

**Hook**: "The same song title can have 20+ versions on Spotify. How do you remember which version your community prefers?"

**Key Points**:
- Database-backed song memory
- Per-guild song preferences
- The UX of "pre-approved" vs "needs selection"
- How memory improves over time

**CTA**: "What data persistence patterns work well for bots?"

---

### Week 3

#### Post 5 (Demo)
**Topic**: Visual workflow demonstration

**Format**: Video/GIF showing the workflow from setlist → playlist

**Hook**: "From Discord message to Spotify playlist in 30 seconds. Here's how JamBot works:"

**Key Points**:
- Show the jam leader posting a setlist
- Bot detection and parsing
- Approval workflow DM
- Final playlist creation

**CTA**: "Want to try it for your music community? Link in comments."

---

#### Post 6 (Insight)
**Topic**: "The UX of emoji reactions: Why I chose reactions over text commands"

**Hook**: "Text commands feel like coding. Emoji reactions feel like voting. For music selection, voting wins."

**Key Points**:
- Approval workflows with 1️⃣ 2️⃣ 3️⃣ reactions
- Lower cognitive load than typing
- The accessibility of visual selection
- Why Discord's reaction API is powerful

**CTA**: "What interaction patterns do you prefer for Discord bots?"

---

### Week 4

#### Post 7 (Technical)
**Topic**: "Modal-based Discord configuration: Zero downtime config changes"

**Hook**: "Editing .env files and restarting your bot for every config change? There's a better way."

**Key Points**:
- Discord modals for configuration
- No-restart architecture
- Per-server settings stored in database
- The /jambot-setup experience

**CTA**: "How do you handle config in production bots?"

---

#### Post 8 (Community)
**Topic**: "What I learned about building for a niche community"

**Hook**: "Bluegrass musicians aren't your typical tech users. Building for them taught me about real-world UX."

**Key Points**:
- Understanding domain-specific needs
- The importance of fuzzy matching for song names
- Building trust through reliability
- Open source lessons from niche communities

**CTA**: "What niche community have you built for?"

---

## Month 2: Technical Deep Dives (Weeks 5-8)

### Week 5

#### Post 9 (Technical)
**Topic**: "From SQLite to PostgreSQL: Migrating a production Discord bot"

**Hook**: "SQLite worked great for 1 server. Then server #50 joined and I needed real concurrent writes."

**Key Points**:
- When SQLite stops being enough
- Migration strategy without downtime
- DigitalOcean managed PostgreSQL
- The reliability improvements

**CTA**: "Have you migrated a production database? What was your strategy?"

---

#### Post 10 (Architecture)
**Topic**: "Why I use JSONB for workflow state in PostgreSQL"

**Hook**: "Storing approval workflow state in relational tables felt wrong. JSONB gave me the flexibility I needed."

**Key Points**:
- Flexible schema patterns with JSONB
- When to use JSONB vs relational
- The active_workflows table design
- Querying JSONB efficiently

**CTA**: "JSONB vs separate tables - what's your preference?"

---

### Week 6

#### Post 11 (Technical)
**Topic**: "Handling Spotify OAuth in headless containers"

**Hook**: "Spotify OAuth wants a browser. My bot runs in a headless container. Here's how I bridged that gap."

**Key Points**:
- MemoryCacheHandler pattern
- Token storage in database
- Web callback flow for initial auth
- Automatic token refresh

**CTA**: "What OAuth challenges have you faced in headless environments?"

---

#### Post 12 (Debugging)
**Topic**: "The bug that taught me about JSONB string keys"

**Hook**: "My workflow selections kept disappearing after restarts. The bug? JSONB always uses string keys."

**Key Points**:
- Real debugging story
- Integer keys vs string keys in JSONB
- How I found the issue
- The fix and lessons learned

**CTA**: "What's a subtle bug that taught you something important?"

---

### Week 7

#### Post 13 (Technical)
**Topic**: "Building resilient API integrations with exponential backoff"

**Hook**: "Spotify rate limits hit hard. Here's how my bot survives and keeps working."

**Key Points**:
- Retry patterns with exponential backoff
- Jitter for avoiding thundering herd
- Logging retry attempts
- When to give up

**CTA**: "What retry strategies do you use for external APIs?"

---

#### Post 14 (Architecture)
**Topic**: "Health checks that actually work: Monitoring Discord connections"

**Hook**: "A 200 OK from /health doesn't mean your Discord bot is connected. Here's what I check instead."

**Key Points**:
- Discord connection state tracking
- Health check that returns 503 when disconnected
- Automatic restart triggers
- Production reliability patterns

**CTA**: "What do your health checks actually verify?"

---

### Week 8

#### Post 15 (Technical)
**Topic**: "Fuzzy song matching for bluegrass: When exact search isn't enough"

**Hook**: "'Will the Circle' vs 'Will the Circle Be Unbroken' - same song, different search results."

**Key Points**:
- Domain-specific song variations
- Building a variations dictionary
- Search fallback strategies
- When to ask the user

**CTA**: "How do you handle fuzzy matching in your applications?"

---

#### Post 16 (Lesson)
**Topic**: "What happens when your Discord bot disconnects mid-workflow"

**Hook**: "A user was mid-approval when my bot restarted. Their progress was gone. Never again."

**Key Points**:
- Persistence patterns for long-running operations
- Restoring workflows from database
- The importance of idempotency
- User experience during failures

**CTA**: "How do you handle state recovery after unexpected restarts?"

---

## Month 3: Community & Open Source (Weeks 9-13)

### Week 9

#### Post 17 (Open Source)
**Topic**: "Making your Discord bot configurable per-server"

**Hook**: "One Discord bot, 50 servers, 50 different configurations. No hardcoding allowed."

**Key Points**:
- Multi-tenant patterns
- Guild-specific configuration tables
- Permission checking per server
- The joy of per-server Spotify credentials

**CTA**: "What multi-tenant patterns do you use?"

---

#### Post 18 (Community)
**Topic**: "Feature requests from my jam group that made it to production"

**Hook**: "Our bass player asked for custom setlist patterns. Two days later, it shipped."

**Key Points**:
- User-driven development
- Short feedback loops in niche communities
- Prioritizing real user needs
- The value of dogfooding

**CTA**: "What feature requests have shaped your projects?"

---

### Week 10

#### Post 19 (Technical)
**Topic**: "Testing Discord bots: What I wish I knew earlier"

**Hook**: "Unit tests pass. Integration tests pass. Bot deployed. Bot immediately broke. Sound familiar?"

**Key Points**:
- Testing strategies for Discord bots
- Mocking Discord API
- Testing reaction handlers
- When to test manually vs automatically

**CTA**: "How do you test your Discord bots?"

---

#### Post 20 (Story)
**Topic**: "The approval workflow: Designing for trust in music selection"

**Hook**: "Not everyone in the jam group trusts the bot to pick the right song version. That's okay."

**Key Points**:
- UX design for trust
- Human-in-the-loop patterns
- Pre-approved vs needs-review
- Building confidence over time

**CTA**: "How do you build trust in automated systems?"

---

### Week 11

#### Post 21 (Open Source)
**Topic**: "Documentation that developers actually read"

**Hook**: "I wrote a 50-page README. Nobody read it. Then I built a documentation site."

**Key Points**:
- Astro Starlight for docs
- Progressive disclosure of information
- Quick start vs deep dive
- The value of visual documentation

**CTA**: "What documentation approaches work for your projects?"

---

#### Post 22 (Community)
**Topic**: "Running a Discord bot on $5/month: DigitalOcean App Platform"

**Hook**: "My bot serves 50+ servers for the cost of a fancy coffee."

**Key Points**:
- Cost-effective hosting
- DigitalOcean App Platform worker
- PostgreSQL managed database
- When to scale up

**CTA**: "What hosting do you use for side projects?"

---

### Week 12

#### Post 23 (Retrospective)
**Topic**: "6 months of JamBot: What worked, what didn't"

**Hook**: "Not everything I built was a good idea. Here's an honest retrospective."

**Key Points**:
- Honest reflection on the project
- Features that worked well
- Ideas that didn't land
- What I'd do differently

**CTA**: "What lessons have you learned from your side projects?"

---

#### Post 24 (Technical)
**Topic**: "Adding workflow persistence: Never lose an in-progress approval"

**Hook**: "Bot restarts used to lose all pending approvals. Now they survive anything."

**Key Points**:
- Reliability engineering for Discord bots
- Persisting workflow state to database
- Restoring on startup
- User experience during restarts

**CTA**: "How reliable are your side projects?"

---

### Week 13

#### Post 25 (Call to Action)
**Topic**: "Try JamBot for your jam group - it's free and open source"

**Hook**: "If you run a music jam or any Discord community that needs playlists, JamBot might be for you."

**Key Points**:
- Community invitation
- Link to GitHub
- Link to documentation
- How to get started

**CTA**: "Know a jam group that would benefit? Share this with them!"

---

## Posting Schedule

| Day | Post Type | Optimal Time |
|-----|-----------|--------------|
| Tuesday | Technical | 8-9 AM local |
| Thursday | Story/Community | 12-1 PM local |

## Engagement Strategy

1. **Respond to all comments** within 2 hours of posting
2. **Ask follow-up questions** to generate discussion
3. **Cross-post** relevant content to Twitter/X with shorter format
4. **Engage with related posts** in the Python, Discord, and music tech communities

## Metrics to Track

- Post impressions
- Engagement rate (comments + reactions / impressions)
- Profile views
- Follower growth
- GitHub stars correlation
- Documentation site traffic

## Content Assets to Create

1. **JamBot logo** - for consistent branding
2. **Carbon code snippets** - for technical posts
3. **Screen recordings** - for demo posts
4. **Architecture diagrams** - for technical deep dives
5. **Before/after comparisons** - for problem/solution posts
