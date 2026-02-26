# Menon & Menon Foundry Management System - User Guide

## What Is This System?

The Menon & Menon Foundry Management System is an intelligent platform designed to help foundry operators and managers make data-driven decisions quickly. It combines an AI chatbot, data analytics, and production management tools in one unified interface.

**In Simple Terms:** Ask questions about your production in natural language, and the system instantly provides answers, market insights, and operational data.

---

## Key Features

### 1. **AI Chatbot Assistant** (Primary Interface)
Talk to your production assistant in plain English. No special commands or technical knowledge required.

**What You Can Ask:**
- **Market Prices:** "What is the copper price today?" → Get real-time metal prices
- **Industry News:** "Latest steel foundry news?" → Stay updated with relevant news
- **Production Data:** "What is the average tap temperature?" → Analytics on your operations
- **Standard Procedures:** "How do I line a furnace?" → Access to safety and operational procedures
- **Production Insights:** "Show me recent yield data" → Detailed production records

**Response Time:** Answers within 2-4 seconds

### 2. **Real-Time Market Data**
Never miss market movements affecting your business.

**Metals Tracked:**
- Copper, Aluminum, Nickel, Zinc, Lead, Tin
- Iron ore, Pig iron, Scrap steel
- Steel & related stocks

**Update Frequency:** Live prices (refreshed with each query)

**Use Case:** Check material costs before placing orders

### 3. **Curated Industry News**
Stay informed about trends and developments in the foundry sector.

**Coverage:**
- Steel industry developments
- Scrap metal market updates
- Casting and metallurgy news
- Global foundry trends

**News Sources:** GNews API (verified sources)

**Use Case:** Understand market conditions and competitive landscape

### 4. **Production Analytics Dashboard**
Visualize and understand your factory performance at a glance.

**Metrics Tracked:**
- **Quality:** Yield percentages, defect counts, rejection rates
- **Efficiency:** Average tap temperatures, processing times, energy usage
- **Capacity:** Production order status, inventory levels, pending orders
- **Maintenance:** Equipment downtime, maintenance costs, asset availability

**Tabs:**
- **Overview:** KPI dashboard
- **Chat:** AI assistant interface
- **Analytics:** Charts and visualizations
- **Reports:** Pre-built report templates

### 5. **Production Data Access**
Query your production database using simple language.

**Information You Can Access:**
- Material specifications and pricing
- Bill of materials (component lists)
- Production order status and history
- Melting/furnace operation records
- Quality inspection results
- Maintenance schedules and costs
- Inventory and stock movements
- Machining and heat treatment logs

**Example Questions:**
- "Average yield by product type?" → Breakdown by your products
- "Total scrap castings this month?" → Aggregated waste metrics
- "How many rejected heats?" → Quality control insights
- "Inventory levels?" → Current stock status

### 6. **Standard Operating Procedures (SOPs)**
Access company procedures and best practices when you need them.

**Included:**
- Furnace lining procedures
- Pouring and casting safety
- Heat treatment guidelines
- Molding specifications
- Quality inspection checklists
- Equipment maintenance protocols

**Search Method:** Ask in natural language; system finds relevant procedures

### 7. **Data Integration**
Your production data is automatically ingested from source systems.

**How It Works:**
- Data feeds from CSV/ERP sources
- Automatic validation and schema checking
- Real-time synchronization
- Historical data retention

---

## How to Use the System

### Before You Start
1. **System must be running:** Your IT team starts the dashboard
2. **Database populated:** Production data loaded from feeders
3. **API keys configured:** Market data and news sources connected

### Using the Chatbot (Main Interface)

**Step 1:** Open the system dashboard (Streamlit interface)

**Step 2:** Click the **Chat** tab

**Step 3:** Type your question naturally:
```
"What is the current copper price?"
"Show me recent yield trends"
"How many castings rejected today?"
"Tell me about furnace procedures"
```

**Step 4:** System responds with:
- Direct answer
- Source of data (live market, database, knowledge base)
- Formatted data (tables, numbers, charts)

### Example Workflows

**Workflow 1: Morning Production Check**
```
Q: "What is the average tap temperature from yesterday?"
A: "Average tap temperature: 1425.3°C (based on 12 heats)"

Q: "How many rejected castings?"
A: "Total rejected: 45 castings (from 340 total = 13.2% rejection rate)"

Q: "Current inventory levels?"
A: [Shows last 5 inventory movements with stock status]
```

**Workflow 2: Market Decision**
```
Q: "Copper and aluminum prices today?"
A: "Copper: $9.42/lb | Aluminum: $2.28/lb (updated 2 minutes ago)"

Q: "Latest news on scrap steel?"
A: [Shows 3-5 recent news articles with links]
```

**Workflow 3: Quality Investigation**
```
Q: "Show defect data from this week"
A: [Table of inspections with defect types and counts]

Q: "How many overall rejections by decision?"
A: [Breakdown: ACCEPT: 45, REWORK: 12, SCRAP: 8]

Q: "Furnace lining procedure?"
A: [Detailed SOP with safety guidelines and steps]
```

