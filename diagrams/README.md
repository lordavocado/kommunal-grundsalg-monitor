# Diagrams

This folder contains Mermaid diagrams documenting the Kommunal Grundsalg Monitor system.

## Available Diagrams

| Diagram | Description |
|---------|-------------|
| [architecture-flowchart.md](architecture-flowchart.md) | System architecture showing all components, data flow, and external APIs |
| [processing-sequence.md](processing-sequence.md) | Temporal sequence of a single monitoring run |

## Viewing Diagrams

These diagrams use [Mermaid](https://mermaid.js.org/) syntax and render automatically on:
- GitHub (in markdown preview)
- VS Code (with Mermaid extension)
- Notion, Confluence, and other markdown tools

## Quick Reference

### Architecture Overview
```
sources.json → Discovery → AI Analysis → Google Sheets + Slack
     ↓              ↓            ↓
  97 sources    Firecrawl    GPT-4o-mini → GPT-4o
```

### Processing Phases
1. **Discovery** - Find new URLs from all sources
2. **AI Analysis** - Classify and extract property data
3. **Output** - Log results and send notifications
