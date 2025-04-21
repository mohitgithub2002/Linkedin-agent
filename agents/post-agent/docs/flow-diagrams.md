# LinkedIn Post Generation System Flow Diagrams

This document contains detailed flow diagrams that visualize the LinkedIn post generation system's architecture, process flow, and component interactions.

## Main System Flow

The following diagram shows the overall system architecture and workflow:

```mermaid
flowchart TD
    %% Main Flow
    Start([User Request]) --> API[FastAPI Endpoint]
    API -->|POST /generate-post| Orchestrator[Orchestrator]
    Orchestrator -->|Initialize Workflow| StateGraph[LangGraph StateGraph]
    StateGraph -->|Set Entry Point| TopicSelector
    
    %% Agent Workflow
    TopicSelector[Topic Selector Agent] -->|Update State| Research[Research Agent]
    Research -->|Update State| Hook[Hook Generator Agent]
    Hook -->|Update State| Body[Body Generator Agent]
    Body -->|Update State| CTA[CTA Generator Agent]
    CTA -->|Update State| QA[QA Agent]
    QA -->|Update State| Assembler[Final Assembler Agent]
    Assembler -->|Complete Post| End([Return Response])
    
    %% Topic Selector Details
    TopicSelector -->|If topic provided| TopicBrief[Create Brief]
    TopicSelector -->|If no topic| TopicSelection[Select New Topic]
    TopicBrief --> TopicState[Update State]
    TopicSelection --> TopicState
    
    %% Research Agent Details
    Research -->|Query Topic| ResearchProcess[Gather Information]
    ResearchProcess -->|Store Findings| ResearchState[Update Research Data]
    
    %% Hook Generator Details
    Hook -->|Process Topic| HookProcess[Generate Hook]
    HookProcess -->|Store Hook| HookState[Update Hook Text]
    
    %% Body Generator Details
    Body -->|Process Topic & Research| BodyProcess[Generate Body]
    BodyProcess -->|Store Body| BodyState[Update Body Text]
    
    %% CTA Generator Details
    CTA -->|Process Topic & Body| CTAProcess[Generate CTA]
    CTAProcess -->|Store CTA| CTAState[Update CTA Text]
    
    %% QA Agent Details
    QA -->|Review Content| QAProcess[Quality Review]
    QAProcess -->|Store Feedback| QAState[Update QA Feedback]
    
    %% Final Assembler Details
    Assembler -->|Combine All Parts| AssemblerProcess[Assemble Post]
    AssemblerProcess -->|Create Payload| PostPayload[Update Post Payload]

    %% State Flow
    subgraph "State Flow: AgentState"
        AgentState1[Initial State] -->|Topic Selection| AgentState2[Topic & Brief]
        AgentState2 -->|Research| AgentState3[+ Research Data]
        AgentState3 -->|Hook Generation| AgentState4[+ Hook Text]
        AgentState4 -->|Body Generation| AgentState5[+ Body Text]
        AgentState5 -->|CTA Generation| AgentState6[+ CTA Text]
        AgentState6 -->|QA Review| AgentState7[+ QA Feedback]
        AgentState7 -->|Final Assembly| AgentState8[+ Post Payload]
    end
    
    %% Error Handling
    TopicSelector -->|No Topic Error| TopicError[Raise ValueError]
    Research -->|No Topic Error| ResearchError[Raise ValueError]
    Hook -->|No Topic Error| HookError[Raise ValueError]
    Body -->|No Topic/Hook Error| BodyError[Raise ValueError]
    CTA -->|No Topic/Body Error| CTAError[Raise ValueError]
    QA -->|Missing Content Error| QAError[Raise ValueError]
    Assembler -->|Missing Content Error| AssemblerError[Raise ValueError]
    
    %% Technical Components
    subgraph "Technical Framework"
        LangChain[LangChain]
        LangGraph[LangGraph]
        Gemini[Google Gemini LLM]
        FastAPI[FastAPI]
        Pydantic[Pydantic Models]
    end
    
    %% Agent Methods
    subgraph "Agent Common Methods"
        Init[__init__]
        SetLLM[set_llm]
        CreatePrompt[create_prompt] 
        Run[run]
        GetGraph[get_graph]
    end
    
    %% LLM Configuration
    subgraph "LLM Configuration"
        GeminiModel[gemini-2.0-flash]
        Temperature[temperature=0.7]
        TopP[top_p=0.8]
        TopK[top_k=40]
    end
    
    %% Styling
    classDef agent fill:#f9f,stroke:#333,stroke-width:2px
    classDef state fill:#bbf,stroke:#333,stroke-width:1px
    classDef error fill:#f55,stroke:#333,stroke-width:1px
    classDef endpoint fill:#5f5,stroke:#333,stroke-width:2px
    
    class TopicSelector,Research,Hook,Body,CTA,QA,Assembler agent
    class AgentState1,AgentState2,AgentState3,AgentState4,AgentState5,AgentState6,AgentState7,AgentState8 state
    class TopicError,ResearchError,HookError,BodyError,CTAError,QAError,AssemblerError error
    class API,End endpoint
```

