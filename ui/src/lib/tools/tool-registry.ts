import { PubMedSearchTool } from './pubmed-search';
import { GrobidParserTool } from './grobid-parser';

class ToolRegistry {
  private tools: any[] = [];

  constructor() {
    this.registerDefaultTools();
  }

  private registerDefaultTools() {
    this.tools.push(new PubMedSearchTool());
    this.tools.push(new GrobidParserTool());
  }

  getTools() {
    return this.tools;
  }
}

export const toolRegistry = new ToolRegistry();
