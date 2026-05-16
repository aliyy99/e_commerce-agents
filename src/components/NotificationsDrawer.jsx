import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, BellOff, Clock, Trash2, X, CheckCheck, Sparkles } from 'lucide-react';

const TYPE_META = {
  'track-started': { icon: Bell, color: 'text-primary', bg: 'bg-primary/10' },
  'track-removed': { icon: BellOff, color: 'text-slate-600', bg: 'bg-slate-100' },
  'track-expired': { icon: Clock, color: 'text-rose-500', bg: 'bg-rose-50' },
};

const formatRelative = (ts) => {
  const diff = Date.now() - ts;
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return 'just now';
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min} min ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} hr ago`;
  const day = Math.floor(hr / 24);
  return `${day}d ago`;
};

const NotificationsDrawer = ({ isOpen, notifications, onClose, onMarkAllRead, onClearAll, onRemove }) => {
  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[90]">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-slate-900/30 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.aside
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 320, damping: 32 }}
            className="absolute top-0 right-0 h-full w-full sm:w-[420px] bg-white shadow-2xl flex flex-col"
          >
            <div className="flex items-center justify-between p-6 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
                  <Bell className="w-5 h-5 fill-current" />
                </div>
                <div>
                  <h3 className="text-lg font-black text-slate-900">Notifications</h3>
                  <p className="text-xs font-medium text-slate-500">
                    {unreadCount > 0 ? `${unreadCount} unread` : 'All caught up'}
                  </p>
                </div>
              </div>
              <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-full transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            {notifications.length > 0 && (
              <div className="flex items-center gap-2 px-6 py-3 border-b border-slate-100 bg-slate-50/50">
                <button
                  onClick={onMarkAllRead}
                  disabled={unreadCount === 0}
                  className="flex items-center gap-1.5 text-xs font-bold text-slate-600 hover:text-primary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                  Mark all as read
                </button>
                <div className="flex-1" />
                <button
                  onClick={onClearAll}
                  className="flex items-center gap-1.5 text-xs font-bold text-slate-600 hover:text-rose-500 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Clear all
                </button>
              </div>
            )}

            <div className="flex-1 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center px-6">
                  <div className="w-20 h-20 rounded-full bg-slate-50 flex items-center justify-center mb-4">
                    <Sparkles className="w-8 h-8 text-slate-300" />
                  </div>
                  <h4 className="text-base font-black text-slate-900 mb-1">No notifications yet</h4>
                  <p className="text-xs text-slate-500 max-w-[220px]">
                    When you track a product or its tracking expires, you'll see it here.
                  </p>
                </div>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {notifications.map(n => {
                    const meta = TYPE_META[n.type] ?? TYPE_META['track-started'];
                    const Icon = meta.icon;
                    return (
                      <li
                        key={n.id}
                        className={`group flex gap-3 px-6 py-4 transition-colors ${n.read ? 'bg-white' : 'bg-primary/5'}`}
                      >
                        <div className={`w-10 h-10 rounded-xl ${meta.bg} ${meta.color} flex items-center justify-center flex-shrink-0`}>
                          <Icon className="w-4 h-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <p className="text-sm font-bold text-slate-900 leading-tight">{n.title}</p>
                            {!n.read && <span className="w-2 h-2 bg-primary rounded-full flex-shrink-0 mt-1.5" />}
                          </div>
                          <p className="text-xs text-slate-600 mt-1 leading-relaxed">{n.message}</p>
                          <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mt-2">{formatRelative(n.createdAt)}</p>
                        </div>
                        <button
                          onClick={() => onRemove(n.id)}
                          className="opacity-0 group-hover:opacity-100 text-slate-300 hover:text-rose-500 transition-all self-start"
                          aria-label="Delete notification"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </motion.aside>
        </div>
      )}
    </AnimatePresence>
  );
};

export default NotificationsDrawer;
