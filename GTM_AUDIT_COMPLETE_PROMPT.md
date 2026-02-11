# GTM AUDIT PLATFORM - COMPLETE SPECIFICATION & CLAUDE CODE PROMPT

---

## COMPLETE CLAUDE CODE PROMPT

Copy everything below into Claude Code:

---

```
You are architecting a production-grade B2B SaaS platform called "GTM Audit" - 
an AI-powered marketing consultant tool for freelance consultants analyzing 
SaaS companies' go-to-market strategies.

## PROJECT SPECIFICATION

### CORE REQUIREMENTS
- Multi-agent AI system with 12 specialized agents + 1 Project Lead orchestrator
- Password-protected online application using Streamlit (frontend) + FastAPI (backend)
- GitHub integration for deployment and version control
- Comprehensive company analysis in 30-45 minutes for full audits, 10-15 minutes for quick audits
- Interactive HTML report + Markdown export for easy editing
- Database persistence of audit results

### USER FLOW
1. User authenticates with password
2. Submits target company website URL (optional files)
3. Selects audit type (quick/full)
4. Watches real-time progress dashboard showing all 12 agents working in parallel
5. Receives comprehensive HTML report with 50+ pages of analysis (full audit)
6. Can download as HTML/Markdown/PDF
7. Can view audit history

### TEAM STRUCTURE & AGENT RESPONSIBILITIES

**Project Lead (Orchestrator)**
- Spawns and monitors all 11 specialist agents
- Manages parallel execution and resource allocation
- Aggregates findings
- Handles error recovery
- Updates user progress

**11 Specialist Agents:**
1. Web Scraper Agent - Crawls 20-30 pages, takes screenshots, extracts structure
2. Company Research Agent - Crunchbase, LinkedIn, funding/growth data
3. Competitor Intelligence Agent - Identifies & analyzes 5-10 competitors
4. Review & Sentiment Agent - G2/Capterra sentiment analysis, NPS benchmark
5. SEO & Visibility Agent - Technical SEO, keywords, rankings, Core Web Vitals
6. Messaging & Positioning Agent - Value prop, headlines, messaging clarity
7. Visual & Design Agent - Layout, color, imagery, CTA effectiveness
8. Conversion Optimization Agent - Funnel, forms, trust signals, CRO roadmap
9. Social & Engagement Agent - Social presence, content, engagement analysis
10. ICP & Segmentation Agent - Buyer personas, market segments, firmographics
11. Report Generation Agent - Synthesizes all findings into HTML/Markdown report

### TECHNICAL ARCHITECTURE

**Frontend (Streamlit)**
- Password login page
- Input collection (URL, optional files, audit type)
- Real-time progress dashboard (12 agent progress bars)
- Interactive report viewer with expandable sections
- Download/share functionality

**Backend (FastAPI)**
- REST API for audit operations
- WebSocket for real-time progress updates
- Background task queue (Celery/RQ) for parallel agent execution
- PostgreSQL database for audit storage
- Redis for message queuing between agents

**External Integrations**
- Web scraping (Selenium/Playwright with Puppeteer for screenshots)
- Vector database (Pinecone) for semantic search on scraped content
- Claude API for multi-agent LLM reasoning
- External APIs: G2/Capterra, Crunchbase, LinkedIn, SEMrush (SEO data)

### ANALYSIS DIMENSIONS (For Each Agent)

1. **Positioning & Messaging**: Value prop clarity, target audience alignment, USP
2. **ICP & Segmentation**: Firmographics, behavioral data, segment-specific messaging
3. **SEO & Visibility**: Technical SEO, keywords, rankings, page speed, Core Web Vitals
4. **Conversion Rate Optimization**: Funnel analysis, forms, CTAs, trust signals
5. **Visual & Design**: Color, typography, imagery, layout, mobile UX
6. **Reviews & Sentiment**: Net sentiment, themes, NPS benchmark, pain points
7. **Competitor Analysis**: Messaging matrix, feature comparison, pricing
8. **Social Media**: Platform presence, engagement, content strategy
9. **Website Content**: Comprehensiveness, case studies, educational content
10. **Brand Perception**: Consistency, thought leadership, press mentions

### REPORT DELIVERABLE

**Structure**: 50+ pages for full audits
- Executive summary with overall GTM health score (0-100) and top 20 priorities
- 10 detailed analysis sections (500-1000 words each)
- 50+ annotated screenshots showing specific issues
- Scoring/grading in each area
- Prioritized action plan (quick wins, medium-term, long-term)
- Success metrics for each recommendation

**Formats**: 
- Interactive HTML (embeddable in Streamlit)
- Markdown (for easy editing)
- PDF (downloadable)

### RECOMMENDATIONS FRAMEWORK

Each recommendation must include:
- Current State (screenshot evidence)
- Best Practice (industry standard)
- Impact Potential (Low/Medium/High)
- Effort Required (Low/Medium/High)
- Specific Implementation Steps (3-5 steps)
- Success Metrics
- Timeline Estimate

### SECURITY REQUIREMENTS
- Password authentication (single password for all users)
- HTTPS/SSL enforcement
- Secure session management
- Rate limiting (5 audits/hour)
- Audit logging
- No long-term data retention (28-day TTL option)
- GDPR compliant
- Secure API key management for external services

### COMMUNICATION BETWEEN AGENTS

**Message Format (JSON)**
```json
{
  "sender": "agent_name",
  "timestamp": "ISO8601",
  "message_type": "task_request|task_completion|error|update",
  "task_id": "unique_id",
  "data": {...},
  "priority": "high|normal|low"
}
```

**Execution Pattern**
1. Project Lead validates input and stores audit record
2. Spawns all 11 agents simultaneously
3. Agents push progress updates to Redis queue (every 30 seconds)
4. Agents store results in shared PostgreSQL cache tables
5. Report Agent polls for completion status
6. Once all agents finish (or timeout after 45 min), Report Agent synthesizes
7. Final report stored in database and shared link generated

**Error Handling**
- Automatic retry 3x with exponential backoff for failed tasks
- Partial failure handling (continue with available data)
- Fallback data sources if APIs fail

### SUCCESS CRITERIA

The application is "done" when:
1. Password authentication works (one password for all users)
2. Full audit completes in 30-45 minutes with real-time progress tracking
3. Quick audit completes in 10-15 minutes
4. All 12 agents execute in parallel (no bottlenecks)
5. Report includes all 10 analysis areas with specific evidence
6. 50+ screenshots with annotations included in full audit reports
7. HTML/Markdown/PDF export formats work correctly
8. Audit history persists in database
9. Share links work and generate unique URLs
10. No API keys exposed in code or logs

### IMPLEMENTATION PRIORITY

**Phase 1 (Foundation)**
- Streamlit UI shell with password auth
- FastAPI backend with basic CRUD endpoints
- PostgreSQL setup and schema

**Phase 2 (Core Agents)**
- Web Scraper Agent (essential for other agents)
- Company Research Agent
- Basic Report Generation (text only)

**Phase 3 (Specialized Agents)**
- SEO Agent
- Messaging Agent  
- Design Agent
- Competitor Agent

**Phase 4 (Polish)**
- CRO Agent
- Review Agent
- Social Agent
- ICP Agent

**Phase 5 (Report & UX)**
- Enhanced Report Generation with screenshots
- HTML/Markdown/PDF export
- Progress dashboard UI
- Share link functionality

**Phase 6 (Production)**
- Security hardening
- Performance optimization
- Error handling and logging
- Deployment to cloud (GCP/AWS with GitHub Actions)

### TECHNOLOGY CHOICES

- Frontend: Streamlit (rapid development, built-in components)
- Backend: FastAPI (async, high performance, OpenAPI docs)
- Database: PostgreSQL (reliable, relational data)
- Vector DB: Pinecone (semantic search on documents)
- Task Queue: Celery (scalable distributed task processing)
- Web Scraping: Selenium/Playwright (JavaScript rendering + screenshots)
- Report Generation: Weasyprint (HTML to PDF conversion)
- LLM: Claude API (via Anthropic SDK)
- Deployment: Docker + GitHub Actions + Cloud Run/ECS

### CODE QUALITY STANDARDS

- Type hints throughout (Python 3.10+)
- Comprehensive error handling and logging
- Separation of concerns (agents isolated, clean APIs)
- Async/await for I/O-bound operations
- Environment variables for configuration
- Unit tests for critical functions
- Clear docstrings on all functions and classes
- GitHub-ready codebase with proper .gitignore

### NEXT STEPS

Start with the project structure, requirements.txt, and foundational code:
1. Create directory structure with clear separation (frontend/, backend/, agents/, config/)
2. Set up FastAPI backend with basic endpoints
3. Create Streamlit frontend shell with password login
4. Implement PostgreSQL schema and ORM models
5. Build Project Lead orchestrator (schedules agent tasks)
6. Implement first agent (Web Scraper) - verify parallel execution works
7. Build progress tracking and real-time updates

Build this progressively and thoroughly. Quality > Speed. Focus on:
- Clean, maintainable code architecture
- Robust error handling
- Real parallel execution (not sequential)
- Clear inter-agent communication patterns
- Type safety and documentation

Create detailed docstrings, error messages, and logging so the next developer 
can understand and extend this easily.

Start now and build comprehensively. Don't skip steps or create placeholder 
implementations. Each component should be production-ready.
```

