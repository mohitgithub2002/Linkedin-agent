# LinkedIn Post Generation System

## Overview

The LinkedIn Post Generation System is an automated content creation platform built with LangChain and LangGraph. It uses a multi-agent orchestration approach to generate high-quality LinkedIn posts through a series of specialized agents working together in a defined workflow.

## System Architecture

The system is built with:

- **LangChain** - For building chains of LLM operations
- **LangGraph** - For orchestrating the agent workflow
- **Google Gemini** - As the underlying LLM model
- **FastAPI** - For exposing the system as a REST API
- **Pydantic** - For data validation and structured outputs

## Component Structure

The system consists of:

1. **API Layer** (`main.py`) - FastAPI interface for client interactions
2. **Orchestrator** (`orchestrator.py`) - Manages the workflow and agent coordination
3. **Specialized Agents** (`agents/`) - Independent components handling specific tasks:
   - **Topic Selector** - Selects or refines post topics
   - **Research Agent** - Gathers supporting information
   - **Hook Generator** - Creates attention-grabbing openings
   - **Body Generator** - Composes the main content
   - **CTA Generator** - Creates compelling calls-to-action
   - **QA Agent** - Performs quality checks
   - **Final Assembler** - Combines all parts into a cohesive post

## Workflow Process

The system follows a linear workflow:

1. User requests a post (with optional topic)
2. Workflow initializes with state tracking
3. Topic Selector creates or refines the post topic
4. Research Agent gathers relevant information
5. Hook, Body, and CTA are generated sequentially
6. QA Agent performs quality assessment
7. Final Assembler combines all components
8. Complete post is returned to the client

## Documentation Contents

This documentation covers:

- [System Overview](README.md)
- [API Documentation](src/main.md)
- [Orchestrator Documentation](src/orchestrator.md)
- Agents Documentation:
  - [Base Agent](src/agents/base.md)
  - [Topic Selector Agent](src/agents/topic_selector.md)
  - [Research Agent](src/agents/research_agent.md)
  - [Hook Generator Agent](src/agents/hook_generator.md)
  - [Body Generator Agent](src/agents/body_generator.md)
  - [CTA Generator Agent](src/agents/cta_generator.md)
  - [QA Agent](src/agents/qa_agent.md)
  - [Final Assembler Agent](src/agents/final_assembler.md)
- [System Flow Diagrams](flow-diagrams.md)

## Dependencies

- Python 3.9+
- LangChain
- LangGraph
- Google Generative AI API
- FastAPI
- Pydantic
- Uvicorn (for serving)
- BeautifulSoup4 (for web scraping in research)
- Requests
- Python-dotenv

## Environment Variables

The following environment variables are required:

- `GOOGLE_API_KEY` - Google AI API key
- `LANGSMITH_API_KEY` (optional) - For LangSmith tracing
- `LANGCHAIN_API_KEY` (optional) - For LangChain API 