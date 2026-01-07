# Strategies for Handling Large PR Diffs That Exceed LLM Context Windows

## Executive Summary

When PR diffs exceed LLM context windows, effective strategies include file-by-file review with parallel processing, intelligent diff chunking with overlap, hierarchical aggregation patterns (Chain-of-Agents or Map-Reduce), and proactive token counting using Bedrock's Count Tokens API.

---

## 1. File-by-File Review Approaches

### Recommended Strategy
Process each file diff independently in parallel, then aggregate results.

**Benefits:**
- Keeps input tokens small per request
- Enables parallel processing for speed
- Improves response quality through focused context
- Allows model mixing (e.g., GPT-4o + Claude simultaneously)

**Implementation Pattern:**
```python
async def review_pr_files(files: list[FileDiff]) -> list[ReviewComment]:
    # Process files in parallel
    tasks = [review_single_file(f) for f in files]
    results = await asyncio.gather(*tasks)
    return flatten(results)
```

**Performance Benchmarks:**
- Small PRs (<300 lines): 30-45 seconds
- Medium PRs (300-1,500 lines): 1-3 minutes
- Parallelization keeps processing fast even for large PRs

### Scope Limiting Best Practices
- Ignore vendor/migration folders by default
- Raise severity for security-critical directories (`auth/`, `payments/`)
- Limit suggestions to diffs only (no drive-by comments on untouched code)
- Turn down sensitivity for generated code and snapshots

---

## 2. Diff Chunking Strategies

### Sliding Window Chunking
```
Chunk 1: tokens 0-200
Chunk 2: tokens 150-350 (50 token overlap)
Chunk 3: tokens 300-500 (50 token overlap)
```

**Pros:** Preserves context across boundaries
**Cons:** Increased storage/processing cost due to redundancy

### Recursive/Hierarchical Chunking
Split by logical structure:
1. File level
2. Class/function level
3. Method/block level

Best for code because it respects semantic boundaries.

### AST-Based Chunking (for Code)
1. Parse code into Abstract Syntax Tree
2. Segment based on AST nodes (functions, classes)
3. Re-rank segments by relevance to review criteria

### Practical Recommendations
- **Chunk size:** 4,000-8,000 tokens per chunk (leaves room for system prompt + response)
- **Overlap:** 10-20% overlap between chunks
- **Metadata:** Include file path, line numbers, and surrounding context with each chunk

---

## 3. Aggregating Results from Multiple Chunks

### Pattern 1: Chain-of-Agents (CoA)
Sequential worker agents process chunks, passing accumulated context forward.

```
Worker 1 (Chunk 1) -> Worker 2 (Chunk 2 + W1 findings) -> ... -> Manager (Final synthesis)
```

**Best for:** Complex reviews requiring cross-chunk reasoning

### Pattern 2: Map-Reduce
```python
def map_reduce_review(diff_chunks):
    # Map Phase: Process chunks in parallel
    partial_results = parallel_map(review_chunk, diff_chunks)

    # Reduce Phase: Synthesize findings
    final_review = reduce_findings(partial_results)
    return final_review
```

**Best for:** High-throughput processing, independent chunk analysis

### Pattern 3: Hierarchical Summarization
1. Summarize each chunk independently
2. Group summaries and create higher-level summaries
3. Repeat until single coherent output

**Best for:** Very large PRs, creating executive summaries

### Filtering Pipeline (Post-Aggregation)
1. **Deduplication Filter:** Remove redundant findings across chunks
2. **Confidence Filter:** Drop low-confidence suggestions
3. **Hallucination Filter:** Validate findings against actual code
4. **Comment Editor:** Improve clarity and actionability

---

## 4. Token Counting for Bedrock Models

### AWS Bedrock Count Tokens API (August 2025)

```python
import boto3

bedrock_runtime = boto3.client('bedrock-runtime')

response = bedrock_runtime.count_tokens(
    modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
    body={
        "messages": [{"role": "user", "content": diff_content}],
        "system": system_prompt
    }
)
token_count = response['inputTokens']
```

