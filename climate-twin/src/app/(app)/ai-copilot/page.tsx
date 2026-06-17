"use client"

import * as React from "react"
import { PageHeader } from "@/components/PageHeader"
import { Card } from "@/components/Card"
import { SectionHeading } from "@/components/SectionHeading"
import { Button } from "@/components/Button"
import { Input } from "@/components/ui/input"
import {
  Bot,
  Send,
  Sparkles,
  User,
  Copy,
  ThumbsUp,
  ThumbsDown,
  Mic,
  Paperclip,
  RefreshCw,
  Satellite,
  BarChart3,
  Map,
  FlaskConical,
} from "lucide-react"

/* ── Message types ─────────────────────────────────────────────────────── */
interface Message {
  id: number
  role: "user" | "assistant"
  content: string
  timestamp: string
}

/* ── Mock conversation ─────────────────────────────────────────────────── */
const INITIAL_MESSAGES: Message[] = [
  {
    id: 1,
    role: "assistant",
    content: "Hello! I'm the **Climate Twin AI Copilot**, powered by real-time satellite data from ISRO's constellation.\n\nI can help you:\n- Analyze regional climate trends and anomalies\n- Interpret NDVI, CO₂, and temperature satellite indices\n- Run natural language queries on climate datasets\n- Summarize risk reports for any region of India\n\nWhat would you like to explore today?",
    timestamp: "Just now",
  },
]

/* ── Suggested prompts ─────────────────────────────────────────────────── */
const PROMPTS = [
  { icon: BarChart3, label: "Analyze CO₂ trends in Rajasthan over the last 30 days" },
  { icon: Map,       label: "Show regions with drought risk above 70% this month" },
  { icon: Satellite, label: "What does the NDVI anomaly in Kerala indicate?" },
  { icon: FlaskConical, label: "Simulate monsoon deficit impact on Vidarbha crops" },
]

