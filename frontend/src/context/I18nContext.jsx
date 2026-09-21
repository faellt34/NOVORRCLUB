import { createContext, useContext, useMemo, useState } from "react";

export const LANGS = { pt: "Português", en: "English", es: "Español" };

const D = {
  pt: {
    dashboard: "Dashboard", campaigns: "Campanhas", statement: "Extrato Mensal", messages: "Mensagens", notifications: "Notificações", ebooks: "E-books & Guias",
    validate: "Validar Cupom", overview: "Visão Geral", manage: "Gestão", payouts: "Pagamentos", logout: "Terminar sessão", privacy: "Privacidade", suggest: "Sugerir melhoria",
    referTitle: "Indique um parceiro", referText: "Conhece um espaço premium? Ganhe bónus por indicação aprovada.", referNow: "Indicar agora",
    loginTitle: "Entrar na sua área", loginSub: "Aceda ao painel de Influencer, Parceiro ou Admin.", email: "Email", password: "Palavra-passe", enter: "Entrar", entering: "A entrar...",
    forgot: "Esqueci a palavra-passe", demo: "Contas de demonstração", demoHint: "Clique para preencher e entrar automaticamente.", welcome: "Bem-vindo",
    heroTag: "Plataforma de parcerias", heroTitle: "Influência que se converte em receita mensurável.", heroText: "Cupões, QR codes, validação em loja e comissões travadas por redenção — tudo com audit log server-side.",
    ebooksTitle: "E-books & Guias Premium", ebooksSub: "Guias curados de experiências de luxo em Portugal e no mundo — leia online após compra ou subscrição",
    subscribe: "Subscrever Premium", perMonth: "/mês — todos os guias", subActive: "Subscrição Premium ativa — todos os guias desbloqueados", cancelSub: "Cancelar subscrição", subEnds: "Termina em",
    buyFor: "Comprar por", readNow: "Ler agora", preview: "Pré-visualizar", pages: "páginas", pdfSoon: "PDF em breve", owned: "Adquirido", unlocked: "Desbloqueado", all: "Todas", allM: "Todos", noResults: "Nenhum guia encontrado para estes filtros.",
    downloadPdf: "Descarregar PDF", exportCsv: "Exportar CSV", suggestTitle: "Sugerir uma melhoria", suggestText: "A sua opinião ajuda a evoluir o RRclub. Diga-nos o que melhorar.", type: "Tipo", message: "Mensagem", send: "Enviar", sent: "Obrigado! Sugestão enviada à equipa.",
    language: "Idioma", installApp: "Instalar app", settings: "Definições", premium: "Premium", free: "Gratuito", region: "Região", country: "País",
  },
  en: {
    dashboard: "Dashboard", campaigns: "Campaigns", statement: "Monthly Statement", messages: "Messages", notifications: "Notifications", ebooks: "E-books & Guides",
    validate: "Validate Coupon", overview: "Overview", manage: "Management", payouts: "Payouts", logout: "Sign out", privacy: "Privacy", suggest: "Suggest improvement",
    referTitle: "Refer a partner", referText: "Know a premium venue? Earn a bonus for each approved referral.", referNow: "Refer now",
    loginTitle: "Sign in to your area", loginSub: "Access the Influencer, Partner or Admin panel.", email: "Email", password: "Password", enter: "Sign in", entering: "Signing in...",
    forgot: "Forgot password", demo: "Demo accounts", demoHint: "Click to fill in and sign in automatically.", welcome: "Welcome",
    heroTag: "Partnership platform", heroTitle: "Influence that converts into measurable revenue.", heroText: "Coupons, QR codes, in-venue validation and commissions locked per redemption — all with a server-side audit log.",
    ebooksTitle: "Premium E-books & Guides", ebooksSub: "Curated luxury experience guides in Portugal and worldwide — read online after purchase or subscription",
    subscribe: "Subscribe Premium", perMonth: "/month — all guides", subActive: "Premium subscription active — all guides unlocked", cancelSub: "Cancel subscription", subEnds: "Ends on",
    buyFor: "Buy for", readNow: "Read now", preview: "Preview", pages: "pages", pdfSoon: "PDF coming soon", owned: "Purchased", unlocked: "Unlocked", all: "All", allM: "All", noResults: "No guides found for these filters.",
    downloadPdf: "Download PDF", exportCsv: "Export CSV", suggestTitle: "Suggest an improvement", suggestText: "Your feedback helps RRclub evolve. Tell us what to improve.", type: "Type", message: "Message", send: "Send", sent: "Thank you! Suggestion sent to the team.",
    language: "Language", installApp: "Install app", settings: "Settings", premium: "Premium", free: "Free", region: "Region", country: "Country",
  },
  es: {
    dashboard: "Panel", campaigns: "Campañas", statement: "Extracto Mensual", messages: "Mensajes", notifications: "Notificaciones", ebooks: "E-books & Guías",
    validate: "Validar Cupón", overview: "Visión General", manage: "Gestión", payouts: "Pagos", logout: "Cerrar sesión", privacy: "Privacidad", suggest: "Sugerir mejora",
    referTitle: "Recomienda un socio", referText: "¿Conoces un espacio premium? Gana un bono por cada recomendación aprobada.", referNow: "Recomendar ahora",
    loginTitle: "Entrar en tu área", loginSub: "Accede al panel de Influencer, Socio o Admin.", email: "Email", password: "Contraseña", enter: "Entrar", entering: "Entrando...",
    forgot: "Olvidé la contraseña", demo: "Cuentas de demostración", demoHint: "Haz clic para rellenar y entrar automáticamente.", welcome: "Bienvenido",
    heroTag: "Plataforma de alianzas", heroTitle: "Influencia que se convierte en ingresos medibles.", heroText: "Cupones, códigos QR, validación en local y comisiones bloqueadas por canje — todo con registro de auditoría en el servidor.",
    ebooksTitle: "E-books & Guías Premium", ebooksSub: "Guías seleccionadas de experiencias de lujo en Portugal y el mundo — lee online tras la compra o suscripción",
    subscribe: "Suscribirse Premium", perMonth: "/mes — todas las guías", subActive: "Suscripción Premium activa — todas las guías desbloqueadas", cancelSub: "Cancelar suscripción", subEnds: "Termina el",
    buyFor: "Comprar por", readNow: "Leer ahora", preview: "Vista previa", pages: "páginas", pdfSoon: "PDF próximamente", owned: "Adquirido", unlocked: "Desbloqueado", all: "Todas", allM: "Todos", noResults: "No se encontraron guías para estos filtros.",
    downloadPdf: "Descargar PDF", exportCsv: "Exportar CSV", suggestTitle: "Sugerir una mejora", suggestText: "Tu opinión ayuda a que RRclub evolucione. Dinos qué mejorar.", type: "Tipo", message: "Mensaje", send: "Enviar", sent: "¡Gracias! Sugerencia enviada al equipo.",
    language: "Idioma", installApp: "Instalar app", settings: "Ajustes", premium: "Premium", free: "Gratis", region: "Región", country: "País",
  },
};

