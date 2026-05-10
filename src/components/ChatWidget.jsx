import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, Send, X, Bot, User } from 'lucide-react';

const ChatWidget = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="fixed bottom-8 right-8 z-50">
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: 20 }}
            className="mb-4 w-96 glass-card overflow-hidden flex flex-col h-[500px]"
          >
            {/* Header */}
            <div className="p-4 bg-primary flex items-center justify-between shadow-lg text-white">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-white/20 rounded-lg">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-sm font-bold">ShopSage Assistant</h3>
                  <div className="flex items-center gap-1">
                    <div className="w-1.5 h-1.5 bg-green-300 rounded-full animate-pulse" />
                    <span className="text-[10px] text-white/80">Online & Ready</span>
                  </div>
                </div>
              </div>
              <button onClick={() => setIsOpen(false)} className="p-2 hover:bg-white/10 rounded-lg transition-all">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Chat Content */}
            <div className="flex-1 p-4 space-y-4 overflow-y-auto bg-slate-50">
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary flex-shrink-0 border border-primary/20">
                  <Bot className="w-5 h-5" />
                </div>
                <div className="bg-white p-3 rounded-2xl rounded-tl-none text-sm text-slate-700 shadow-sm border border-slate-100">
                  Hello! I'm ShopSage. How can I help you with your shopping journey today?
                </div>
              </div>

              <div className="flex gap-3 flex-row-reverse">
                <div className="w-8 h-8 rounded-lg bg-slate-200 flex items-center justify-center text-slate-600 flex-shrink-0">
                  <User className="w-5 h-5" />
                </div>
                <div className="bg-primary p-3 rounded-2xl rounded-tr-none text-sm text-white shadow-md">
                  Compare MacBook Pro prices across major retailers.
                </div>
              </div>

              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary flex-shrink-0 border border-primary/20">
                  <Bot className="w-5 h-5" />
                </div>
                <div className="bg-white p-3 rounded-2xl rounded-tl-none text-sm text-slate-700 shadow-sm border border-slate-100">
                  Scanning... I've found prices ranging from $1,245.50 to $1,350.00. Check the analysis card for details!
                </div>
              </div>
            </div>

            {/* Input */}
            <div className="p-4 bg-white border-t border-slate-100">
              <div className="relative">
                <input 
                  type="text" 
                  placeholder="Ask a question..." 
                  className="input-glass w-full pr-12 text-sm"
                />
                <button className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-primary rounded-lg text-white hover:bg-primary-hover transition-all">
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(!isOpen)}
        className="w-16 h-16 bg-primary rounded-2xl flex items-center justify-center shadow-2xl shadow-primary/40 hover:bg-primary-hover transition-all relative group"
      >
        <MessageSquare className="w-8 h-8 text-white group-hover:rotate-12 transition-transform" />
        <div className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 border-2 border-white rounded-full" />
      </motion.button>
    </div>
  );
};

export default ChatWidget;
