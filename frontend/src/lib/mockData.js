export const USERS = {
  influencer: {
    id: "inf-1",
    role: "influencer",
    name: "Robson Oliveira",
    firstName: "Robson",
    handle: "@robson.luxe",
    avatar: "https://i.pravatar.cc/80?img=12",
    label: "Influencer",
  },
  partner: {
    id: "par-1",
    role: "partner",
    name: "Tivoli Sky Bar Lisboa",
    firstName: "Tivoli Sky Bar",
    handle: "Rooftop · Lisboa",
    avatar: "https://i.pravatar.cc/80?img=68",
    label: "Parceiro",
  },
  admin: {
    id: "adm-1",
    role: "admin",
    name: "Admin Geral",
    firstName: "Admin",
    handle: "admin@robson.club",
    avatar: "https://i.pravatar.cc/80?img=33",
    label: "Admin",
  },
};

export const PARTNERS = [
  { id: "p1", name: "Tivoli Sky Bar", category: "Rooftop", city: "Lisboa", avatar: "https://i.pravatar.cc/64?img=68", uses: 392, revenue: 42180 },
  { id: "p2", name: "Belcanto", category: "Restaurante", city: "Lisboa", avatar: "https://i.pravatar.cc/64?img=59", uses: 286, revenue: 31240 },
  { id: "p3", name: "The Yeatman", category: "Hotel", city: "Porto", avatar: "https://i.pravatar.cc/64?img=15", uses: 214, revenue: 24890 },
  { id: "p4", name: "Vila Vita Parc", category: "Hotel", city: "Algarve", avatar: "https://i.pravatar.cc/64?img=5", uses: 168, revenue: 19430 },
  { id: "p5", name: "Quinta do Crasto", category: "Passeio", city: "Douro", avatar: "https://i.pravatar.cc/64?img=22", uses: 124, revenue: 11260 },
];

export const CAMPAIGNS = [
  { id: "c1", name: "Sunset Sessions Verão", partnerId: "p1", partner: "Tivoli Sky Bar", city: "Lisboa", category: "Rooftop", coupon: "ROBSON-LUXE-25", discountPct: 15, commissionRate: 0.10, uses: 392, revenue: 42180, validUntil: "2026-09-30", status: "Ativa" },
  { id: "c2", name: "Menu Degustação Estrela", partnerId: "p2", partner: "Belcanto", city: "Lisboa", category: "Restaurante", coupon: "ROBSON-BEL-10", discountPct: 10, commissionRate: 0.10, uses: 286, revenue: 31240, validUntil: "2026-08-15", status: "Ativa" },
  { id: "c3", name: "Wine Escape Porto", partnerId: "p3", partner: "The Yeatman", city: "Porto", category: "Hotel", coupon: "ROBSON-YEAT-20", discountPct: 20, commissionRate: 0.12, uses: 214, revenue: 24890, validUntil: "2026-07-31", status: "Ativa" },
  { id: "c4", name: "Algarve Golden Week", partnerId: "p4", partner: "Vila Vita Parc", city: "Algarve", category: "Hotel", coupon: "ROBSON-VITA-15", discountPct: 15, commissionRate: 0.10, uses: 168, revenue: 19430, validUntil: "2026-06-20", status: "Pausada" },
  { id: "c5", name: "Douro Harvest Tour", partnerId: "p5", partner: "Quinta do Crasto", city: "Douro", category: "Passeio", coupon: "ROBSON-DOURO-10", discountPct: 10, commissionRate: 0.08, uses: 124, revenue: 11260, validUntil: "2026-03-31", status: "Expirada" },
];

export const FEATURED_COUPON = {
  code: "ROBSON-LUXE-25",
  campaign: "Sunset Sessions Verão",
  partner: "Tivoli Sky Bar",
  discount: "15% OFF em experiências selecionadas",
  link: "https://robson.club/c/ROBSON-LUXE-25",
};

const gen = (days, base, spread) =>
  Array.from({ length: days }, (_, i) => {
    const d = new Date(2026, 5, 14 - (days - 1 - i));
    const wave = Math.sin(i / 2.6) * spread * 0.5 + Math.cos(i / 1.7) * spread * 0.3;
    return {
      label: d.toLocaleDateString("pt-PT", { day: "2-digit", month: "short" }),
      utilizacoes: Math.max(4, Math.round(base + wave + (i / days) * spread)),
    };
  });

export const CHART_DATA = {
  "7": gen(7, 48, 22),
  "30": gen(30, 42, 26),
  "90": gen(90, 36, 30).filter((_, i) => i % 3 === 0),
};

