# LinkedIn Post Generation System Flow Diagram

## System Flow (Text-Based Representation)

```
User Request
    │
    ▼
┌─────────────────┐
│    FastAPI      │  POST /generate-post
│    Endpoint     │  (with optional topic)
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   Orchestrator  │  Initialize workflow and AgentState
└─────────────────┘
    │
    ▼
┌─────────────────┐        ┌─────────────────────────┐
│ Topic Selector  │───────▶│ AgentState + Topic/Brief│
└─────────────────┘        └─────────────────────────┘
    │
    ▼
┌─────────────────┐        ┌─────────────────────────┐
│ Research Agent  │───────▶│ AgentState + Research   │
└─────────────────┘        └─────────────────────────┘
    │
    ▼
┌─────────────────┐        ┌─────────────────────────┐
│ Hook Generator  │───────▶│ AgentState + Hook       │
└─────────────────┘        └─────────────────────────┘
    │
    ▼
┌─────────────────┐        ┌─────────────────────────┐
│ Body Generator  │───────▶│ AgentState + Body       │
└─────────────────┘        └─────────────────────────┘
    │
    ▼
┌─────────────────┐        ┌─────────────────────────┐
│ CTA Generator   │───────▶│ AgentState + CTA        │
└─────────────────┘        └─────────────────────────┘
    │
    ▼
┌─────────────────┐        ┌─────────────────────────┐
│   QA Agent      │───────▶│ AgentState + QA Data    │
└─────────────────┘        └─────────────────────────┘
    │
    ▼
┌─────────────────┐        ┌─────────────────────────┐
│ Final Assembler │───────▶│ AgentState + Post       │
└─────────────────┘        └─────────────────────────┘
    │
    ▼
┌─────────────────┐
│  API Response   │  Return complete post
└─────────────────┘
```

## Data Flow Through Agents

```
┌───────────────────────────────────────────────────────────┐
│                       AgentState                           │
├───────────────┬───────────────────────────────────────────┤
│ Field         │ Updated By                                │
├───────────────┼───────────────────────────────────────────┤
│ current_topic │ Topic Selector                            │
│ research_data │ Research Agent                            │
│ hook_text     │ Hook Generator                            │
│ body_text     │ Body Generator                            │
│ cta_text      │ CTA Generator                             │
│ qa_feedback   │ QA Agent                                  │
│ qa_score      │ QA Agent                                  │
│ qa_suggestions│ QA Agent                                  │
│ qa_issues     │ QA Agent                                  │
│ post_payload  │ Final Assembler                           │
└───────────────┴───────────────────────────────────────────┘
```

## Agent Functional Overview

```
Topic Selector
  │
  ├─▶ If topic provided: Create detailed brief
  │
  └─▶ If no topic: Select topic and create brief

Research Agent
  │
  └─▶ Gather facts/statistics/information on topic

Hook Generator
  │
  └─▶ Create attention-grabbing opening for post

Body Generator
  │
  └─▶ Generate main content using research and hook

CTA Generator
  │
  └─▶ Create call-to-action to drive engagement

QA Agent
  │
  └─▶ Review post for quality and provide feedback

Final Assembler
  │
  └─▶ Combine all components into cohesive post
```

## Common Agent Structure

```
┌───────────────────────────┐
│      BaseAgent            │
├───────────────────────────┤
│ - name                    │
│ - llm (Google Gemini)     │
│ - tools (optional)        │
├───────────────────────────┤
│ + set_llm()               │
│ + create_prompt()         │
│ + run() [abstract]        │
│ + get_graph() [abstract]  │
└───────────────────────────┘
           ▲
           │
           │ inherits
           │
┌───────────────────────────┐
│    Specialized Agent      │
├───────────────────────────┤
│ - parser                  │
├───────────────────────────┤
│ + create_prompt()         │
│ + run(state)              │
│ + get_graph()             │
└───────────────────────────┘
```

## Error Handling Pathways

```
User Request
    │
    ▼
API Endpoint
    │
    ├───────── Invalid Request Format ───────▶ 400 Bad Request
    │
    ▼
Topic Selector
    │
    ▼
Research Agent
    │
    ├───────── No Topic ───────────────────▶ ValueError
    │
    ▼
Hook Generator
    │
    ├───────── No Topic ───────────────────▶ ValueError
    │
    ▼
Body Generator
    │
    ├───────── No Topic/Hook ──────────────▶ ValueError
    │
    ▼
CTA Generator
    │
    ├───────── No Topic/Body ──────────────▶ ValueError
    │
    ▼
QA Agent
    │
    ├───────── Missing Content ─────────────▶ ValueError
    │
    ▼
Final Assembler
    │
    ├───────── Missing Components ───────────▶ ValueError
    │
    ▼
Response
```

## Technical Components

```
┌───────────────────────────────────────────────────────────┐
│                  Technical Framework                       │
├───────────────┬───────────────────────────────────────────┤
│ Component     │ Role                                      │
├───────────────┼───────────────────────────────────────────┤
│ LangChain     │ Building LLM operation chains             │
│ LangGraph     │ Orchestrating agent workflow              │
│ Google Gemini │ LLM for content generation                │
│ FastAPI       │ REST API interface                        │
│ Pydantic      │ Data validation and schemas               │
│ BeautifulSoup │ Web scraping for research                 │
└───────────────┴───────────────────────────────────────────┘
``` 