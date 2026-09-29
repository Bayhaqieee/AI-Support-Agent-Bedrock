# Submission Checklist

## Project: AI Customer Support Agent with Amazon Bedrock AgentCore

### Agent Deployment and Tool Integration

- [x] BedrockAgentCoreApp instance created and agent deployed to cloud runtime
- [x] Agent entrypoint decorated with @app.entrypoint
- [x] BedrockModel configured with amazon.nova-2-lite-v1:0
- [x] Agent deployed via agentcore deploy to AgentCore Runtime (PYTHON_3_13)
- [x] Agent ARN: arn:aws:bedrock-agentcore:us-east-1:016586718516:runtime/customer_support_agent-MoXBtpDpHj

### MCP Gateway Integration

- [x] AgentCore Gateway created and configured with MCP endpoint
- [x] Gateway URL: https://customersupportgateway-eeqgr9w2fn.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp
- [x] Lambda targets registered: order-tracker and refund-processor
- [x] MCPClient wraps gateway tools with try-except and logger.exception error handling
- [x] Order tracking tool (order-tracker___get_order) verified via Test Scenario 1
- [x] Refund processing tool (refund-processor___initiate_refund) verified via Test Scenario 2

### Knowledge Base (RAG)

- [x] Amazon Bedrock Knowledge Base created with OpenSearch Serverless vector store
- [x] KB_ID configured: 75EMY72ZDW
- [x] Knowledge Base guard clause implemented: returns descriptive error if KB_ID is empty or placeholder
- [x] Hybrid fallback to local product_catalog.txt when KB returns no results
- [x] Return policy retrieval verified via Test Scenario 3

### Long-Term Memory

- [x] AgentCore Memory created: CustomerSupportMemory-n6H2nwAv8i
- [x] MemoryHook implemented with MessageAddedEvent (retrieve) and AfterInvocationEvent (save)
- [x] Memory retrieval prepended to user message with strict no-tool-call instruction
- [x] Cross-session memory recall verified via Test Scenario 4 (Session A and Session B)

### Code Interpreter

- [x] calculate_loyalty_discount tool implemented using AgentCore Code Interpreter sandbox
- [x] Fallback arithmetic applied if Code Interpreter is unavailable
- [x] Discount calculation verified via Test Scenario 5

### Browser Tool

- [x] AgentCoreBrowser integrated as browser tool
- [x] HTTP fallback implemented for page title retrieval
- [x] Web navigation to https://www.udacity.com verified via Test Scenario 6

### Documentation

- [x] test_logs.md: all 6 test scenario outputs with CLI commands and verification results
- [x] reflection.md: architectural decisions, technical challenges, and production roadmap
- [x] Screenshots: evidence PNG files for all 6 test scenarios in Submission/screenshot/
- [x] main.py: complete implementation included in Submission folder

### Test Scenarios Summary

| Test | Scenario | Tool Used | Status |
|------|----------|-----------|--------|
| 1 | Order Tracking | order-tracker___get_order via MCP Gateway | PASS |
| 2 | Refund Processing | refund-processor___initiate_refund via MCP Gateway | PASS |
| 3 | Knowledge Base RAG | search_knowledge_base with Bedrock KB | PASS |
| 4 | Memory Recall | MemoryHook across sessions s-A and s-B | PASS |
| 5 | Loyalty Discount | calculate_loyalty_discount via Code Interpreter | PASS |
| 6 | Browser Tool | browser via AgentCoreBrowser | PASS |