## Detailed Agent Flows

The following diagrams show the internal logic flow of each agent:

### 1. Topic Selector Agent

```mermaid
flowchart LR
    Start([Input: AgentState]) --> Check{Topic Provided?}
    Check -->|Yes| CreatePrompt1[Create Prompt with Topic]
    Check -->|No| CreatePrompt2[Create Prompt for Selection]
    CreatePrompt1 --> InvokeLLM1[Invoke LLM]
    CreatePrompt2 --> InvokeLLM2[Invoke LLM]
    InvokeLLM1 --> Parse1[Parse Topic Brief]
    InvokeLLM2 --> Parse2[Parse Topic Selection]
    Parse1 --> UpdateState1[Update State]
    Parse2 --> UpdateState2[Update State]
    UpdateState1 --> End([Return: Updated AgentState])
    UpdateState2 --> End
```

### 2. Research Agent

```mermaid
flowchart LR
    Start([Input: AgentState]) --> Check{Topic Available?}
    Check -->|No| Error[Raise ValueError]
    Check -->|Yes| CreatePrompt[Create Research Prompt]
    CreatePrompt --> InvokeLLM[Invoke LLM]
    InvokeLLM --> Parse[Parse Research Results]
    Parse --> UpdateState[Add Research Items to State]
    UpdateState --> End([Return: Updated AgentState])
```

### 3. Hook Generator Agent

```mermaid
flowchart LR
    Start([Input: AgentState]) --> Check{Topic Available?}
    Check -->|No| Error[Raise ValueError]
    Check -->|Yes| CreatePrompt[Create Hook Prompt]
    CreatePrompt --> InvokeLLM[Invoke LLM]
    InvokeLLM --> Parse[Parse Hook Result]
    Parse --> UpdateState[Update State with Hook]
    UpdateState --> End([Return: Updated AgentState])
```

### 4. Body Generator Agent

```mermaid
flowchart LR
    Start([Input: AgentState]) --> CheckTopic{Topic Available?}
    CheckTopic -->|No| Error1[Raise ValueError]
    CheckTopic -->|Yes| CheckHook{Hook Available?}
    CheckHook -->|No| Error2[Raise ValueError]
    CheckHook -->|Yes| CreatePrompt[Create Body Prompt]
    CreatePrompt --> ProcessResearch[Process Research Data]
    ProcessResearch --> InvokeLLM[Invoke LLM]
    InvokeLLM --> Parse[Parse Body Result]
    Parse --> UpdateState[Update State with Body]
    UpdateState --> End([Return: Updated AgentState])
```

### 5. CTA Generator Agent

