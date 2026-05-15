import React from 'react';
import { motion } from 'framer-motion';
import { Cpu, Search, BarChart3, Sparkles } from 'lucide-react';

/**
 * PipelineLoader — Creative loading animation shown while agents work.
 * Displays the pipeline stages with animated progress indicators.
 * 
 * Props:
 *   currentAgent: string — Which agent is currently active
 *   message: string — Status message from the agent
 */

const stages = [
  { id: 'Visionary', label: 'Vision Agent', sub: 'Gemini 3 Flash', icon: Cpu, color: 'text-blue-500 bg-blue-500' },
  { id: 'Detective', label: 'Detective Agent', sub: 'Search Engine', icon: Search, color: 'text-amber-500 bg-amber-500' },
  { id: 'Analyst', label: 'Analyst Agent', sub: 'Gemini 2.5 Flash', icon: BarChart3, color: 'text-violet-500 bg-violet-500' },
  { id: 'Decision', label: 'Final Decision', sub: 'Recommendation', icon: Sparkles, color: 'text-primary bg-primary' },
];

const PipelineLoader = ({ currentAgent = '', message = '' }) => {
  const currentIndex = stages.findIndex(s => s.id === currentAgent);

  return (
    <div className="w-full glass-card p-10 bg-white border-slate-100">
      {/* Header */}
      <div className="text-center mb-10">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          className="w-12 h-12 mx-auto mb-4 border-2 border-slate-200 border-t-primary rounded-full"
        />
        <h3 className="text-xl font-display font-black text-slate-900 mb-2">
          Agents are negotiating for you...
        </h3>
        <p className="text-sm text-slate-500">{message || 'Starting pipeline...'}</p>
      </div>

      {/* Pipeline Progress */}
      <div className="flex items-center justify-between max-w-lg mx-auto">
        {stages.map((stage, i) => {
          const isCompleted = i < currentIndex;
          const isActive = i === currentIndex;
          const isPending = i > currentIndex;
          const Icon = stage.icon;

          return (
            <React.Fragment key={stage.id}>
              <div className="flex flex-col items-center gap-2 relative">
                <motion.div 
                  animate={isActive ? { scale: [1, 1.15, 1] } : {}}
                  transition={{ duration: 1, repeat: Infinity }}
                  className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${
                    isCompleted 
                      ? `${stage.color.split(' ')[1]}/10 border border-${stage.color.split(' ')[0].replace('text-','')}/20` 
                      : isActive 
                        ? `${stage.color.split(' ')[1]}/20 border-2 border-${stage.color.split(' ')[0].replace('text-','')}/40 shadow-lg`
                        : 'bg-slate-100 border border-slate-200'
                  }`}
                >
                  <Icon className={`w-5 h-5 ${isCompleted || isActive ? stage.color.split(' ')[0] : 'text-slate-300'}`} />
                </motion.div>
                <span className={`text-[10px] font-bold uppercase tracking-wider ${isActive ? 'text-slate-900' : 'text-slate-400'}`}>
                  {stage.label}
                </span>
                <span className={`text-[9px] ${isActive ? stage.color.split(' ')[0] : 'text-slate-300'}`}>
                  {stage.sub}
                </span>

                {/* Active pulse ring */}
                {isActive && (
                  <motion.div 
                    animate={{ scale: [1, 1.6], opacity: [0.4, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                    className={`absolute -top-1 w-14 h-14 rounded-xl ${stage.color.split(' ')[1]}/10 border border-${stage.color.split(' ')[0].replace('text-','')}/20`}
                  />
                )}
              </div>

              {/* Connector line */}
              {i < stages.length - 1 && (
                <div className="flex-1 h-0.5 mx-2 bg-slate-100 rounded-full overflow-hidden relative -mt-8">
                  <motion.div 
                    className={`h-full ${isCompleted ? stage.color.split(' ')[1] : 'bg-slate-200'}`}
                    initial={{ width: '0%' }}
                    animate={{ width: isCompleted ? '100%' : isActive ? '50%' : '0%' }}
                    transition={{ duration: 0.8 }}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Skeleton preview of what will load */}
      <div className="mt-10 grid grid-cols-12 gap-4 opacity-30">
        <div className="col-span-4 h-32 skeleton rounded-xl" />
        <div className="col-span-4 h-32 skeleton rounded-xl" />
        <div className="col-span-4 h-32 skeleton rounded-xl" />
      </div>
    </div>
  );
};

export default PipelineLoader;