export const INFLUENCER_LEADERBOARD = [
  { id: "i1", name: "Robson Oliveira", handle: "@robson.luxe", avatar: "https://i.pravatar.cc/64?img=12", redemptions: 392, revenue: 42180, commission: 4218 },
  { id: "i2", name: "Marta Vasconcelos", handle: "@marta.lx", avatar: "https://i.pravatar.cc/64?img=45", redemptions: 218, revenue: 23410, commission: 2341 },
  { id: "i3", name: "Diogo Fontes", handle: "@diogo.eats", avatar: "https://i.pravatar.cc/64?img=53", redemptions: 154, revenue: 16820, commission: 1682 },
  { id: "i4", name: "Inês Castelo", handle: "@ines.castelo", avatar: "https://i.pravatar.cc/64?img=31", redemptions: 96, revenue: 10140, commission: 1014 },
];

export const INITIAL_REDEMPTIONS = [
  { id: "r-1006", coupon: "ROBSON-LUXE-25", influencer: "Robson Oliveira", amount: 186.5, discount: 27.98, commission: 18.65, rate: 0.10, date: "2026-06-14T20:42:00", staff: "Ana P." },
  { id: "r-1005", coupon: "ROBSON-LUXE-25", influencer: "Robson Oliveira", amount: 94.0, discount: 14.1, commission: 9.4, rate: 0.10, date: "2026-06-14T19:18:00", staff: "Ana P." },
  { id: "r-1004", coupon: "MARTA-SKY-10", influencer: "Marta Vasconcelos", amount: 132.0, discount: 13.2, commission: 13.2, rate: 0.10, date: "2026-06-13T22:05:00", staff: "João M." },
  { id: "r-1003", coupon: "ROBSON-LUXE-25", influencer: "Robson Oliveira", amount: 248.9, discount: 37.34, commission: 24.89, rate: 0.10, date: "2026-06-13T21:11:00", staff: "João M." },
  { id: "r-1002", coupon: "DIOGO-SKY-15", influencer: "Diogo Fontes", amount: 76.4, discount: 11.46, commission: 7.64, rate: 0.10, date: "2026-06-12T20:33:00", staff: "Ana P." },
  { id: "r-1001", coupon: "ROBSON-LUXE-25", influencer: "Robson Oliveira", amount: 158.0, discount: 23.7, commission: 15.8, rate: 0.10, date: "2026-06-12T19:47:00", staff: "Carla S." },
];

export const PARTNER_COUPONS = {
  "ROBSON-LUXE-25": { influencer: "Robson Oliveira", campaign: "Sunset Sessions Verão", discountPct: 15, commissionRate: 0.10, status: "Ativa" },
  "MARTA-SKY-10": { influencer: "Marta Vasconcelos", campaign: "Sky Nights", discountPct: 10, commissionRate: 0.10, status: "Ativa" },
  "DIOGO-SKY-15": { influencer: "Diogo Fontes", campaign: "Sky Nights", discountPct: 15, commissionRate: 0.10, status: "Ativa" },
  "ROBSON-DOURO-10": { influencer: "Robson Oliveira", campaign: "Douro Harvest Tour", discountPct: 10, commissionRate: 0.08, status: "Expirada" },
};

const IMG = {
  rooftop: "https://images.unsplash.com/photo-1786520403993-e1dfdc0864b5?crop=entropy&cs=srgb&fm=jpg&q=85&w=800",
  dish: "https://images.unsplash.com/photo-1786520403836-bbb95ed8904f?crop=entropy&cs=srgb&fm=jpg&q=85&w=800",
  porto: "https://images.unsplash.com/photo-1634057306449-51bc02166e3d?crop=entropy&cs=srgb&fm=jpg&q=85&w=800",
  hotel: "https://images.unsplash.com/photo-1589125753960-3793f25d50dc?crop=entropy&cs=srgb&fm=jpg&q=85&w=800",
};

export const EBOOKS = [
  { id: "e1", title: "Rooftops Secretos de Lisboa", region: "Lisboa", category: "Rooftops", premium: true, pages: 42, cover: IMG.rooftop, desc: "Os 12 rooftops com as melhores vistas e cocktails de autor da capital." },
  { id: "e2", title: "Guia Gastronómico Estrelado", region: "Lisboa", category: "Restaurantes", premium: false, pages: 36, cover: IMG.dish, desc: "Menus de degustação imperdíveis, do Chiado a Belém." },
  { id: "e3", title: "Porto Boutique & Heritage", region: "Porto", category: "Hotéis", premium: true, pages: 54, cover: IMG.porto, desc: "Hotéis-palacete e quartos com vista para o Douro." },
  { id: "e4", title: "Wine Bars da Ribeira", region: "Porto", category: "Restaurantes", premium: false, pages: 28, cover: IMG.dish, desc: "Onde provar os melhores Vinhos do Porto junto ao rio." },
  { id: "e5", title: "Resorts Escondidos do Algarve", region: "Algarve", category: "Hotéis", premium: true, pages: 48, cover: IMG.hotel, desc: "Luxo discreto entre falésias, dos Salgados à Ponta da Piedade." },
  { id: "e6", title: "Sunset Spots do Algarve", region: "Algarve", category: "Rooftops", premium: false, pages: 22, cover: IMG.rooftop, desc: "Terraços e beach clubs para o pôr do sol perfeito." },
  { id: "e7", title: "Douro: Quintas & Vindimas", region: "Douro", category: "Passeios", premium: true, pages: 60, cover: IMG.porto, desc: "Roteiro completo de quintas, provas e cruzeiros privados." },
  { id: "e8", title: "Hotéis com Azulejo & História", region: "Lisboa", category: "Hotéis", premium: true, pages: 38, cover: IMG.hotel, desc: "Dormir em fachadas pombalinas restauradas ao detalhe." },
];