---

## DETAILED REFERENCE GUIDE (For Context)

### AGENT RESPONSIBILITIES IN DETAIL

#### 1. PROJECT LEAD (Orchestrator Agent)
- **Role**: Central coordinator managing all parallel workflows
- **Responsibilities**:
  - Receives company input (website URL + optional files)
  - Spawns and monitors all specialist agents
  - Manages priority and resource allocation
  - Aggregates findings into coherent recommendations
  - Handles error recovery and retry logic
  - Updates progress indicators for user
- **Communication**: Receives task completions from all agents, feeds findings to Report Agent
- **Skills**: Python orchestration, async task management, error handling

#### 2. WEB SCRAPER AGENT
- **Role**: Comprehensive website analysis and documentation
- **Responsibilities**:
  - Crawl target website (20-30 pages hierarchically)
  - Take Puppeteer/Selenium screenshots of every page
  - Extract metadata, structure, CMS type, technology stack
  - Build sitemap and information architecture analysis
  - Identify conversion funnel pages
  - Extract all CTAs, forms, and conversion mechanics
  - Store screenshots and structured data for Report Agent
- **Skills**: Web scraping, headless browser automation, HTML/CSS analysis, image processing
- **Output**: Scraped content JSON, screenshots folder, technical analysis

#### 3. COMPANY RESEARCH AGENT
- **Role**: Deep company intelligence gathering
- **Responsibilities**:
  - Query multiple data sources (Crunchbase, LinkedIn, news APIs)
  - Analyze company founding story, funding history, leadership team
  - Extract business model information
  - Identify target industries and customer segments
  - Research company growth trajectory and milestones
  - Compile competitive positioning context