const CONTENT = {
  en: { Todas: "All", Todos: "All", Restaurantes: "Restaurants", Hotéis: "Hotels", Rooftops: "Rooftops", Passeios: "Tours", Restaurante: "Restaurant", Hotel: "Hotel", Rooftop: "Rooftop", Passeio: "Tour",
        Portugal: "Portugal", Espanha: "Spain", Itália: "Italy", França: "France", Emirados: "UAE", Lisboa: "Lisbon", Porto: "Porto", Algarve: "Algarve", Douro: "Douro", Madrid: "Madrid", Amalfi: "Amalfi", Paris: "Paris", Dubai: "Dubai", Outra: "Other",
        Ativa: "Active", Pausada: "Paused", Expirada: "Expired", Ativo: "Active", Pendente: "Pending", Suspenso: "Suspended", Pago: "Paid", Novo: "New", Aprovada: "Approved", Rejeitada: "Rejected" },
  es: { Todas: "Todas", Todos: "Todos", Restaurantes: "Restaurantes", Hotéis: "Hoteles", Rooftops: "Rooftops", Passeios: "Paseos", Restaurante: "Restaurante", Hotel: "Hotel", Rooftop: "Rooftop", Passeio: "Paseo",
        Portugal: "Portugal", Espanha: "España", Itália: "Italia", França: "Francia", Emirados: "Emiratos", Lisboa: "Lisboa", Porto: "Oporto", Algarve: "Algarve", Douro: "Duero", Madrid: "Madrid", Amalfi: "Amalfi", Paris: "París", Dubai: "Dubái", Outra: "Otra",
        Ativa: "Activa", Pausada: "Pausada", Expirada: "Expirada", Ativo: "Activo", Pendente: "Pendiente", Suspenso: "Suspendido", Pago: "Pagado", Novo: "Nuevo", Aprovada: "Aprobada", Rejeitada: "Rechazada" },
};

const I18nContext = createContext(null);

export const I18nProvider = ({ children }) => {
  const [lang, setLangState] = useState(() => localStorage.getItem("robson_lang") || "pt");
  const setLang = (l) => { localStorage.setItem("robson_lang", l); setLangState(l); };
  const value = useMemo(() => ({ lang, setLang, t: (k) => D[lang]?.[k] ?? D.pt[k] ?? k, tc: (v) => CONTENT[lang]?.[v] ?? v }), [lang]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
};

export const useT = () => useContext(I18nContext);
