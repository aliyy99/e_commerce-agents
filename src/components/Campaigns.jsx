import React from 'react';
import { motion } from 'framer-motion';
import { Tag, Ticket, BellRing, Copy, Check } from 'lucide-react';

const Campaigns = () => {
  const [copiedId, setCopiedId] = React.useState(null);

  const copyToClipboard = (id, code) => {
    navigator.clipboard.writeText(code);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const campaigns = [
    {
      id: 1,
      type: 'coupon',
      title: 'Tech Festival Sale',
      description: 'Instant 15% discount on selected tech products. Weekend only.',
      code: 'TECHFEST15',
      expire: '2 days left'
    },
    {
      id: 2,
      type: 'coupon',
      title: 'First Purchase Special',
      description: '$50 discount valid on your first electronics purchase via SHOPSAGE.AI.',
      code: 'SAGE50',
      expire: '7 days left'
    },
    {
      id: 3,
      type: 'news',
      title: 'Apple Education Sales Started',
      description: 'Special pricing and free AirPods for university students and teachers on Mac and iPad models. Limited stock.',
      date: 'Today'
    },
    {
      id: 4,
      type: 'news',
      title: 'Samsung Unpacked Event',
      description: 'Announcements about next-gen foldable devices and AI integration coming soon. Don\'t miss event-day pre-order benefits.',
      date: 'Tomorrow'
    }
  ];

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 bg-primary/10 text-primary rounded-xl flex items-center justify-center">
          <Tag className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-3xl font-display font-black text-slate-900">Campaigns and Coupons</h2>
          <p className="text-slate-500 mt-1 text-sm">Latest deals, discount codes, and industry news.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Coupons Column */}
        <div className="space-y-6">
          <h3 className="font-bold text-slate-900 flex items-center gap-2">
            <Ticket className="w-5 h-5 text-accent-rose" />
            Discount Coupons
          </h3>
          {campaigns.filter(c => c.type === 'coupon').map((coupon) => (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              key={coupon.id} 
              className="glass-card p-6 bg-white border-slate-100 flex flex-col justify-between"
            >
              <div>
                <div className="flex justify-between items-start mb-2">
                  <h4 className="text-lg font-black text-slate-900">{coupon.title}</h4>
                  <span className="text-[10px] font-bold px-2 py-1 bg-red-50 text-red-600 rounded uppercase tracking-widest">{coupon.expire}</span>
                </div>
                <p className="text-sm text-slate-500 mb-6">{coupon.description}</p>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-200 border-dashed">
                <span className="font-mono font-bold text-slate-700 tracking-wider">{coupon.code}</span>
                <button 
                  onClick={() => copyToClipboard(coupon.id, coupon.code)}
                  className="p-2 bg-white rounded-lg shadow-sm text-slate-400 hover:text-primary transition-colors border border-slate-100"
                  title="Copy Code"
                >
                  {copiedId === coupon.id ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            </motion.div>
          ))}
        </div>

        {/* News Column */}
        <div className="space-y-6">
          <h3 className="font-bold text-slate-900 flex items-center gap-2">
            <BellRing className="w-5 h-5 text-primary" />
            Special Discount News
          </h3>
          {campaigns.filter(c => c.type === 'news').map((news) => (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              key={news.id} 
              className="glass-card p-6 bg-white border-slate-100 relative overflow-hidden"
            >
              <div className="absolute top-0 left-0 w-1 h-full bg-primary/20"></div>
              <div className="flex justify-between items-start mb-2">
                <h4 className="text-lg font-black text-slate-900">{news.title}</h4>
                <span className="text-[10px] font-bold text-slate-400 uppercase">{news.date}</span>
              </div>
              <p className="text-sm text-slate-500 leading-relaxed">{news.description}</p>
              <button className="mt-4 text-xs font-black text-primary uppercase tracking-widest hover:underline">
                View Details
              </button>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Campaigns;