- **Skills**: API integration, data aggregation, business analysis
- **Output**: Structured company profile JSON

#### 4. COMPETITOR INTELLIGENCE AGENT
- **Role**: Market landscape and competitive analysis
- **Responsibilities**:
  - Identify 5-10 key competitors based on ICP and positioning
  - Analyze competitor websites and positioning statements
  - Extract competitor pricing/packaging strategies
  - Build competitive feature matrix
  - Identify market gaps and white space
  - Analyze competitor marketing messaging
- **Skills**: Competitor research, web scraping, comparative analysis
- **Output**: Competitor matrix, positioning gap analysis

#### 5. REVIEW & SENTIMENT AGENT
- **Role**: Customer perception and brand sentiment analysis
- **Responsibilities**:
  - Scrape G2, Capterra, Trustpilot reviews
  - Analyze review sentiment (positive/negative themes)
  - Extract common use cases from reviews
  - Identify pain points customers mention
  - Calculate NPS/sentiment scores
  - Extract competitor review analysis for comparison
  - Identify review-based feature gaps
- **Skills**: API access, sentiment analysis, NLP, data extraction
- **Output**: Sentiment analysis report, theme extraction, comparative NPS

#### 6. SEO & VISIBILITY AGENT
- **Role**: Search visibility and organic performance analysis
- **Responsibilities**:
  - Conduct SEO audit (technical SEO, on-page SEO, keywords)
  - Analyze page titles, meta descriptions, header structure
  - Identify keyword ranking opportunities
  - Extract current rankings for target keywords
  - Analyze backlink profile (if API available)
  - Identify content gaps vs. competitors
  - Analyze site speed and Core Web Vitals
  - Build keyword opportunity matrix