**Key Considerations:**
- API adds ~7 tokens overhead for message structure wrapping
- Available in all regions where Claude models are supported
- Requires `bedrock:CountTokens` IAM permission

### Pre-Request Validation Pattern
```python
def validate_and_chunk(content: str, max_tokens: int = 150000) -> list[str]:
    token_count = count_tokens(content)

    if token_count <= max_tokens:
        return [content]

    # Chunk if exceeds limit
    return chunk_content(content, target_size=max_tokens * 0.8)
```

### Approximation Methods (When API Not Available)
- **Tiktoken (cl100k_base):** Reasonable approximation for Claude
- **Heuristic:** ~4 characters per token for code, ~3.5 for English text
- **Hybrid:** Use fast heuristic first, API only when near limits

### Cost Optimization
- `max_tokens` is deducted from quota at request start
- Set `max_tokens` to approximate expected response size
- Output token burndown rate is 5x for some models

---

## 5. Best Practices for Code Review Agents

### Architecture Recommendations

1. **Parallel Comment Generators**
   - Separate agents for different concern types:
     - Style/formatting violations
     - Security issues
     - Performance concerns
     - Logic errors
     - Customer-defined rules

2. **Chunking Decision Tree**
   ```
   PR Size < 300 LOC  -> Single request
   PR Size < 1500 LOC -> File-by-file parallel
   PR Size > 1500 LOC -> File chunking + aggregation
   ```

3. **Quality Control Pipeline**
   - Never blindly trust LLM output
   - Implement multi-stage filtering
   - Validate suggested changes against codebase
   - Track false positive rates

### GitHub API Limitations
- Diff API returns 406 error for diffs > 3,000 lines
- Implement pagination for large PRs
- Use file-based filtering when possible

### Recommended Workflow
```
1. Fetch PR metadata
2. Count total tokens
3. Decide chunking strategy based on size
4. Process chunks (parallel where possible)
5. Aggregate and filter results
6. Post comments to PR
```

### Error Handling
- Implement exponential backoff with jitter
- Handle partial failures gracefully
- Cache intermediate results for retry scenarios

---

## Quick Reference: Strategy Selection

| PR Size | Strategy | Expected Time |
|---------|----------|---------------|
| < 300 LOC | Single request | 30-45s |
| 300-1,500 LOC | File-by-file parallel | 1-3 min |
| 1,500-5,000 LOC | File chunking + map-reduce | 3-5 min |
| > 5,000 LOC | Hierarchical + sampling | 5-10 min |

---

## Sources

- [Pinecone: Chunking Strategies for LLM Applications](https://www.pinecone.io/learn/chunking-strategies/)
- [Addy Osmani: My LLM Coding Workflow Going Into 2026](https://medium.com/@addyosmani/my-llm-coding-workflow-going-into-2026-52fe1681325e)
- [AWS: Count Tokens API for Claude Models in Bedrock](https://aws.amazon.com/about-aws/whats-new/2025/08/count-tokens-api-anthropics-claude-models-bedrock/)
- [AWS Docs: Monitor Token Usage by Counting Tokens](https://docs.aws.amazon.com/bedrock/latest/userguide/count-tokens.html)
- [Google Research: Chain of Agents for Long-Context Tasks](https://research.google/blog/chain-of-agents-large-language-models-collaborating-on-long-context-tasks/)
- [Anyscale: Building an LLM-powered GitHub Bot](https://www.anyscale.com/blog/building-an-llm-powered-github-bot-to-improve-your-pull-requests)
- [ZenML: Building Production LLM Code Review Agents](https://www.zenml.io/llmops-database/building-and-deploying-production-llm-code-review-agents-architecture-and-best-practices)
- [GitHub MCP Server: Pagination for Large PRs](https://github.com/github/github-mcp-server/issues/625)
- [JetBrains Research: Efficient Context Management](https://blog.jetbrains.com/research/2025/12/efficient-context-management/)
- [Propel: Token Counting Guide 2025](https://www.propelcode.ai/blog/token-counting-tiktoken-anthropic-gemini-guide-2025)
- [Arxiv: Hierarchical Repository-Level Code Summarization](https://arxiv.org/html/2501.07857v1)
