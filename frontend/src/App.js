import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AppProvider, useApp } from "@/context/AppContext";
import AppLayout from "@/components/layout/AppLayout";
import InfluencerDashboard from "@/pages/InfluencerDashboard";
import PartnerDashboard from "@/pages/PartnerDashboard";
import AdminDashboard from "@/pages/AdminDashboard";
import AdminManage from "@/pages/AdminManage";
import Statement from "@/pages/Statement";
import Ebooks from "@/pages/Ebooks";
import ComingSoon from "@/pages/ComingSoon";

const ROLE_HOME = { influencer: "/influencer", partner: "/parceiro", admin: "/admin" };

const RoleRedirect = () => {
  const { role } = useApp();
  return <Navigate to={ROLE_HOME[role]} replace />;
};

function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<RoleRedirect />} />
            <Route path="/influencer" element={<InfluencerDashboard />} />
            <Route path="/influencer/extrato" element={<Statement />} />
            <Route path="/parceiro" element={<PartnerDashboard />} />
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/gestao" element={<AdminManage />} />
            <Route path="/mensagens" element={<ComingSoon title="Mensagens" />} />
            <Route path="/ebooks" element={<Ebooks />} />
            <Route path="*" element={<RoleRedirect />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AppProvider>
  );
}

export default App;