- **Skills**: SEO analysis, keyword research, technical SEO
- **Output**: SEO audit report, keyword opportunities, technical recommendations

#### 7. MESSAGING & POSITIONING AGENT
- **Role**: Marketing message and value proposition analysis
- **Responsibilities**:
  - Extract homepage value proposition and messaging hierarchy
  - Analyze headline effectiveness (headline formulas, clarity tests)
  - Extract all key messaging pillars
  - Analyze customer success stories and case studies
  - Evaluate messaging clarity and target audience alignment
  - Identify positioning gaps vs. competitors
  - Analyze proof elements (testimonials, logos, data points)
  - Create messaging audit with recommendations
- **Skills**: Copywriting analysis, marketing psychology, positioning strategy
- **Output**: Messaging audit, positioning matrix, improvement recommendations

#### 8. VISUAL & DESIGN AGENT
- **Role**: Visual design and imagery analysis
- **Responsibilities**:
  - Analyze hero image effectiveness (emotional resonance, clarity)
  - Evaluate color scheme and brand consistency
  - Assess imagery quality and professionalism
  - Identify missing visual elements (product screenshots, team photos)
  - Analyze call-to-action button placement and design
  - Create annotated screenshots highlighting design issues
  - Compare visual design vs. competitors
  - Provide specific design improvement recommendations
- **Skills**: UX/UI analysis, visual design principles, design psychology
- **Output**: Design audit with annotated screenshots, visual recommendations

#### 9. CONVERSION OPTIMIZATION AGENT
- **Role**: Landing page and funnel optimization analysis
- **Responsibilities**:
  - Analyze CRO best practices implementation
  - Identify form field optimization opportunities
  - Evaluate page flow and user journey
  - Assess trust signals and social proof placement
  - Analyze friction points in conversion funnel
  - Benchmark conversion elements vs. industry best practices
  - Identify A/B testing opportunities
  - Create CRO roadmap
- **Skills**: CRO best practices, funnel analysis, user psychology
- **Output**: CRO audit, optimization roadmap, A/B test recommendations

#### 10. SOCIAL & ENGAGEMENT AGENT
- **Role**: Social media presence and activation analysis
- **Responsibilities**:
  - Extract social media presence (LinkedIn, Twitter, etc.)
  - Analyze posting frequency and engagement rates
  - Evaluate content themes and messaging consistency
  - Identify social media gaps vs. competitors
  - Extract follower counts and growth trajectory
  - Analyze community engagement tactics
  - Identify untapped social channels
  - Create social media effectiveness scorecard
- **Skills**: Social media analysis, content strategy, engagement metrics
- **Output**: Social media audit, engagement scorecard, activation recommendations

#### 11. ICP & SEGMENTATION AGENT
- **Role**: Ideal Customer Profile definition and market segmentation
- **Responsibilities**:
  - Extract company size, industry, geography targeting from website
  - Analyze customer testimonials/case studies for common attributes
  - Define buyer personas based on messaging targeting
  - Create ICP framework with firmographic and behavioral data
  - Develop market segmentation strategy
  - Identify primary, secondary, tertiary segments
  - Analyze segment messaging and targeting
  - Create segment-specific messaging recommendations