export const EBOOK_REGIONS = ["Todas", "Lisboa", "Porto", "Algarve", "Douro"];
export const EBOOK_CATEGORIES = ["Todas", "Restaurantes", "Hotéis", "Rooftops", "Passeios"];

export const STATEMENT_MONTHS = [
  {
    id: "2026-06", label: "Junho 2026", status: "Pendente",
    lines: [
      { campaign: "Sunset Sessions Verão", partner: "Tivoli Sky Bar", uses: 148, revenue: 16240, rate: 0.10 },
      { campaign: "Menu Degustação Estrela", partner: "Belcanto", uses: 96, revenue: 10480, rate: 0.10 },
      { campaign: "Wine Escape Porto", partner: "The Yeatman", uses: 71, revenue: 8290, rate: 0.12 },
    ],
  },
  {
    id: "2026-05", label: "Maio 2026", status: "Pago", paidAt: "2026-06-05",
    lines: [
      { campaign: "Sunset Sessions Verão", partner: "Tivoli Sky Bar", uses: 132, revenue: 14380, rate: 0.10 },
      { campaign: "Menu Degustação Estrela", partner: "Belcanto", uses: 104, revenue: 11120, rate: 0.10 },
      { campaign: "Algarve Golden Week", partner: "Vila Vita Parc", uses: 88, revenue: 9840, rate: 0.10 },
      { campaign: "Wine Escape Porto", partner: "The Yeatman", uses: 63, revenue: 7110, rate: 0.12 },
    ],
  },
  {
    id: "2026-04", label: "Abril 2026", status: "Pago", paidAt: "2026-05-05",
    lines: [
      { campaign: "Sunset Sessions Verão", partner: "Tivoli Sky Bar", uses: 112, revenue: 12060, rate: 0.10 },
      { campaign: "Douro Harvest Tour", partner: "Quinta do Crasto", uses: 58, revenue: 5240, rate: 0.08 },
      { campaign: "Menu Degustação Estrela", partner: "Belcanto", uses: 91, revenue: 9630, rate: 0.10 },
    ],
  },
];

export const ADMIN_SEED = {
  usuarios: [
    { id: "u1", nome: "Robson Oliveira", email: "robson@robson.club", papel: "Influencer", status: "Ativo" },
    { id: "u2", nome: "Marta Vasconcelos", email: "marta@robson.club", papel: "Influencer", status: "Ativo" },
    { id: "u3", nome: "Tivoli Sky Bar", email: "gerencia@tivolisky.pt", papel: "Parceiro", status: "Ativo" },
    { id: "u4", nome: "Admin Geral", email: "admin@robson.club", papel: "Admin", status: "Ativo" },
  ],
  influencers: [
    { id: "if1", nome: "Robson Oliveira", handle: "@robson.luxe", cidade: "Lisboa", status: "Ativo" },
    { id: "if2", nome: "Marta Vasconcelos", handle: "@marta.lx", cidade: "Lisboa", status: "Ativo" },
    { id: "if3", nome: "Diogo Fontes", handle: "@diogo.eats", cidade: "Porto", status: "Ativo" },
    { id: "if4", nome: "Inês Castelo", handle: "@ines.castelo", cidade: "Algarve", status: "Suspenso" },
  ],
  parceiros: PARTNERS.map((p) => ({ id: p.id, nome: p.name, categoria: p.category, cidade: p.city, status: "Ativo" })),
  campanhas: CAMPAIGNS.map((c) => ({ id: c.id, nome: c.name, parceiro: c.partner, cupom: c.coupon, desconto: String(c.discountPct), comissao: String(c.commissionRate * 100), validade: c.validUntil, status: c.status })),
};

export const eur = (v) =>
  new Intl.NumberFormat("pt-PT", { style: "currency", currency: "EUR", maximumFractionDigits: v % 1 === 0 ? 0 : 2 }).format(v);

export const num = (v) => new Intl.NumberFormat("pt-PT").format(v);
