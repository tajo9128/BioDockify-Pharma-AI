"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Send, Search, BookOpen, FileText, Settings, Bot, Plus, Trash2, Download, Sparkles } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  provider?: string;
}

interface SearchResult {
  id: string;
  title: string;
  source: string;
  authors?: string[];
  year?: string;
  url?: string;
}

type Tab = 'chat' | 'research' | 'deep' | 'kb' | 'writing';

export default function BioDockifyAgent() {
  const [activeTab, setActiveTab] = useState<Tab>('chat');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [provider, setProvider] = useState('ollama');
  const [model, setModel] = useState('llama3.2');
  const [models, setModels] = useState<{ollama: string[], openai: string[], anthropic: string[]}>({
    ollama: [], openai: [], anthropic: []
  });
  const [documents, setDocuments] = useState<{id: string, title: string, source: string}[]>([]);
  const messagesEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadModels();
    loadDocuments();
    setMessages([{
      id: '1',
      role: 'system',
      content: `🔬 BioDockify Pharma AI v1.60

Your AI Research Assistant for PhD Scholars

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROVIDERS: Ollama (local), OpenAI, Anthropic
FEATURES:
• Chat with AI (choose provider)
• Literature Search (PubMed, Semantic Scholar, arXiv)
• Deep Research (web scraping + literature)
• Knowledge Base (store & search)
• Academic Writing (templates)

Ready to research!`
    }]);
  }, []);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadModels = async () => {
    try {
      const res = await fetch('/api/models');
      const data = await res.json();
      setModels(data);
    } catch (e) {
      console.error('Failed to load models:', e);
    }
  };

  const loadDocuments = async () => {
    try {
      const res = await fetch('/api/kb');
      const data = await res.json();
      setDocuments(data.documents || []);
    } catch (e) {
      console.error('Failed to load docs:', e);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: input,
          model: model,
          provider: provider
        })
      });
      
      const data = await res.json();
      
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response,
        provider: data.provider
      }]);
    } catch (e) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `❌ Error: ${e}`
      }]);
    }
    setLoading(false);
  };

  const searchLiterature = async (query: string, sources: string[]) => {
    setLoading(true);
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'user',
      content: `🔍 Search: "${query}" in ${sources.join(', ')}`
    }]);
    
    try {
      const res = await fetch('/api/research/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, sources, limit: 10 })
      });
      const data = await res.json();
      
      const resultsText = data.results?.length 
        ? data.results.map((r: SearchResult, i: number) => 
            `${i + 1}. ${r.title}\n   📚 ${r.authors?.slice(0,2).join(', ')} (${r.year || 'N/A'})\n   🔗 ${r.url || r.source}`
          ).join('\n\n')
        : 'No results found';
      
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `📚 Found ${data.count || 0} papers:\n\n${resultsText}`
      }]);
    } catch (e) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `❌ Search error: ${e}`
      }]);
    }
    setLoading(false);
  };

  const deepResearch = async (query: string) => {
    setLoading(true);
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'user',
      content: `🧠 Deep Research: "${query}"`
    }]);
    
    try {
      const res = await fetch('/api/research/deep', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, max_sources: 20 })
      });
      const data = await res.json();
      
      let resultText = `📚 Papers: ${data.papers?.length || 0}\n🌐 Web: ${data.web_results?.length || 0}\n\n`;
      
      if (data.papers?.length) {
        resultText += 'Top Papers:\n';
        data.papers.slice(0, 5).forEach((p: SearchResult, i: number) => {
          resultText += `${i + 1}. ${p.title}\n`;
        });
      }
      
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: resultText
      }]);
    } catch (e) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `❌ Deep Research error: ${e}`
      }]);
    }
    setLoading(false);
  };

  const tabs = [
    { id: 'chat', label: 'Chat', icon: Bot },
    { id: 'research', label: 'Search', icon: Search },
    { id: 'deep', label: 'Deep Research', icon: Sparkles },
    { id: 'kb', label: 'Knowledge Base', icon: BookOpen },
    { id: 'writing', label: 'Writing', icon: FileText },
  ];

  return (
    <div className="flex h-screen bg-slate-950 text-slate-200">
      <aside className="w-20 flex flex-col items-center py-6 bg-slate-900 border-r border-slate-800">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-teal-500 to-emerald-600 flex items-center justify-center text-xl font-bold mb-8">
          B
        </div>
        
        <nav className="flex flex-col gap-3">
          {tabs.map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as Tab)}
                className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${
                  activeTab === tab.id
                    ? 'bg-teal-500/20 text-teal-400'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                }`}
                title={tab.label}
              >
                <Icon className="w-5 h-5" />
              </button>
            );
          })}
        </nav>

        <div className="mt-auto">
          <button className="w-12 h-12 rounded-xl flex items-center justify-center text-slate-400 hover:text-slate-200 hover:bg-white/5">
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </aside>

      <main className="flex-1 flex flex-col">
        <header className="h-16 border-b border-slate-800 flex items-center justify-between px-6 bg-slate-900/50">
          <h1 className="text-lg font-semibold">
            {activeTab === 'chat' && 'BioDockify AI Chat'}
            {activeTab === 'research' && 'Literature Search'}
            {activeTab === 'deep' && 'Deep Research'}
            {activeTab === 'kb' && 'Knowledge Base'}
            {activeTab === 'writing' && 'Academic Writing'}
          </h1>
          
          <div className="flex items-center gap-3">
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm"
            >
              <option value="ollama">🦙 Ollama</option>
              <option value="openai">🤖 OpenAI</option>
              <option value="anthropic">📘 Anthropic</option>
            </select>
            
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm"
            >
              {(models[provider as keyof typeof models] || []).map(m => (
                <option key={m} value={m}>{m}</option>
              ))}
              {provider === 'ollama' && <option value="llama3.2">llama3.2</option>}
            </select>
          </div>
        </header>

        <div className="flex-1 overflow-hidden">
          {activeTab === 'chat' && (
            <ChatInterface 
              messages={messages} 
              input={input} 
              setInput={setInput}
              sendMessage={sendMessage}
              loading={loading}
              messagesEnd={messagesEnd}
            />
          )}

          {activeTab === 'research' && (
            <ResearchInterface onSearch={searchLiterature} loading={loading} />
          )}

          {activeTab === 'deep' && (
            <DeepResearchInterface onResearch={deepResearch} loading={loading} />
          )}

          {activeTab === 'kb' && (
            <KBInterface documents={documents} onRefresh={loadDocuments} />
          )}

          {activeTab === 'writing' && (
            <WritingInterface />
          )}
        </div>
      </main>
    </div>
  );
}

function ChatInterface({ messages, input, setInput, sendMessage, loading, messagesEnd }: {
  messages: Message[], input: string, setInput: (v: string) => void,
  sendMessage: () => void, loading: boolean, messagesEnd: React.RefObject<HTMLDivElement | null>
}) {
  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
              msg.role === 'user' ? 'bg-teal-600 text-white' : 
              msg.role === 'system' ? 'bg-slate-800 text-slate-300 text-sm' : 'bg-slate-800 text-slate-200'
            }`}>
              <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
              {msg.provider && (
                <span className="text-xs text-slate-500 mt-1 block">via {msg.provider}</span>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800 rounded-2xl px-4 py-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-teal-400 rounded-full animate-bounce" />
                <span className="w-2 h-2 bg-teal-400 rounded-full animate-bounce [animation-delay:0.1s]" />
                <span className="w-2 h-2 bg-teal-400 rounded-full animate-bounce [animation-delay:0.2s]" />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEnd} />
      </div>

      <div className="p-4 border-t border-slate-800">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder="Ask about your research..."
            className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 focus:ring-2 focus:ring-teal-500"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="bg-teal-600 hover:bg-teal-500 disabled:opacity-50 rounded-xl px-4 py-3"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}

function ResearchInterface({ onSearch, loading }: { onSearch: (q: string, s: string[]) => void, loading: boolean }) {
  const [query, setQuery] = useState('');
  const [sources, setSources] = useState(['pubmed', 'semantic_scholar', 'arxiv']);

  const sourceOptions = [
    { id: 'pubmed', label: 'PubMed' },
    { id: 'semantic_scholar', label: 'Semantic Scholar' },
    { id: 'arxiv', label: 'arXiv' },
  ];

  return (
    <div className="h-full p-6">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-xl font-semibold mb-4">Search Academic Literature</h2>
        <div className="space-y-4">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter research query..."
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3"
          />
          <div className="flex flex-wrap gap-2">
            {sourceOptions.map(src => (
              <label key={src.id} className="flex items-center gap-2 bg-slate-800 px-3 py-2 rounded-lg cursor-pointer">
                <input
                  type="checkbox"
                  checked={sources.includes(src.id)}
                  onChange={(e) => {
                    if (e.target.checked) setSources([...sources, src.id]);
                    else setSources(sources.filter(s => s !== src.id));
                  }}
                  className="accent-teal-500"
                />
                <span>{src.label}</span>
              </label>
            ))}
          </div>
          <button
            onClick={() => onSearch(query, sources)}
            disabled={loading || !query.trim()}
            className="w-full bg-teal-600 hover:bg-teal-500 disabled:opacity-50 rounded-xl py-3 flex items-center justify-center gap-2"
          >
            <Search className="w-5 h-5" />
            {loading ? 'Searching...' : 'Search Literature'}
          </button>
        </div>
      </div>
    </div>
  );
}

function DeepResearchInterface({ onResearch, loading }: { onResearch: (q: string) => void, loading: boolean }) {
  const [query, setQuery] = useState('');

  return (
    <div className="h-full p-6">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-xl font-semibold mb-4">🧠 Deep Research</h2>
        <p className="text-slate-400 mb-4">
          Comprehensive research across literature databases + web scraping
        </p>
        <div className="space-y-4">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter complex research question..."
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3"
          />
          <button
            onClick={() => onResearch(query)}
            disabled={loading || !query.trim()}
            className="w-full bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 disabled:opacity-50 rounded-xl py-3 flex items-center justify-center gap-2"
          >
            <Sparkles className="w-5 h-5" />
            {loading ? 'Researching...' : 'Start Deep Research'}
          </button>
          <div className="bg-slate-800 rounded-xl p-4 text-sm text-slate-400">
            <p>🔍 Searches: PubMed, Semantic Scholar, arXiv + Web</p>
            <p>🌐 Scrapes: Academic websites, preprints</p>
            <p>📊 Collects: Papers, abstracts, citations, web sources</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function KBInterface({ documents, onRefresh }: { documents: any[], onRefresh: () => void }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [adding, setAdding] = useState(false);
  const [newDoc, setNewDoc] = useState({ title: '', content: '', source: '' });

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    try {
      const res = await fetch('/api/kb/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, limit: 10 })
      });
      const data = await res.json();
      setResults(data.results || []);
    } catch (e) {
      console.error('Search error:', e);
    }
  };

  const handleAdd = async () => {
    if (!newDoc.title || !newDoc.content) return;
    try {
      await fetch('/api/kb/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newDoc)
      });
      setNewDoc({ title: '', content: '', source: '' });
      setAdding(false);
      onRefresh();
    } catch (e) {
      console.error('Add error:', e);
    }
  };

  return (
    <div className="h-full p-6 overflow-y-auto">
      <div className="max-w-2xl mx-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">📚 Knowledge Base</h2>
          <button 
            onClick={() => setAdding(!adding)}
            className="bg-teal-600 px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> Add
          </button>
        </div>

        {adding && (
          <div className="bg-slate-800 rounded-xl p-4 mb-4 space-y-3">
            <input
              value={newDoc.title}
              onChange={(e) => setNewDoc({...newDoc, title: e.target.value})}
              placeholder="Title"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2"
            />
            <textarea
              value={newDoc.content}
              onChange={(e) => setNewDoc({...newDoc, content: e.target.value})}
              placeholder="Content..."
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 h-32"
            />
            <input
              value={newDoc.source}
              onChange={(e) => setNewDoc({...newDoc, source: e.target.value})}
              placeholder="Source (e.g., meeting-notes, paper-summary)"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2"
            />
            <div className="flex gap-2">
              <button onClick={handleAdd} className="bg-teal-600 px-4 py-2 rounded-lg">Save</button>
              <button onClick={() => setAdding(false)} className="bg-slate-700 px-4 py-2 rounded-lg">Cancel</button>
            </div>
          </div>
        )}

        <div className="flex gap-2 mb-4">
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search knowledge base..."
            className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2"
          />
          <button onClick={handleSearch} className="bg-slate-700 px-4 py-2 rounded-lg">
            <Search className="w-4 h-4" />
          </button>
        </div>

        {results.length > 0 && (
          <div className="space-y-2 mb-4">
            <h3 className="text-sm text-slate-400">Search Results:</h3>
            {results.map(r => (
              <div key={r.id} className="bg-slate-800 rounded-lg p-3">
                <h4 className="font-medium">{r.title}</h4>
                <p className="text-sm text-slate-400 line-clamp-2">{r.content}</p>
              </div>
            ))}
          </div>
        )}

        <div className="space-y-2">
          {documents.length === 0 ? (
            <p className="text-slate-400">No documents yet. Add your research notes!</p>
          ) : documents.map(doc => (
            <div key={doc.id} className="bg-slate-800 rounded-lg p-3 flex justify-between items-center">
              <div>
                <h4 className="font-medium">{doc.title}</h4>
                <p className="text-sm text-slate-400">{doc.source}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function WritingInterface() {
  const [template, setTemplate] = useState('thesis');

  return (
    <div className="h-full p-6 overflow-y-auto">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-xl font-semibold mb-4">📝 Academic Writing</h2>
        
        <div className="grid grid-cols-3 gap-3 mb-6">
          {[
            { id: 'thesis', label: 'Thesis Template' },
            { id: 'review', label: 'Review Template' },
          ].map(t => (
            <button
              key={t.id}
              onClick={() => setTemplate(t.id)}
              className={`p-4 rounded-xl text-center ${
                template === t.id ? 'bg-teal-600' : 'bg-slate-800 hover:bg-slate-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        
        {template === 'thesis' && (
          <div className="bg-slate-800 rounded-xl p-6">
            <h3 className="font-semibold mb-4">Thesis Structure</h3>
            <ol className="space-y-2">
              {[
                'Abstract (250-300 words)',
                'Introduction (background, problem, research questions)',
                'Literature Review (existing research and gaps)',
                'Methodology (research methods and design)',
                'Results (findings with data analysis)',
                'Discussion (interpretation of results)',
                'Conclusion (summary and future work)',
                'References (bibliography)',
              ].map((s, i) => (
                <li key={s} className="flex gap-3">
                  <span className="text-teal-400 font-mono">{i + 1}.</span>
                  {s}
                </li>
              ))}
            </ol>
          </div>
        )}
        
        {template === 'review' && (
          <div className="bg-slate-800 rounded-xl p-6">
            <h3 className="font-semibold mb-4">Article Review Template</h3>
            <pre className="text-sm whitespace-pre-wrap">
{`# Article Review Template

## Summary
[One paragraph summary]

## Strengths
- [Point 1]
- [Point 2]

## Weaknesses
- [Point 1]
- [Point 2]

## Specific Comments
### Introduction
### Methodology  
### Results
### Discussion

## Recommendation
- [ ] Accept
- [ ] Minor Revision
- [ ] Major Revision
- [ ] Reject`}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}