- **Skills**: Market sizing, segmentation strategy, buyer persona development
- **Output**: ICP definition, segmentation matrix, persona development

#### 12. REPORT GENERATION AGENT
- **Role**: Synthesis and comprehensive report creation
- **Responsibilities**:
  - Receive findings from all 11 specialist agents
  - Synthesize into coherent narrative structure
  - Create executive summary with top 20 action items
  - Design visual report layout with HTML/CSS
  - Embed screenshots and visual evidence
  - Create scoring/grading system for each audit area
  - Generate interactive HTML report
  - Export to Markdown for editing
  - Create downloadable PDF version
  - Track audit metadata (date, company, version)
- **Skills**: Report writing, HTML/CSS, technical documentation
- **Output**: HTML report, Markdown file, PDF export

---

### COMMUNICATION PROTOCOLS BETWEEN AGENTS

**Message Queue & Architecture**
- Use **Redis** as message queue for inter-agent communication
- Implement **async task queues** (Celery or RQ) for parallel execution
- Create standardized JSON message format for all agent-to-agent communication

**Standard Message Format**
```json
{
  "sender": "agent_name",
  "timestamp": "2026-02-10T12:00:00Z",
  "message_type": "task_request|task_completion|error|update",
  "task_id": "unique_id",
  "data": {...},
  "requires_approval": false
}
```

**Execution Workflow**
1. **Input Phase**: User submits company URL → Project Lead validates and stores
2. **Parallel Execution Phase**: Project Lead spawns 11 specialist agents simultaneously
3. **Progress Tracking**: Each agent sends progress updates to Project Lead every 30 seconds
4. **Result Aggregation**: Agents push results to shared results store (PostgreSQL + Redis)
5. **Synthesis Phase**: Report Agent pulls all results and creates comprehensive report
6. **Output Phase**: Report stored in database, shared link generated

**Error Handling & Retry Logic**
- Failed agent tasks automatically retry 3x with exponential backoff
- Project Lead notifies user of partial failures but continues with available data
- Fallback strategies: if API fails, use cached/alternative data sources

---

### SECURITY PROTOCOLS

**Authentication & Authorization**
- Simple password authentication (single password for all users)
- Store password as bcrypt hash in environment variables
- Session management with secure HTTP-only cookies
- Rate limiting: 5 audits per hour per user (prevent abuse)
- Audit logging: Log all user actions with timestamps

**Data Security**
- HTTPS only (enforce SSL/TLS)
- Database encryption at rest (PostgreSQL with pgcrypto)
- API keys for external services stored in secure environment variables
- No sensitive company data retained after audit completion (28-day TTL option)
- GDPR compliant data handling

**API Security**
- Validate all user inputs (URL validation, file scanning)
- Implement CORS restrictions
- Rate limiting on all endpoints
- API key authentication for GitHub integration
- Scraping robots.txt compliance
- User-Agent headers to identify crawler

**Frontend Security**
- Implement CSP (Content Security Policy) headers
- Sanitize all user inputs before rendering
- CSRF token validation on forms
- Secure file upload handling (max 50MB, whitelist formats)

---

### FRONTEND & BACKEND SPECIFICATION

**Frontend (Streamlit)**
- **Authentication Page**: Password entry + submit
- **Input Collection Page**: 
  - Company website URL (URL validation)
  - Optional file uploads (technical docs, marketing materials, pricing pages)
  - Audit type selector (Full/Quick audit)
  - Advanced options (competitor depth, data source selection)
- **Progress Dashboard**:
  - Real-time progress bars for each agent (12 total)
  - Update frequency: every 5 seconds
  - Current task display
  - Estimated time remaining
  - Historical audit list (left sidebar)
- **Report Viewer**:
  - Interactive HTML report embedded in Streamlit
  - Expandable sections for each analysis area
  - Screenshot viewer with annotations
  - Download buttons for HTML/Markdown/PDF
  - Share link generation (with optional password protection)
  - Export formats toggle

