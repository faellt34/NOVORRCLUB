import { Link } from "react-router-dom";
import { Crown, ArrowLeft, ShieldCheck } from "lucide-react";
import { useT } from "../context/I18nContext";

const CONTENT = {
  pt: {
    title: "Política de Privacidade", updated: "Última atualização: setembro de 2026",
    sections: [
      ["1. Quem somos", "O ןןClub é uma plataforma que liga influencers de experiências de luxo a parceiros (restaurantes, hotéis, rooftops e experiências) através de cupões e códigos QR. O responsável pelo tratamento dos dados é a administração do ןןClub, contactável através de faellt@gmail.com."],
      ["2. Dados que recolhemos", "Dados de conta (nome, email, palavra-passe encriptada, papel na plataforma); dados de atividade (redenções de cupões, valores de compra, comissões, mensagens internas, notificações, indicações de parceiros); dados de compra de e-books (processados pelo Stripe — não guardamos dados de cartão); registos técnicos (data/hora de acesso, endereço IP para proteção contra acessos abusivos) e um registo de auditoria imutável das operações relevantes."],
      ["3. Finalidades e base legal", "Utilizamos os dados para prestar o serviço contratado (execução de contrato): calcular e travar comissões, gerar extratos mensais, validar cupões, permitir a comunicação entre utilizadores, processar compras e subscrições e notificar eventos relevantes. Tratamos também dados por interesse legítimo (segurança, prevenção de fraude, auditoria) e para cumprir obrigações legais (faturação e contabilidade)."],
      ["4. Partilha com terceiros", "Stripe (pagamentos e subscrições), serviço de armazenamento de ficheiros (PDFs dos e-books), fornecedor de email transacional (recuperação de palavra-passe e notificações) e fornecedor de alojamento. Os parceiros veem apenas os dados necessários à validação de cupões e ao apuramento de comissões; os influencers veem apenas os seus próprios resultados. Não vendemos dados pessoais."],
      ["5. Conservação", "Os dados de conta são conservados enquanto a conta estiver ativa. Registos de redenções, extratos, pagamentos e auditoria são conservados pelo prazo legal aplicável à contabilidade (até 10 anos). Links de recuperação de palavra-passe expiram em 24 horas."],
      ["6. Os seus direitos (RGPD)", "Tem direito de acesso, retificação, apagamento, limitação, portabilidade e oposição, bem como de retirar o consentimento e de apresentar reclamação à CNPD (www.cnpd.pt). Para exercer estes direitos, contacte faellt@gmail.com."],
      ["7. Segurança", "Palavras-passe guardadas com bcrypt, sessões com tokens assinados (JWT), controlo de acesso por papel, bloqueio temporário após tentativas de login falhadas, comunicações cifradas (HTTPS) e registo de auditoria server-side."],
      ["8. Cookies", "Utilizamos apenas armazenamento técnico estritamente necessário para manter a sessão iniciada e a preferência de idioma. Não usamos cookies de publicidade."],
      ["9. Alterações", "Esta política pode ser atualizada. Notificaremos alterações relevantes na plataforma."],
    ],
  },
  en: {
    title: "Privacy Policy", updated: "Last updated: September 2026",
    sections: [
      ["1. Who we are", "ןןClub is a platform connecting luxury-experience influencers with partners (restaurants, hotels, rooftops and experiences) through coupons and QR codes. The data controller is the ןןClub administration, reachable at faellt@gmail.com."],
      ["2. Data we collect", "Account data (name, email, encrypted password, platform role); activity data (coupon redemptions, purchase amounts, commissions, internal messages, notifications, partner referrals); e-book purchase data (processed by Stripe — we never store card data); technical logs (access time, IP address for abuse protection) and an immutable audit log of relevant operations."],
      ["3. Purposes and legal basis", "We use data to provide the contracted service: compute and lock commissions, generate monthly statements, validate coupons, enable communication between users, process purchases and subscriptions and notify relevant events. We also process data under legitimate interest (security, fraud prevention, auditing) and to comply with legal obligations (invoicing and accounting)."],
      ["4. Sharing with third parties", "Stripe (payments and subscriptions), file storage provider (e-book PDFs), transactional email provider (password recovery and notifications) and hosting provider. Partners only see data needed to validate coupons and settle commissions; influencers only see their own results. We do not sell personal data."],
      ["5. Retention", "Account data is kept while the account is active. Redemption, statement, payment and audit records are kept for the legally applicable accounting period (up to 10 years). Password recovery links expire after 24 hours."],
      ["6. Your rights (GDPR)", "You have the right to access, rectify, erase, restrict, port and object, to withdraw consent and to lodge a complaint with the Portuguese supervisory authority (CNPD, www.cnpd.pt). Contact faellt@gmail.com to exercise them."],
      ["7. Security", "Passwords hashed with bcrypt, signed session tokens (JWT), role-based access control, temporary lockout after failed logins, encrypted transport (HTTPS) and a server-side audit log."],
      ["8. Cookies", "We only use strictly necessary technical storage to keep you signed in and remember your language. No advertising cookies."],
      ["9. Changes", "This policy may be updated. Relevant changes will be announced in the platform."],
    ],
  },
  es: {
    title: "Política de Privacidad", updated: "Última actualización: septiembre de 2026",
    sections: [
      ["1. Quiénes somos", "ןןClub es una plataforma que conecta influencers de experiencias de lujo con socios (restaurantes, hoteles, rooftops y experiencias) mediante cupones y códigos QR. El responsable del tratamiento es la administración de ןןClub, contactable en faellt@gmail.com."],
      ["2. Datos que recogemos", "Datos de cuenta (nombre, email, contraseña cifrada, rol); datos de actividad (canjes de cupones, importes, comisiones, mensajes internos, notificaciones, recomendaciones de socios); datos de compra de e-books (procesados por Stripe — no guardamos datos de tarjeta); registros técnicos (fecha/hora de acceso, dirección IP para protección frente a abusos) y un registro de auditoría inmutable."],
      ["3. Finalidades y base legal", "Usamos los datos para prestar el servicio contratado: calcular y bloquear comisiones, generar extractos mensuales, validar cupones, permitir la comunicación entre usuarios, procesar compras y suscripciones y notificar eventos relevantes. También por interés legítimo (seguridad, prevención de fraude, auditoría) y para cumplir obligaciones legales (facturación y contabilidad)."],
      ["4. Compartición con terceros", "Stripe (pagos y suscripciones), proveedor de almacenamiento de archivos (PDF de e-books), proveedor de email transaccional y proveedor de alojamiento. Los socios solo ven los datos necesarios para validar cupones y liquidar comisiones; los influencers solo ven sus propios resultados. No vendemos datos personales."],
      ["5. Conservación", "Los datos de cuenta se conservan mientras la cuenta esté activa. Los registros de canjes, extractos, pagos y auditoría se conservan durante el plazo legal contable (hasta 10 años). Los enlaces de recuperación de contraseña caducan a las 24 horas."],
      ["6. Sus derechos (RGPD)", "Tiene derecho de acceso, rectificación, supresión, limitación, portabilidad y oposición, a retirar el consentimiento y a reclamar ante la autoridad de control (CNPD, www.cnpd.pt). Contacte con faellt@gmail.com para ejercerlos."],
      ["7. Seguridad", "Contraseñas con bcrypt, tokens de sesión firmados (JWT), control de acceso por rol, bloqueo temporal tras intentos fallidos, cifrado HTTPS y registro de auditoría en el servidor."],
      ["8. Cookies", "Solo usamos almacenamiento técnico estrictamente necesario para mantener la sesión y el idioma. Sin cookies publicitarias."],
      ["9. Cambios", "Esta política puede actualizarse. Anunciaremos los cambios relevantes en la plataforma."],
    ],
  },
};

export default function Privacy() {
  const { lang } = useT();
  const c = CONTENT[lang] || CONTENT.pt;
  return (
    <div className="min-h-screen bg-[#F8F9FC] py-10 px-6">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center"><Crown className="w-5 h-5 text-white" /></div>
            <p className="font-display font-bold text-lg">ןןClub</p>
          </Link>
          <Link to="/" data-testid="privacy-back" className="inline-flex items-center gap-1.5 text-xs font-semibold text-purple-700 hover:underline"><ArrowLeft className="w-3.5 h-3.5" /> Voltar</Link>
        </div>
        <div className="card-soft p-8">
          <div className="flex items-center gap-3 mb-2"><ShieldCheck className="w-6 h-6 text-purple-600" /><h1 data-testid="privacy-title" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">{c.title}</h1></div>
          <p className="text-xs text-slate-400 mb-8">{c.updated}</p>
          <div className="space-y-6">
            {c.sections.map(([h, p]) => (
              <section key={h}><h2 className="text-base md:text-lg font-semibold text-slate-900 mb-1.5">{h}</h2><p className="text-sm text-slate-600 leading-relaxed">{p}</p></section>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
