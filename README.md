# VertexMemory - Google Vertex AI / Vector Search MCP Server

VertexMemory is your memory layer for LLMs using Google Vertex AI Vector Search - private, portable, open-source MCP Server. Your memories live locally, giving you complete control over your data. Build AI applications with sophisticated vector search integration..

## Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for backend development)
- Node.js (for frontend development)
- OpenAI API Key (required for LLM interactions)

## Quickstart

You can run the project using the following two commands:
```bash
make build # builds the mcp server and ui
make up  # runs vertexmemory mcp server and ui
```

After running these commands, you will have:
- VertexMemory MCP server running at: http://localhost:8765 (API documentation available at http://localhost:8765/docs)
- VertexMemory UI running at: http://localhost:3000

## Project Structure

- `api/` - Backend APIs + MCP server
- `ui/` - Frontend React application

## Contributing

We are a team of developers passionate about the future of AI and open-source software. With years of experience in both fields, we believe in the power of community-driven development and are excited to build tools that make AI more accessible and personalized.

We welcome all forms of contributions:
- Bug reports and feature requests
- Documentation improvements
- Code contributions
- Testing and feedback
- Community support

How to contribute:

1. Fork the repository
2. Create your feature branch (`git checkout -b vertexmemory/feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin vertexmemory/feature/amazing-feature`)
5. Open a Pull Request

Join us in building the future of AI memory management! Your contributions help make VertexMemory better for everyone.
