import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, Send, X, Bot, User, Loader2, Sparkles } from 'lucide-react';
import { chatWithAssistant } from '../services/api';

const ChatWidget = ({ contextProduct }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Merhaba! 👋 Ben ShopSage AI, kişisel alışveriş asistanınızım. Ürünler hakkında fiyat karşılaştırması, teknik detaylar ve alım tavsiyeleri konusunda size yardımcı olabilirim. Nasıl yardımcı olabilirim?" }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  // When product context changes, send an informational message
  useEffect(() => {
    if (contextProduct) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `📦 "${contextProduct.name}" ürünü hakkında bilgi almak ister misiniz? Fiyat karşılaştırması, teknik özellikler veya alım tavsiyesi sorun!` }
      ]);
    }
  }, [contextProduct?.id]);

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setInputValue('');
    setIsLoading(true);

    try {
      const { reply } = await chatWithAssistant({
        history: messages,
        userMessage,
        contextData: contextProduct,
      });
      setMessages(prev => [...prev, { role: 'assistant', content: reply }]);
    } catch (err) {
      console.error('Backend chat error:', err);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `Üzgünüm, bir hata oluştu: ${err.message}. Lütfen tekrar deneyin.` 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClearChat = () => {
    setMessages([
      { role: 'assistant', content: "Sohbet temizlendi! 🧹 Size nasıl yardımcı olabilirim?" }
    ]);
  };

  return (
    <div className="fixed bottom-8 left-8 z-[60]">
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="mb-4 w-[400px] rounded-2xl overflow-hidden flex flex-col h-[520px] shadow-2xl shadow-primary/20 border border-slate-200 bg-white"
          >
            {/* Header */}
            <div className="p-4 bg-gradient-to-r from-primary to-emerald-600 flex items-center justify-between text-white">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-white/20 backdrop-blur rounded-xl">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-sm font-black tracking-tight">ShopSage AI</h3>
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 bg-green-300 rounded-full animate-pulse" />
                    <span className="text-[10px] text-white/80 font-medium">Powered by Gemini</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button 
                  onClick={handleClearChat} 
                  className="p-2 hover:bg-white/10 rounded-lg transition-all text-white/70 hover:text-white text-xs font-bold"
                  title="Sohbeti Temizle"
                >
                  Temizle
                </button>
                <button onClick={() => setIsOpen(false)} className="p-2 hover:bg-white/10 rounded-lg transition-all">
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Chat Content */}
            <div className="flex-1 p-4 space-y-4 overflow-y-auto bg-slate-50/50">
              {messages.map((msg, idx) => (
                <motion.div 
                  key={idx} 
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                  className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                >
                  <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${
                    msg.role === 'user' ? 'bg-slate-200 text-slate-600' : 'bg-primary/10 text-primary border border-primary/20'
                  }`}>
                    {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>
                  <div className={`max-w-[280px] p-3 text-[13px] leading-relaxed shadow-sm border ${
                    msg.role === 'user' 
                      ? 'bg-primary text-white rounded-2xl rounded-tr-sm border-primary/50' 
                      : 'bg-white text-slate-700 rounded-2xl rounded-tl-sm border-slate-100'
                  }`}>
                    {msg.content}
                  </div>
                </motion.div>
              ))}
              {isLoading && (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex gap-3"
                >
                  <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center text-primary flex-shrink-0 border border-primary/20">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="bg-white p-3 rounded-2xl rounded-tl-sm text-[13px] text-slate-500 shadow-sm border border-slate-100 flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    Düşünüyor...
                  </div>
                </motion.div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-3 bg-white border-t border-slate-100">
              {contextProduct && (
                <div className="mb-2 px-3 py-1.5 bg-primary/5 rounded-lg border border-primary/10 flex items-center gap-2">
                  <span className="text-[10px] text-primary font-bold truncate">📦 {contextProduct.name}</span>
                </div>
              )}
              <div className="relative flex items-center gap-2">
                <input 
                  type="text" 
                  placeholder="Ürünler hakkında bir şey sorun..." 
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="flex-1 bg-slate-100 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 outline-none focus:border-primary/50 transition-colors"
                  disabled={isLoading}
                />
                <button 
                  onClick={handleSend}
                  disabled={isLoading || !inputValue.trim()}
                  className="p-2.5 bg-primary rounded-xl text-white hover:bg-primary-hover transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating Button with Label */}
      <div className="flex flex-col items-start gap-2">
        <AnimatePresence>
          {!isOpen && (
            <motion.div
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              className="bg-slate-900 text-white px-4 py-2 rounded-xl shadow-lg text-xs font-bold whitespace-nowrap"
            >
              ✨ Your Smart Shopping Assistant
            </motion.div>
          )}
        </AnimatePresence>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setIsOpen(!isOpen)}
          className={`w-14 h-14 rounded-2xl flex items-center justify-center shadow-2xl transition-all relative group ${
            isOpen 
              ? 'bg-slate-200 text-slate-600 shadow-slate-200/40' 
              : 'bg-gradient-to-br from-primary to-emerald-600 text-white shadow-primary/40'
          }`}
        >
          {isOpen ? (
            <X className="w-6 h-6" />
          ) : (
            <>
              <MessageSquare className="w-6 h-6 group-hover:rotate-12 transition-transform" />
              <div className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-red-500 border-2 border-white rounded-full animate-pulse" />
            </>
          )}
        </motion.button>
      </div>
    </div>
  );
};

export default ChatWidget;
