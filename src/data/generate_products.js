import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const generateProducts = () => {
  return [
    {
      "id": 1,
      "name": "Samsung Galaxy S25 Ultra 512 GB 12 GB Ram",
      "image": "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?auto=format&fit=crop&q=80&w=800",
      "description": "Samsung'un en yeni amiral gemisi Galaxy S25 Ultra, olağanüstü kamera yetenekleri, yapay zeka özellikleri ve muazzam performans sunuyor.",
      "specs": [
        { "label": "Ekran", "value": "6.8 inç Dynamic AMOLED 2X, 120Hz" },
        { "label": "İşlemci", "value": "Snapdragon 8 Gen 4 for Galaxy" },
        { "label": "RAM", "value": "12 GB" },
        { "label": "Depolama", "value": "512 GB" },
        { "label": "Kamera", "value": "200MP Ana + 50MP Periskop" },
        { "label": "Batarya", "value": "5000 mAh (45W Hızlı Şarj)" }
      ],
      "aiSummary": "Sektördeki en gelişmiş yapay zeka özellikleri ve kamera donanımı. Fiyat eğilimi stabil.",
      "strategy": "BEKLE",
      "stores": [
        {
          "name": "Amazon",
          "price": 2100,
          "rating": 4.9,
          "maxRating": 5,
          "pros": ["Hızlı Teslimat", "Güvenilir Satıcı"],
          "cons": ["Stok kısıtlı"],
          "url": "#"
        },
        {
          "name": "Hepsiburada",
          "price": 2150,
          "rating": 4.8,
          "maxRating": 5,
          "pros": ["Taksit seçenekleri"],
          "cons": ["Kargo süresi uzun"],
          "url": "#"
        }
      ]
    },
    {
      "id": 2,
      "name": "Samsung Galaxy S24 256 GB 8 GB Ram",
      "image": "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?auto=format&fit=crop&q=80&w=800",
      "description": "Kompakt tasarım ve güçlü performansı bir araya getiren Galaxy S24, günlük kullanım için mükemmel bir deneyim vadediyor.",
      "specs": [
        { "label": "Ekran", "value": "6.2 inç Dynamic AMOLED 2X, 120Hz" },
        { "label": "İşlemci", "value": "Exynos 2400" },
        { "label": "RAM", "value": "8 GB" },
        { "label": "Depolama", "value": "256 GB" },
        { "label": "Kamera", "value": "50MP Ana Kamera" },
        { "label": "Batarya", "value": "4000 mAh (25W Hızlı Şarj)" }
      ],
      "aiSummary": "Fiyat performans açısından ideal bir kompakt amiral gemisi.",
      "strategy": "AL",
      "stores": [
        {
          "name": "Trendyol",
          "price": 950,
          "rating": 4.7,
          "maxRating": 5,
          "pros": ["Uygun Fiyat", "Kupon Fırsatı"],
          "cons": ["Satıcı değerlendirmesi değişken"],
          "url": "#"
        }
      ]
    },
    {
      "id": 3,
      "name": "Apple Macbook Air M4 16 GB 512 GB SSD macOS 13\"",
      "image": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&q=80&w=800",
      "description": "Yeni M4 çipiyle donatılmış MacBook Air, inanılmaz ince tasarımıyla masaüstü sınıfı performansı her yere taşımanızı sağlar.",
      "specs": [
        { "label": "Ekran", "value": "13.6 inç Liquid Retina" },
        { "label": "İşlemci", "value": "Apple M4 Çip" },
        { "label": "RAM", "value": "16 GB Birleşik Bellek" },
        { "label": "Depolama", "value": "512 GB SSD" },
        { "label": "İşletim Sistemi", "value": "macOS" },
        { "label": "Batarya", "value": "18 Saate Kadar" }
      ],
      "aiSummary": "Uzun pil ömrü ve yüksek performans isteyen profesyoneller için ideal seçim.",
      "strategy": "AL",
      "stores": [
        {
          "name": "Apple Store",
          "price": 1499,
          "rating": 5.0,
          "maxRating": 5,
          "pros": ["Orijinal Satıcı", "Eğitim İndirimi"],
          "cons": ["İndirim nadir"],
          "url": "#"
        }
      ]
    },
    {
      "id": 4,
      "name": "Apple iPhone 15 128 GB Mavi",
      "image": "https://images.unsplash.com/photo-1695048133142-1a20484d2569?auto=format&fit=crop&q=80&w=800",
      "description": "Dynamic Island, 48MP Ana kamera ve USB-C ile yenilenen iPhone 15, göz alıcı renk seçenekleriyle öne çıkıyor.",
      "specs": [
        { "label": "Ekran", "value": "6.1 inç Super Retina XDR" },
        { "label": "İşlemci", "value": "A16 Bionic Çip" },
        { "label": "Depolama", "value": "128 GB" },
        { "label": "Kamera", "value": "48MP Gelişmiş Çift Kamera" },
        { "label": "Bağlantı", "value": "USB-C" },
        { "label": "Renk", "value": "Mavi" }
      ],
      "aiSummary": "Fiyatı sabitlendi, eski nesilden geçiş yapmak için mantıklı bir seçenek.",
      "strategy": "BEKLE",
      "stores": [
        {
          "name": "Amazon",
          "price": 799,
          "rating": 4.8,
          "maxRating": 5,
          "pros": ["Güvenilir Kargo"],
          "cons": ["Renk seçeneği stokta az"],
          "url": "#"
        }
      ]
    },
    {
      "id": 5,
      "name": "Samsung Galaxy Tab S11 Ultra 12GB 256GB SM-X930",
      "image": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&q=80&w=800",
      "description": "Geniş ekranı ve üretkenlik özellikleriyle sınırları zorlayan yeni nesil premium tablet deneyimi.",
      "specs": [
        { "label": "Ekran", "value": "14.6 inç Dynamic AMOLED 2X" },
        { "label": "İşlemci", "value": "Snapdragon 8 Gen 3" },
        { "label": "RAM", "value": "12 GB" },
        { "label": "Depolama", "value": "256 GB" },
        { "label": "Aksesuarlar", "value": "S Pen Dahil" },
        { "label": "Model", "value": "SM-X930 (Wi-Fi)" }
      ],
      "aiSummary": "Üretkenlik ve medya tüketimi için rakipsiz bir ekran ve donanım sunuyor.",
      "strategy": "KAÇIN",
      "stores": [
        {
          "name": "Vatan Bilgisayar",
          "price": 1200,
          "rating": 4.6,
          "maxRating": 5,
          "pros": ["Mağazadan teslim", "Garanti avantajı"],
          "cons": ["Online fiyat rekabetçi değil"],
          "url": "#"
        }
      ]
    }
  ];
};

const fileContent = `// Auto-generated 5 products
export const sampleProducts = ${JSON.stringify(generateProducts(), null, 2)};
`;
fs.writeFileSync(path.join(__dirname, 'products.js'), fileContent);
console.log('5 UNIQUE products generated successfully!');
