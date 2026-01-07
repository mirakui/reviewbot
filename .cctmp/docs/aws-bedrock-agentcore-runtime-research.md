# AWS Bedrock AgentCore Runtime Research

## Executive Summary

Amazon Bedrock AgentCore Runtime is a serverless, managed platform for deploying and operating AI agents at scale. It provides complete session isolation via dedicated microVMs, supports any AI framework and model provider, and uses a pay-per-use pricing model that charges only for active resource consumption.

---

## 1. How AgentCore Runtime Works with Strands SDK

### Integration Overview

Strands Agents SDK integrates with AgentCore Runtime through a simple SDK import:

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp
```

### Key Integration Features

- **Framework Agnostic**: Strands Agents works seamlessly alongside LangGraph, CrewAI, LlamaIndex, Google ADK, and OpenAI Agents SDK
- **Unified SDK**: AgentCore SDK provides streamlined access to complete AgentCore capabilities including Memory, Tools, and Gateway
- **Portable Code**: Agents built with Strands SDK are portable Python apps that can run across different compute options (AgentCore Runtime, Lambda, ECS)

### Deployment Flow

1. Define agent logic using Strands Agents framework
2. Add required HTTP endpoints using AgentCore SDK
3. Package dependencies in `requirements.txt`
4. Build and push container image to Amazon ECR (or use direct code deployment)
5. Create AgentCore Runtime with container image
6. Invoke agent via `InvokeAgentRuntime` or `InvokeAgentRuntimeWithWebSocketStream`

---

## 2. Deployment Patterns for Lambda Integration

### Option 1: Direct AgentCore Runtime Deployment (Recommended)

- **Best for**: Package size under 250MB, Python 3.10-3.13, rapid prototyping
- **Process**: AgentCore automatically packages code into Docker image, pushes to ECR, deploys to serverless runtime
- **Session Duration**: Up to 8 hours (longest in industry for async workloads)

### Option 2: Container-Based Deployment

- **Best for**: Teams with existing container build/deploy pipelines
- **Process**: Code packaged as arm64 container, pushed to ECR, hosted by AgentCore Runtime
- **Features**: Supports controlled deployment, rollback capabilities via version management

### Option 3: Lambda + API Gateway Pattern

- **Architecture**: Lambda for serverless compute, API Gateway as frontend
- **Integration**: Lambda Web Adapter (LWA) proxies event payload to underlying agent endpoint as HTTP request
- **Use Case**: When existing Lambda infrastructure needs agent capabilities

### Gateway Integration with Lambda Functions

AgentCore Gateway automatically converts:
- Existing APIs
- Lambda functions
- Other services

Into MCP-compatible tools for agent consumption without managing integrations.

### Infrastructure as Code Options

- AWS CloudFormation
- AWS CDK
- Terraform

Production-ready templates available for basic runtimes, MCP servers, multi-agent systems.

---

## 3. Authentication and IAM Requirements

### Inbound Authentication (Who Can Access Agents)

Powered by **AgentCore Identity**:

| Method | Description |
|--------|-------------|
| **AWS IAM (SigV4)** | Uses AWS credentials for verification |
| **OAuth 2.0** | Integrates with external identity providers |

**OAuth Configuration Required**:
- Discovery URL (OpenID Connect discovery endpoint)
- Allowed Audiences (valid audience values for tokens)
- Allowed Clients (client identifiers with access)

**Supported Identity Providers**:
- Amazon Cognito
- Microsoft Entra ID (Azure AD)
- Okta

### Outbound Authentication (Agent Access to External Services)

**Authentication Methods**:
- OAuth for OAuth-supporting services
- API Keys for key-based authentication

**Authentication Modes**:
| Mode | Description |
|------|-------------|
| **User-delegated** | Agent acts on behalf of end user with their credentials |
| **Autonomous** | Agent acts independently with service-level credentials |

**Supported External Services**:
- Slack, Zoom, GitHub
- Salesforce, Stripe
- AWS services
- Custom APIs and data sources

### Security Features

- **Session Isolation**: Dedicated microVM per session
- **Memory Sanitization**: MicroVM destroyed and memory sanitized after session termination
- **Credential Management**: Secure handling without exposure in agent code/logs
- **VPC Connectivity**: Available across all AgentCore services
- **PrivateLink Support**: For additional network security

**Note**: AgentCore Identity usage through Runtime or Gateway incurs no additional charges.

---

## 4. Pricing Model (Pay-Per-Use)

### Core Pricing Philosophy

- **No upfront commitments or minimum fees**
- **Consumption-based**: Pay only for active resource consumption
- **I/O Wait is Free**: If no CPU consumed during I/O wait, no charges (significant savings for agents that spend 30-70% of time waiting for LLM responses, API calls)

### Runtime Pricing Structure

| Resource | Billing Model |
|----------|---------------|
| **CPU** | Per-second, actual consumption only |
| **Memory** | Per-second, peak memory consumed (128MB minimum) |
| **Minimum billing period** | 1 second |

### Coverage

Pricing covers entire session lifecycle:
- MicroVM boot
- Initialization
- Active processing
- Idle periods
- Shutdown

### Additional Charges

| Service | Pricing |
|---------|---------|
| **Gateway** | $0.005 per 1,000 tool API invocations |
| **Memory (Short-term)** | $0.25 per 1,000 memory events |
| **Storage (Direct Code)** | S3 Standard rates (starting Feb 27, 2026) |
| **Storage (Container)** | Separate ECR storage costs |
| **Network** | Standard EC2 data transfer rates |

### Cost Optimization Benefits

Traditional compute charges for pre-allocated resources (fixed instance size). AgentCore charges only for active processing, delivering substantial savings for typical agentic workloads with high I/O wait times.

---

## 5. Supported Models and Configuration

### Model Support (Model-Agnostic)

AgentCore works with any foundation model inside or outside Amazon Bedrock:

| Provider | Models |
|----------|--------|
| **Amazon** | Nova |
| **Anthropic** | Claude (all versions) |
| **OpenAI** | GPT models |
| **Google** | Gemini |
| **Meta** | Llama |
| **Mistral** | Mistral models |

### Framework Support

| Framework | Status |
|-----------|--------|
| Strands Agents | Supported |
| LangGraph | Supported |
| CrewAI | Supported |
| LlamaIndex | Supported |
| Google ADK | Supported |
| OpenAI Agents SDK | Supported |
| Custom frameworks | Supported |

### Protocol Support

| Protocol | Use Case |
|----------|----------|
| **HTTP** | Direct REST API endpoints for request/response patterns |
| **MCP** | Model Context Protocol for tools and agent servers |
| **A2A** | Agent-to-Agent protocol for multi-agent communication |

### Session Configuration

| Parameter | Value |
|-----------|-------|
| **Maximum session duration** | 8 hours |
| **Idle timeout** | 15 minutes |
| **Session isolation** | Dedicated microVM per session |

### Endpoint Configuration

- **DEFAULT endpoint**: Automatically created, updates to latest version
- **Custom endpoints**: Support multiple environments (dev, test, prod)
- Each endpoint has unique ARN for invocation

**Endpoint Lifecycle States**:
- `CREATING`, `CREATE_FAILED`, `READY`, `UPDATING`, `UPDATE_FAILED`

### Regional Availability (Preview)

- US East (N. Virginia)
- US West (Oregon)
- Asia Pacific (Sydney)
- Europe (Frankfurt)
- Plus 5 additional regions (9 total)

---

## Key Takeaways

1. **Strands Integration**: Simple SDK import enables full AgentCore capabilities; agents are portable across compute options
2. **Flexible Deployment**: Container-based, direct code, or Lambda integration patterns available with IaC support
3. **Enterprise Security**: Dual-layer authentication (inbound/outbound), session isolation in microVMs, IdP integration
4. **Cost Efficient**: True pay-per-use with no charges during I/O wait periods (30-70% of typical agent workload)
5. **Model Agnostic**: Works with any model provider, any framework, supporting HTTP/MCP/A2A protocols

---

## Sources

- [Strands Agents - Deploy to Bedrock AgentCore](https://strandsagents.com/latest/documentation/docs/user-guide/deploy/deploy_to_bedrock_agentcore/)
- [AWS Docs - How AgentCore Runtime Works](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-how-it-works.html)
- [AWS Docs - Host Agent or Tools with AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html)
- [AWS - Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/)
- [AWS - Amazon Bedrock AgentCore Pricing](https://aws.amazon.com/bedrock/agentcore/pricing/)
- [AWS - Amazon Bedrock AgentCore FAQs](https://aws.amazon.com/bedrock/agentcore/faqs/)
- [AWS News Blog - Introducing Amazon Bedrock AgentCore](https://aws.amazon.com/blogs/aws/introducing-amazon-bedrock-agentcore-securely-deploy-and-operate-ai-agents-at-any-scale/)
- [AWS Blog - Iterate Faster with Direct Code Deployment](https://aws.amazon.com/blogs/machine-learning/iterate-faster-with-amazon-bedrock-agentcore-runtime-direct-code-deployment/)
- [GitHub - Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
