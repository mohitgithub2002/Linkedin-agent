# LinkedIn Post Generation System

A multi-agent system for generating professional LinkedIn posts using LangChain and LangGraph.

## Overview

This system uses a multi-agent architecture to generate high-quality LinkedIn posts. Each agent specializes in a specific aspect of content creation:

1. Topic Selector: Chooses relevant and engaging topics
2. Research Agent: Gathers supporting information and facts
3. Hook Generator: Creates attention-grabbing opening lines
4. Body Generator: Develops the main content
5. CTA Generator: Produces effective call-to-action statements
6. QA Agent: Verifies content quality and provides feedback
7. Final Assembler: Combines all components into a final post

## Features

- Multi-agent architecture using LangGraph
- Quality assurance and feedback loops
- Research-backed content generation
- Professional tone and style maintenance
- LinkedIn best practices compliance
- REST API interface

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd linkedin-post-agent
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the FastAPI server:
```bash
python -m src.main
```

2. Generate a post using the API:
```bash
curl -X POST "http://localhost:8000/generate-post" \
     -H "Content-Type: application/json" \
     -d '{"topic": "optional_topic", "custom_prompt": "optional_prompt"}'
```

## API Endpoints

### POST /generate-post

Generate a new LinkedIn post.

Request body:
```json
{
    "topic": "optional_topic",
    "custom_prompt": "optional_prompt"
}
```

Response:
```json
{
    "text": "Generated post content",
    "image_url": "optional_image_url",
    "status": "success"
}
```

## Architecture

The system uses LangGraph to create a directed acyclic graph (DAG) of agents:

1. Topic Selection → Research
2. Research → Hook Generation
3. Hook Generation → Body Generation
4. Body Generation → CTA Generation
5. CTA Generation → QA Check
6. QA Check → Final Assembly (if passed) or Hook Generation (if failed)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License 