**Backend (FastAPI)**
- **Endpoints**:
  - `POST /api/auth/login` - Password validation
  - `POST /api/audits/create` - Submit audit request
  - `GET /api/audits/{audit_id}/status` - Get progress
  - `GET /api/audits/{audit_id}/report` - Retrieve report
  - `POST /api/audits/{audit_id}/export` - Export report
  - `GET /api/audits/history` - List user's audits
  - `DELETE /api/audits/{audit_id}` - Delete audit
  - WebSocket: `/ws/audits/{audit_id}/progress` - Real-time updates
- **Response Format**: Standardized JSON with status codes
- **Database Models**: Audit record, User session, Report storage

---

### DETAILED DATA ANALYSIS AREAS (For Each Agent)

**1. Positioning & Messaging**
- Current positioning statement clarity
- Value proposition effectiveness
- Target audience alignment
- Messaging hierarchy analysis
- Unique selling proposition (USP) clarity
- Brand personality consistency

**2. ICP & Segmentation**
- Identified customer segments
- Firmographic targeting (company size, industry)
- Behavioral targeting (use cases, pain points)
- Geographic targeting
- Segment-specific messaging
- Market sizing and TAM analysis

**3. SEO & Visibility**
- Page speed scores (Lighthouse)
- Mobile optimization
- Core Web Vitals
- Keyword rankings and opportunities
- Title/meta description optimization
- Header structure (H1-H3 hierarchy)
- Internal linking strategy
- Backlink analysis

**4. Conversion Rate Optimization**
- Funnel analysis (traffic → MQL → SQL → Demo → Customer)
- Form field optimization opportunities
- CTA placement and design
- Trust signal implementation
- Social proof effectiveness
- Friction point identification
- Landing page scoring (vs. best practices)

**5. Visual & Design**
- Color palette analysis
- Typography effectiveness
- Imagery quality and emotional resonance
- Layout consistency
- Iconography and visual hierarchy
- Mobile responsiveness assessment
- Design debt identification

**6. Reviews & Sentiment**
- Net sentiment score (positive/negative ratio)
- Common themes in reviews
- Competitive NPS benchmark
- Pain points identified in reviews
- Feature gaps mentioned
- Pricing perception
- Customer service sentiment

**7. Competitor Positioning**
- 5-10 competitors identified
- Messaging comparison matrix
- Pricing/packaging comparison
- Feature parity analysis
- Market positioning gaps
- Messaging differentiation opportunities

**8. Social Media Effectiveness**
- Presence across platforms (LinkedIn, Twitter, etc.)
- Content frequency and engagement
- Audience growth rate
- Audience demographics
- Content themes and performance
- Community engagement score
- Untapped channels

**9. Website Content Quality**
- Content comprehensiveness
- Jargon vs. clarity ratio
- Use case documentation
- Educational content gaps
- Blog quality and freshness
- Resource library assessment

**10. Brand & Perception**
- Brand consistency across touchpoints
- Voice & tone analysis
- Thought leadership indicators
- Press mentions and media presence
- Award/certification display

---

### RECOMMENDATIONS OUTPUT FRAMEWORK