---

## System Components (User Perspective)

| Component | What It Does | When You Use It |
|-----------|------------|-----------------|
| **AI Chatbot** | Interprets your questions and finds answers | Every query |
| **Market Data Feed** | Provides real-time commodity prices | Price decisions, cost planning |
| **News Service** | Curates industry news and trends | Strategic planning |
| **Production Database** | Stores and retrieves all operational data | Analytics, reporting |
| **Knowledge Base** | Stores procedures and best practices | Training, compliance |
| **Dashboard UI** | Visual interface for queries and reports | Daily operations |

---

## What Data Is Available?

### Production Records
- Melting operations (temperatures, yields, energy usage)
- Casting results (good units, scrap, quality grades)
- Quality inspections (defects, acceptance decisions)
- Machining operations (machine type, efficiency)
- Heat treatments (temperature control, status)

### Inventory & Materials
- Material specifications (types, descriptions, pricing)
- Component lists (bill of materials)
- Stock levels (current inventory, movements)
- Price tracking (standard costs, market updates)

### Orders & Planning
- Production orders (status, quantities, deadlines)
- Order history (fulfillment rates, timelines)
- Scheduled vs. actual (variance analysis)

### Equipment & Maintenance
- All equipment tracked (furnaces, machines, tools)
- Maintenance history (costs, downtime, schedules)
- Performance metrics (power consumption, efficiency)

---

## Key Capabilities

✅ **Real-Time:** Live commodity prices and current inventory  
✅ **Intelligent:** Natural language understanding (no special syntax required)  
✅ **Fast:** Responses in 2-4 seconds typically  
✅ **Safe:** Read-only database access (no data can be accidentally deleted)  
✅ **Contextual:** Remembers previous questions in conversation  
✅ **Comprehensive:** Covers market, production, quality, and operations data  
✅ **User-Friendly:** No technical skills required  

---

## Typical Use Cases

### 1. **Production Manager** (Daily Operations)
*"Show me current production order status"* → View workflow and bottlenecks  
*"Average yield percentage?"* → Quality trends  
*"Any equipment maintenance due?"* → Asset planning

### 2. **Quality Inspector** (Quality Control)
*"Defects reported this week?"* → Quality trends  
*"Rejection rate by product?"* → Which products need attention  
*"Inspection guidelines for casting"* → Access procedures

### 3. **Cost Accountant** (Financial Planning)
*"Copper and aluminum prices?"* → Material cost forecasting  
*"Total maintenance costs last month?"* → Budget tracking  
*"Material price history?"* → Cost curve analysis

### 4. **Procurement Officer** (Supply Chain)
*"Scrap steel market news?"* → Supplier negotiations  
*"Steel prices today?"* → Purchase timing  
*"High-value inventory items?"* → Inventory optimization

### 5. **Facility Manager** (Asset Management)
*"Equipment maintenance status?"* → Scheduling maintenance  
*"Equipment downtime trends?"* → Reliability analysis  
*"Maintenance procedure for furnace?"* → Training reference

---

## Limitations & Considerations

⚠️ **Rate Limits:** News API has 100 requests/day standard tier  
⚠️ **Data Freshness:** Market prices typically 5-15 minutes delayed  
⚠️ **Database Latency:** Complex queries may take 5-10 seconds  
⚠️ **User Capacity:** Best for 10-20 simultaneous users  
⚠️ **Read-Only:** Cannot directly modify production data via chatbot (use ERP/forms)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No data found" for production queries | Contact IT; database may need data refresh |
| System slow to respond | Check internet connection; Groq API may be busy |
| Market prices show "Reference:" label | prices are from YFinance fallback (still accurate) |
| News missing | Daily limit reached; try again tomorrow |
| Can't find SOP procedures | Procedure may not be in system; contact training team |

---

## Quick Reference: What the System Knows

**About Your Factory:**
- What you produce (materials, alloys, products)
- How you produce it (processes, equipment, procedures)
- How well you produce it (yields, defects, quality grades)
- What you use (materials, inventory, components)
- Equipment status (maintenance, downtime, costs)
- Orders (status, deadlines, quantities)

**About the Market:**
- Current metal/commodity prices
- Industry trends and news
- Competitor activity (from news feeds)

**About Best Practices:**
- Your internal procedures (SOPs, safety guidelines)
- Equipment operation manuals
- Quality standards and specifications

---

## Getting Started Checklist

- [ ] System is running (IT team confirms)
- [ ] You can access the dashboard
- [ ] Try a simple query: "What is the copper price?"
- [ ] Ask a production question: "Show me recent yield data"
- [ ] Explore an SOP: "Furnace lining procedure?"
- [ ] Check market news: "Steel industry news?"

---

## Support & Questions

For technical issues or feature requests:
- **System Admin:** Database connectivity, data loading issues
- **Data Team:** Schema questions, new data sources
- **Production:** How to interpret results, available metrics
- **Training:** Using the chatbot effectively, best practices

---

**System Status:** Active & Ready  
**Last Updated:** February 26, 2026  
**Version:** 1.0