/* ── Message bubble ────────────────────────────────────────────────────── */
function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user"

  /* Very basic markdown-like rendering */
  const renderContent = (text: string) =>
    text.split("\n").map((line, i) => {
      const bold = line.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      const isBullet = line.startsWith("- ")
      return isBullet ? (
        <li key={i} dangerouslySetInnerHTML={{ __html: bold.slice(2) }} />
      ) : (
        <p key={i} className={i > 0 && !line ? "mt-2" : ""} dangerouslySetInnerHTML={{ __html: bold }} />
      )
    })

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div className={`flex size-8 shrink-0 items-center justify-center rounded-full ${
        isUser
          ? "bg-secondary border border-border"
          : "bg-gradient-to-br from-climate-emerald to-climate-teal shadow-md shadow-climate-emerald/20"
      }`}>
        {isUser
          ? <User className="size-4 text-muted-foreground" aria-hidden />
          : <Bot className="size-4 text-white" aria-hidden />
        }
      </div>

      {/* Bubble */}
      <div className={`flex max-w-[80%] flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}>
        <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "rounded-tr-sm bg-primary text-primary-foreground"
            : "rounded-tl-sm border border-border bg-card text-foreground"
        }`}>
          {msg.role === "assistant" ? (
            <div className="flex flex-col gap-1">
              {renderContent(msg.content)}
            </div>
          ) : (
            msg.content
          )}
        </div>

        {/* Actions for assistant messages */}
        {!isUser && (
          <div className="flex items-center gap-1">
            <span className="text-[10px] text-muted-foreground">{msg.timestamp}</span>
            {[
              { icon: Copy,      label: "Copy" },
              { icon: ThumbsUp,  label: "Good response" },
              { icon: ThumbsDown,label: "Bad response" },
              { icon: RefreshCw, label: "Regenerate" },
            ].map(({ icon: Icon, label }) => (
              <button
                key={label}
                aria-label={label}
                className="flex size-6 items-center justify-center rounded text-muted-foreground/60 transition-colors hover:bg-secondary hover:text-foreground"
              >
                <Icon className="size-3" aria-hidden />
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

/* ── Page ──────────────────────────────────────────────────────────────── */
export default function AICopilotPage() {
  const [messages, setMessages] = React.useState<Message[]>(INITIAL_MESSAGES)
  const [input, setInput] = React.useState("")
  const bottomRef = React.useRef<HTMLDivElement>(null)

  const send = (text?: string) => {
    const content = text ?? input.trim()
    if (!content) return

    const userMsg: Message = { id: Date.now(), role: "user", content, timestamp: "Just now" }
    const aiMsg: Message = {
      id: Date.now() + 1,
      role: "assistant",
      content: `Analyzing your query: **"${content}"**\n\nFetching data from ISRO satellite constellation and cross-referencing with historical climate models...\n\nThis is a placeholder response. Connect to your AI backend (e.g. Gemini API / Claude / GPT-4) to stream real-time climate intelligence here.`,
      timestamp: "Just now",
    }

    setMessages((prev) => [...prev, userMsg, aiMsg])
    setInput("")
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100)
  }

  return (
    <div className="flex flex-col gap-4" style={{ height: "calc(100vh - 3.5rem - 3rem)" }}>
      <PageHeader
        title={<span>AI <span className="text-gradient-climate">Copilot</span></span>}
        subtitle="Natural language climate intelligence · Powered by ISRO satellite data"
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "AI Copilot" }]}
        compact
        actions={
          <div className="flex items-center gap-1.5">
            <div className="flex items-center gap-1.5 rounded-full border border-climate-emerald/30 bg-climate-emerald/10 px-2.5 py-1 text-xs font-medium text-climate-emerald">
              <Sparkles className="size-3" />
              Gemini Pro
            </div>
            <Button variant="outline" size="sm">New Chat</Button>
          </div>
        }
      />

      <div className="flex min-h-0 flex-1 gap-4">
        {/* ── Chat area ─────────────────────────────────────────────── */}
        <div className="flex flex-1 min-w-0 flex-col rounded-xl border border-border bg-card overflow-hidden">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-5">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Suggested prompts — only shown when empty */}
          {messages.length === 1 && (
            <div className="border-t border-border px-4 py-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Suggested</p>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {PROMPTS.map(({ icon: Icon, label }) => (
                  <button
                    key={label}
                    onClick={() => send(label)}
                    className="flex items-start gap-2 rounded-lg border border-border bg-secondary/30 px-3 py-2 text-left text-xs text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                  >
                    <Icon className="mt-0.5 size-3.5 shrink-0 text-climate-teal" aria-hidden />
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input bar */}
          <div className="border-t border-border p-3">
            <div className="flex items-end gap-2 rounded-xl border border-border bg-secondary/40 px-3 py-2 focus-within:border-primary/50 focus-within:bg-secondary/60 transition-colors">
              <button aria-label="Attach file" className="mb-0.5 shrink-0 text-muted-foreground hover:text-foreground transition-colors">
                <Paperclip className="size-4" aria-hidden />
              </button>
              <textarea
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send() } }}
                placeholder="Ask about any climate indicator, region, or anomaly…"
                className="flex-1 resize-none bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
                style={{ maxHeight: 120 }}
                aria-label="Message input"
              />
              <div className="mb-0.5 flex shrink-0 items-center gap-1">
                <button aria-label="Voice input" className="text-muted-foreground hover:text-foreground transition-colors">
                  <Mic className="size-4" aria-hidden />
                </button>
                <button
                  onClick={() => send()}
                  disabled={!input.trim()}
                  aria-label="Send message"
                  className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground transition-opacity disabled:opacity-40 hover:opacity-90"
                >
                  <Send className="size-3.5" aria-hidden />
                </button>
              </div>
            </div>
            <p className="mt-1.5 text-center text-[10px] text-muted-foreground/60">
              AI responses are based on satellite data and climate models. Verify critical decisions independently.
            </p>
          </div>
        </div>

        {/* ── Side panel ────────────────────────────────────────────── */}
        <div className="hidden w-56 shrink-0 flex-col gap-3 xl:flex">
          <Card title={<SectionHeading title="Data Sources" accent="dot" />}>
            {[
              { name: "RESOURCESAT-2A", status: "Live" },
              { name: "INSAT-3DR",      status: "Live" },
              { name: "Cartosat-3",     status: "Live" },
              { name: "CMIP6 Models",   status: "Cached" },
              { name: "IMD Records",    status: "Live" },
            ].map(({ name, status }) => (
              <div key={name} className="flex items-center justify-between py-1.5 text-xs border-b border-border/50 last:border-0">
                <span className="text-muted-foreground">{name}</span>
                <span className={`font-medium ${status === "Live" ? "text-climate-emerald" : "text-muted-foreground"}`}>
                  {status}
                </span>
              </div>
            ))}
          </Card>

          <Card title={<SectionHeading title="Capabilities" accent="dot" />}>
            {[
              "Regional trend analysis",
              "Anomaly detection",
              "Crop impact prediction",
              "Carbon flux estimation",
              "Extreme event forecast",
            ].map((cap) => (
              <div key={cap} className="flex items-center gap-2 py-1.5 text-xs border-b border-border/50 last:border-0">
                <span className="size-1.5 shrink-0 rounded-full bg-climate-emerald" />
                <span className="text-muted-foreground">{cap}</span>
              </div>
            ))}
          </Card>
        </div>
      </div>
    </div>
  )
}