```mermaid
flowchart LR
    Start([Input: AgentState]) --> CheckTopic{Topic Available?}
    CheckTopic -->|No| Error1[Raise ValueError]
    CheckTopic -->|Yes| CheckBody{Body Available?}
    CheckBody -->|No| Error2[Raise ValueError]
    CheckBody -->|Yes| CreatePrompt[Create CTA Prompt]
    CreatePrompt --> InvokeLLM[Invoke LLM]
    InvokeLLM --> Parse[Parse CTA Result]
    Parse --> UpdateState[Update State with CTA]
    UpdateState --> End([Return: Updated AgentState])
```

### 6. QA Agent

```mermaid
flowchart LR
    Start([Input: AgentState]) --> CheckContent{All Content Available?}
    CheckContent -->|No| Error[Raise ValueError]
    CheckContent -->|Yes| CreatePrompt[Create QA Prompt]
    CreatePrompt --> InvokeLLM[Invoke LLM]
    InvokeLLM --> Parse[Parse QA Result]
    Parse --> UpdateState[Update State with QA Feedback]
    UpdateState --> End([Return: Updated AgentState])
```

### 7. Final Assembler Agent

```mermaid
flowchart LR
    Start([Input: AgentState]) --> CheckContent{All Content Available?}
    CheckContent -->|No| Error[Raise ValueError]
    CheckContent -->|Yes| CreatePrompt[Create Assembler Prompt]
    CreatePrompt --> InvokeLLM[Invoke LLM]
    InvokeLLM --> Parse[Parse Post Payload]
    Parse --> UpdateState[Update State with Final Post]
    UpdateState --> End([Return: Updated AgentState])
```

## Data Flow Diagram

This diagram visualizes how data flows through the system:

```mermaid
graph TD
    subgraph "Input"
        UserRequest[User Request] -->|Topic| API[FastAPI Endpoint]
    end
    
    subgraph "Processing Pipeline"
        API --> StateInit[Initialize AgentState]
        StateInit --> TopicProcess[Topic Selection Process]
        TopicProcess -->|"current_topic & brief"| ResearchProcess[Research Process]
        ResearchProcess -->|"research_data"| HookProcess[Hook Generation Process]  
        HookProcess -->|"hook_text"| BodyProcess[Body Generation Process]
        BodyProcess -->|"body_text"| CTAProcess[CTA Generation Process]
        CTAProcess -->|"cta_text"| QAProcess[QA Review Process]
        QAProcess -->|"qa_feedback, qa_score"| AssemblyProcess[Post Assembly Process]
    end
    
    subgraph "Output"
        AssemblyProcess -->|"post_payload"| Response[API Response]
        Response -->|JSON| Client[Client]
    end
    
    subgraph "Data Models"
        AgentState[AgentState]
        TopicBrief[TopicBrief]
        ResearchResult[ResearchResult]
        HookResult[HookResult]
        BodyResult[BodyResult]
        CTAResult[CTAResult]
        QAResult[QAResult]
        PostPayload[PostPayload]
    end
    
    TopicProcess -.-> TopicBrief
    ResearchProcess -.-> ResearchResult
    HookProcess -.-> HookResult
    BodyProcess -.-> BodyResult
    CTAProcess -.-> CTAResult
    QAProcess -.-> QAResult
    AssemblyProcess -.-> PostPayload
```

## State Transition Diagram

The following diagram shows how the `AgentState` evolves through the workflow:

```mermaid
stateDiagram-v2
    [*] --> InitialState
    
    InitialState --> TopicSelected: Topic Selection
    TopicSelected --> ResearchCollected: Research Collection
    ResearchCollected --> HookGenerated: Hook Generation
    HookGenerated --> BodyGenerated: Body Generation
    BodyGenerated --> CTAGenerated: CTA Generation
    CTAGenerated --> QAReviewed: QA Review
    QAReviewed --> PostAssembled: Final Assembly
    
    PostAssembled --> [*]: Return Response
    
    InitialState: Empty AgentState
    TopicSelected: AgentState with current_topic
    ResearchCollected: + research_data
    HookGenerated: + hook_text
    BodyGenerated: + body_text 
    CTAGenerated: + cta_text
    QAReviewed: + qa_feedback, qa_score
    PostAssembled: + post_payload
``` 