Each recommendation should include:
1. **Area of Focus** (SEO, Messaging, Design, etc.)
2. **Current State** (what's happening now)
3. **Best Practice** (industry standard)
4. **Impact Potential** (Low/Medium/High impact on GTM)
5. **Effort Required** (Low/Medium/High effort)
6. **Specific Actions** (3-5 step implementation plan)
7. **Success Metrics** (how to measure improvement)
8. **Evidence** (screenshot or data showing current state)

---

### REPORT STRUCTURE (HTML/Markdown)

```
📊 B2B GTM AUDIT REPORT
├── Executive Summary (1-2 min read)
│   ├── Overall GTM Health Score (0-100)
│   ├── Top 20 Recommendations (prioritized)
│   └── Quick wins (high impact, low effort)
│
├── 1. Company Profile & Competitive Context (5 min)
│   ├── Company overview (funding, growth, mission)
│   ├── Market position
│   └── Top 5 competitors identified
│
├── 2. Positioning & Messaging Audit (10 min)
│   ├── Current positioning statement
│   ├── Messaging effectiveness score
│   ├── Value proposition clarity
│   ├── Screenshots of key messaging areas
│   └── Improvement recommendations
│
├── 3. ICP & Segmentation Strategy (8 min)
│   ├── Identified customer segments
│   ├── ICP definition
│   ├── Segment-specific messaging gaps
│   └── Expansion opportunities
│
├── 4. Website UX & Visual Design (12 min)
│   ├── Design audit score
│   ├── Annotated screenshots (issues highlighted)
│   ├── Hero image/CTA effectiveness
│   ├── Mobile optimization assessment
│   └── Design recommendations
│
├── 5. SEO & Organic Visibility (10 min)
│   ├── Current SEO score
│   ├── Keyword opportunity analysis
│   ├── Technical SEO issues
│   ├── Page speed analysis
│   └── SEO roadmap (6-month)
│
├── 6. Conversion Optimization (10 min)
│   ├── CRO audit score
│   ├── Funnel analysis
│   ├── Form field optimization
│   ├── Trust signal audit
│   └── A/B testing recommendations
│
├── 7. Competitive Benchmark (8 min)
│   ├── Messaging comparison matrix
│   ├── Feature comparison
│   ├── Pricing comparison
│   └── Market positioning gaps
│
├── 8. Review & Sentiment Analysis (6 min)
│   ├── Overall sentiment score
│   ├── Review themes (+/-)
│   ├── NPS vs. competitors
│   └── Customer pain points
│
├── 9. Social & Content Presence (6 min)
│   ├── Social media audit score
│   ├── Platform effectiveness
│   ├── Content strategy assessment
│   └── Engagement benchmarks
│
└── 10. Prioritized Action Plan (5 min)
    ├── Quick wins (implement in 1-2 weeks)
    ├── Medium-term initiatives (1-3 months)
    ├── Long-term strategy (3-6 months)
    └── Success metrics & tracking
```

---

### QUICK AUDIT vs. FULL AUDIT

**Quick Audit (10-15 minutes)**
- Basic website structure analysis
- Homepage messaging review
- Top 5 competitors identified
- Quick SEO audit (no backlink analysis)
- Basic design assessment
- Simplified report (5-page summary)

**Full Audit (30-45 minutes)**
- 20-30 page comprehensive scrape
- Deep competitor analysis
- Full review scraping and sentiment analysis
- Complete SEO audit with backlinks
- Design audit with 50+ annotated screenshots
- ICP and segmentation development
- Social media deep dive
- Comprehensive 50+ page report

---

### TECHNOLOGY DECISIONS & RATIONALE

| Component | Choice | Why |
|-----------|--------|-----|
| Web Scraping | Selenium/Playwright | Captures JavaScript rendering & screenshots |
| Vector DB | Pinecone | Fast semantic search on large document corpus |
| Report Format | HTML + Markdown | Interactive viewing + easy editing |
| Agent Framework | LLM function calling + async tasks | Parallel execution, cost-effective |
| Frontend | Streamlit | Fast iteration, built-in components |
| Backend | FastAPI | Async, high performance, easy deployment |
| Database | PostgreSQL | Reliable, good for relational audit data |
| Deployment | GitHub + Cloud (GCP/AWS) | Leverages GitHub integration |

---

### IMPLEMENTATION TIMELINE SUGGESTION

- **Week 1**: Project scaffolding, basic Streamlit UI, authentication
- **Week 2**: Web Scraper Agent, Company Research Agent
- **Week 3**: SEO Agent, Messaging Agent, Design Agent
- **Week 4**: CRO Agent, Review Agent, Competitor Agent
- **Week 5**: Social Agent, ICP Agent, Report Generation
- **Week 6**: Integration testing, Report design, deployment
- **Week 7**: Polish, user testing, security audit
- **Week 8**: Launch and optimization
