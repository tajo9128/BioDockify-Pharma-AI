/**
 * BioDockify AI Panel - Unified Interface
 * 
 * Features:
 * - Chat with BioDockify AI
 * - Spawn background tasks
 * - Schedule recurring research jobs
 * - View memory and skills
 */

import React, { useState, useEffect, useRef } from 'react';
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription
} from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { Badge } from "./ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { ScrollArea } from "./ui/scroll-area";
import {
    Bot,
    Send,
    Cpu,
    Clock,
    Brain,
    Sparkles,
    Terminal,
    Calendar,
    Play,
    Trash2,
    RefreshCcw,
    MessageSquare
} from "lucide-react";

// API base URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3000";

interface Message {
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
}

interface CronJob {
    id: string;
    name: string;
    enabled: boolean;
    next_run_at_ms: number | null;
    last_status: string | null;
}

interface Skill {
    name: string;
    path: string;
    source: string;
}

export default function NanoBotPanel() {
    // Chat state
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Status state
    const [status, setStatus] = useState<any>(null);

    // Cron jobs state
    const [cronJobs, setCronJobs] = useState<CronJob[]>([]);
    const [newJobName, setNewJobName] = useState('');
    const [newJobMessage, setNewJobMessage] = useState('');
    const [newJobCron, setNewJobCron] = useState('0 9 * * *');

    // Skills state
    const [skills, setSkills] = useState<Skill[]>([]);

    // Spawn task state
    const [spawnTask, setSpawnTask] = useState('');
    const [spawnLabel, setSpawnLabel] = useState('');

    // Fetch status on mount
    useEffect(() => {
        fetchStatus();
        fetchCronJobs();
        fetchSkills();
    }, []);

    // Auto-scroll messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const fetchStatus = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/nanobot/status`);
            const data = await res.json();
            setStatus(data);
        } catch (e) {
            console.error('Failed to fetch status:', e);
        }
    };

    const fetchCronJobs = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/nanobot/cron`);
            const data = await res.json();
            setCronJobs(data.jobs || []);
        } catch (e) {
            console.error('Failed to fetch cron jobs:', e);
        }
    };

    const fetchSkills = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/nanobot/skills`);
            const data = await res.json();
            setSkills(data.skills || []);
        } catch (e) {
            console.error('Failed to fetch skills:', e);
        }
    };

    const sendMessage = async () => {
        if (!input.trim()) return;

        const userMessage: Message = {
            role: 'user',
            content: input,
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            const res = await fetch(`${API_BASE}/api/nanobot/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: input })
            });

            const data = await res.json();

            const assistantMessage: Message = {
                role: 'assistant',
                content: data.response || 'No response',
                timestamp: new Date()
            };

            setMessages(prev => [...prev, assistantMessage]);
        } catch (e) {
            console.error('Chat error:', e);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: `Error: ${e}`,
                timestamp: new Date()
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const spawnBackgroundTask = async () => {
        if (!spawnTask.trim()) return;

        try {
            const res = await fetch(`${API_BASE}/api/nanobot/spawn`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task: spawnTask, label: spawnLabel || undefined })
            });

            const data = await res.json();
            alert(data.message);
            setSpawnTask('');
            setSpawnLabel('');
            fetchStatus();
        } catch (e) {
            console.error('Spawn error:', e);
            alert(`Failed to spawn task: ${e}`);
        }
    };

    const scheduleJob = async () => {
        if (!newJobName.trim() || !newJobMessage.trim()) return;

        try {
            const res = await fetch(`${API_BASE}/api/nanobot/schedule`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: newJobName,
                    message: newJobMessage,
                    cron_expr: newJobCron
                })
            });

            const data = await res.json();
            alert(`Job scheduled! ID: ${data.id}`);
            setNewJobName('');
            setNewJobMessage('');
            fetchCronJobs();
        } catch (e) {
            console.error('Schedule error:', e);
            alert(`Failed to schedule job: ${e}`);
        }
    };

    const deleteJob = async (jobId: string) => {
        try {
            await fetch(`${API_BASE}/api/nanobot/cron/${jobId}`, { method: 'DELETE' });
            fetchCronJobs();
        } catch (e) {
            console.error('Delete error:', e);
        }
    };

    const formatDate = (ms: number | null) => {
        if (!ms) return 'N/A';
        return new Date(ms).toLocaleString();
    };

    return (
        <div className="flex flex-col gap-4 p-4 h-full">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg">
                        <Bot className="h-6 w-6 text-white" />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold">BioDockify AI</h2>
                        <p className="text-sm text-gray-500">Research Workstation v2.4.9</p>
                    </div>
                </div>
                {status && (
                    <div className="flex items-center gap-2">
                        <Badge variant="outline" className="flex items-center gap-1">
                            <Cpu className="h-3 w-3" />
                            {status.running_subagents || 0} tasks
                        </Badge>
                        <Badge variant="outline" className="flex items-center gap-1">
                            <Brain className="h-3 w-3" />
                            {skills.length} skills
                        </Badge>
                        <Badge variant="outline" className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {cronJobs.length} jobs
                        </Badge>
                    </div>
                )}
            </div>

            {/* Main Tabs */}
            <Tabs defaultValue="chat" className="flex-1 flex flex-col">
                <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="chat">
                        <MessageSquare className="h-4 w-4 mr-2" />
                        Chat
                    </TabsTrigger>
                    <TabsTrigger value="spawn">
                        <Terminal className="h-4 w-4 mr-2" />
                        Spawn
                    </TabsTrigger>
                    <TabsTrigger value="schedule">
                        <Calendar className="h-4 w-4 mr-2" />
                        Schedule
                    </TabsTrigger>
                    <TabsTrigger value="skills">
                        <Sparkles className="h-4 w-4 mr-2" />
                        Skills
                    </TabsTrigger>
                </TabsList>

                {/* Chat Tab */}
                <TabsContent value="chat" className="flex-1 flex flex-col">
                    <Card className="flex-1 flex flex-col">
                        <CardContent className="flex-1 flex flex-col p-4">
                            <ScrollArea className="flex-1 pr-4 mb-4">
                                <div className="space-y-4">
                                    {messages.length === 0 ? (
                                        <div className="text-center text-gray-500 py-8">
                                            <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
                                            <p>Start a conversation with BioDockify AI</p>
                                        </div>
                                    ) : (
                                        messages.map((msg, idx) => (
                                            <div
                                                key={idx}
                                                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                            >
                                                <div
                                                    className={`max-w-[80%] rounded-lg p-3 ${msg.role === 'user'
                                                        ? 'bg-purple-500 text-white'
                                                        : 'bg-gray-100 dark:bg-gray-800'
                                                        }`}
                                                >
                                                    <p className="whitespace-pre-wrap">{msg.content}</p>
                                                    <p className="text-xs opacity-50 mt-1">
                                                        {msg.timestamp.toLocaleTimeString()}
                                                    </p>
                                                </div>
                                            </div>
                                        ))
                                    )}
                                    <div ref={messagesEndRef} />
                                </div>
                            </ScrollArea>

                            <div className="flex gap-2">
                                <Input
                                    placeholder="Ask your research question..."
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                                    disabled={isLoading}
                                />
                                <Button onClick={sendMessage} disabled={isLoading}>
                                    {isLoading ? (
                                        <RefreshCcw className="h-4 w-4 animate-spin" />
                                    ) : (
                                        <Send className="h-4 w-4" />
                                    )}
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Spawn Tab */}
                <TabsContent value="spawn">
                    <Card>
                        <CardHeader>
                            <CardTitle>Spawn BioDockify AI Task</CardTitle>
                            <CardDescription>
                                Start a sub-task for BioDockify AI to handle in the background
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div>
                                <label className="text-sm font-medium">Task Description</label>
                                <Textarea
                                    placeholder="e.g., Search for papers about CRISPR and summarize findings"
                                    value={spawnTask}
                                    onChange={(e) => setSpawnTask(e.target.value)}
                                    className="mt-1"
                                />
                            </div>
                            <div>
                                <label className="text-sm font-medium">Label (optional)</label>
                                <Input
                                    placeholder="e.g., CRISPR Research"
                                    value={spawnLabel}
                                    onChange={(e) => setSpawnLabel(e.target.value)}
                                    className="mt-1"
                                />
                            </div>
                            <Button onClick={spawnBackgroundTask} className="w-full">
                                <Play className="h-4 w-4 mr-2" />
                                Spawn Task
                            </Button>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Schedule Tab */}
                <TabsContent value="schedule">
                    <div className="space-y-4">
                        <Card>
                            <CardHeader>
                                <CardTitle>Schedule Research Job</CardTitle>
                                <CardDescription>
                                    Create recurring automated research tasks
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-sm font-medium">Job Name</label>
                                        <Input
                                            placeholder="e.g., Daily Literature Scan"
                                            value={newJobName}
                                            onChange={(e) => setNewJobName(e.target.value)}
                                            className="mt-1"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-sm font-medium">Cron Expression</label>
                                        <Input
                                            placeholder="0 9 * * *"
                                            value={newJobCron}
                                            onChange={(e) => setNewJobCron(e.target.value)}
                                            className="mt-1"
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="text-sm font-medium">Task Message</label>
                                    <Textarea
                                        placeholder="The task to execute on schedule"
                                        value={newJobMessage}
                                        onChange={(e) => setNewJobMessage(e.target.value)}
                                        className="mt-1"
                                    />
                                </div>
                                <Button onClick={scheduleJob} className="w-full">
                                    <Calendar className="h-4 w-4 mr-2" />
                                    Schedule Job
                                </Button>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle>Scheduled Jobs</CardTitle>
                            </CardHeader>
                            <CardContent>
                                {cronJobs.length === 0 ? (
                                    <p className="text-center text-gray-500 py-4">No scheduled jobs</p>
                                ) : (
                                    <div className="space-y-2">
                                        {cronJobs.map((job) => (
                                            <div
                                                key={job.id}
                                                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                                            >
                                                <div>
                                                    <p className="font-medium">{job.name}</p>
                                                    <p className="text-sm text-gray-500">
                                                        Next: {formatDate(job.next_run_at_ms)}
                                                    </p>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <Badge variant={job.enabled ? "default" : "secondary"}>
                                                        {job.enabled ? "Active" : "Disabled"}
                                                    </Badge>
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        onClick={() => deleteJob(job.id)}
                                                    >
                                                        <Trash2 className="h-4 w-4 text-red-500" />
                                                    </Button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                {/* Skills Tab */}
                <TabsContent value="skills">
                    <Card>
                        <CardHeader>
                            <CardTitle>Available Skills</CardTitle>
                            <CardDescription>
                                Skills teach the agent specialized capabilities
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {skills.length === 0 ? (
                                <p className="text-center text-gray-500 py-4">No skills loaded</p>
                            ) : (
                                <div className="grid grid-cols-2 gap-2">
                                    {skills.map((skill) => (
                                        <div
                                            key={skill.name}
                                            className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                                        >
                                            <div className="flex items-center gap-2">
                                                <Sparkles className="h-4 w-4 text-purple-500" />
                                                <span className="font-medium">{skill.name}</span>
                                            </div>
                                            <p className="text-xs text-gray-500 mt-1">
                                                Source: {skill.source}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
