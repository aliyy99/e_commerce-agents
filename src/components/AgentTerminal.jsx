import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, ChevronDown, ChevronUp, X, Cpu } from 'lucide-react';

/**
 * AgentTerminal — A real-time "Agentic Logs" terminal panel.
 * 
 * Appears at the bottom of the dashboard, showing live SSE events
 * from each agent (Visionary, Detective, Analyst, Decision) as they work.
 * 
 * Props:
 *   logs: Array of { agent, message, ts } objects
 *   isRunning: Boolean — whether the pipeline is currently executing
 *   onClear: Function — clears the log buffer
 */

const AGENT_COLORS = {
  'Visionary': 'text-blue-500',
  'Detective': 'text-amber-500',
  'Analyst':   'text-violet-500',
  'Decision':  'text-primary',
  'Visualizer':'text-pink-400',
  'System':    'text-slate-400',
};

const AGENT_ICONS = {
  'Visionary': '👁️',
  'Detective': '🔍',
  'Analyst':   '🧠',
  'Decision':  '✅',
  'Visualizer':'🎨',
  'System':    '⚙️',
};

const AgentTerminal = ({ logs = [], isRunning = false, onClear }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const scrollRef = useRef(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (scrollRef.current && isExpanded) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, isExpanded]);

  // Auto-expand when pipeline starts
  useEffect(() => {
    if (isRunning) setIsExpanded(true);
  }, [isRunning]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="fixed bottom-6 right-6 z-50 w-[520px] overflow-hidden"
    >
      {/* Terminal Header */}
      <div 
        className="flex items-center justify-between px-4 py-3 bg-slate-900 border border-slate-700 rounded-t-xl cursor-pointer select-none"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-accent-rose/80" />
            <div className="w-3 h-3 rounded-full bg-accent-amber/80" />
            <div className="w-3 h-3 rounded-full bg-primary/80" />
          </div>
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
              Agent Pipeline
            </span>
          </div>
          {isRunning && (
            <motion.div 
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="flex items-center gap-1.5 ml-2"
            >
              <div className="w-2 h-2 rounded-full bg-primary" />
              <span className="text-[10px] text-primary font-bold uppercase">Processing</span>
            </motion.div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {logs.length > 0 && (
            <button 
              onClick={(e) => { e.stopPropagation(); onClear?.(); }}
              className="text-slate-500 hover:text-slate-300 transition-colors p-1"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-slate-500" />
          ) : (
            <ChevronUp className="w-4 h-4 text-slate-500" />
          )}
        </div>
      </div>

      {/* Terminal Body */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            className="overflow-hidden"
          >
            <div 
              ref={scrollRef}
              className="bg-slate-950 border-x border-b border-slate-700 rounded-b-xl p-4 max-h-72 overflow-y-auto font-mono text-xs space-y-2.5 scrollbar-thin"
            >
              {logs.length === 0 ? (
                <div className="flex items-center justify-center py-8 text-slate-600">
                  <Cpu className="w-5 h-5 mr-2 opacity-50" />
                  <span>Waiting for pipeline activation...</span>
                </div>
              ) : (
                logs.map((log, i) => (
                  <motion.div 
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.2 }}
                    className="flex items-start gap-2 leading-relaxed"
                  >
                    <span className="text-slate-600 shrink-0 w-16 text-right">
                      {new Date(log.ts * 1000).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                    <span className="shrink-0">{AGENT_ICONS[log.agent] || '📋'}</span>
                    <span className={`font-bold shrink-0 ${AGENT_COLORS[log.agent] || 'text-slate-400'}`}>
                      [{log.agent}]
                    </span>
                    <span className="text-slate-300">{log.message}</span>
                  </motion.div>
                ))
              )}

              {/* Blinking cursor */}
              {isRunning && (
                <motion.span 
                  animate={{ opacity: [1, 0] }}
                  transition={{ duration: 0.8, repeat: Infinity }}
                  className="inline-block w-2 h-4 bg-primary ml-20"
                />
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default AgentTerminal;
