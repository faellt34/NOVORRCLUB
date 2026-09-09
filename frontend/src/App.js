import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AppProvider, useApp } from "@/context/AppContext";
import AppLayout from "@/components/layout/AppLayout";
import Login from "@/pages/Login";
import InfluencerDashboard from "@/pages/InfluencerDashboard";
import PartnerDashboard from "@/pages/PartnerDashboard";
import AdminDashboard from "@/pages/AdminDashboard";
import AdminManage from "@/pages/AdminManage";
import Statement from "@/pages/Statement";
import Ebooks from "@/pages/Ebooks";
import Messages from "@/pages/Messages";
import Notifications from "@/pages/Notifications";
import PaymentResult from "@/pages/PaymentResult";
import AdminPayouts from "@/pages/AdminPayouts";
import { ForgotPassword, ResetPassword } from "@/pages/PasswordRecovery";

const ROLE_HOME = { influencer: "/influencer", partner: "/parceiro", admin: "/admin" };

const Splash = () => (
  <div className="min-h-screen flex items-center justify-center bg-[#F8F9FC]" data-testid="auth-loading">
    <div className="w-10 h-10 rounded-full border-4 border-purple-200 border-t-purple-600 animate-spin" />
  </div>
);

const RoleRedirect = () => {
  const { user } = useApp();
  return <Navigate to={ROLE_HOME[user.role]} replace />;
};

const Protected = ({ roles }) => {
  const { user } = useApp();
  if (user === undefined) return <Splash />;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to={ROLE_HOME[user.role]} replace />;
  return <Outlet />;
};

const PublicOnly = () => {
  const { user } = useApp();
  if (user === undefined) return <Splash />;
  if (user) return <Navigate to={ROLE_HOME[user.role]} replace />;
  return <Outlet />;
};

function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<PublicOnly />}>
            <Route path="/login" element={<Login />} />
            <Route path="/esqueci-password" element={<ForgotPassword />} />
            <Route path="/redefinir-password" element={<ResetPassword />} />
          </Route>
          <Route element={<Protected />}>
            <Route element={<AppLayout />}>
              <Route path="/" element={<RoleRedirect />} />
              <Route path="/payment/success" element={<PaymentResult />} />
              <Route path="/payment/cancel" element={<PaymentResult cancelled />} />
              <Route path="/mensagens" element={<Messages />} />
              <Route path="/notificacoes" element={<Notifications />} />
              <Route path="/ebooks" element={<Ebooks />} />
              <Route element={<Protected roles={["influencer"]} />}>
                <Route path="/influencer" element={<InfluencerDashboard />} />
                <Route path="/influencer/extrato" element={<Statement />} />
              </Route>
              <Route element={<Protected roles={["partner"]} />}>
                <Route path="/parceiro" element={<PartnerDashboard />} />
              </Route>
              <Route element={<Protected roles={["admin"]} />}>
                <Route path="/admin" element={<AdminDashboard />} />
                <Route path="/admin/gestao" element={<AdminManage />} />
                <Route path="/admin/pagamentos" element={<AdminPayouts />} />
              </Route>
              <Route path="*" element={<RoleRedirect />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AppProvider>
  );
}

export default App;
