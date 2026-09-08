import { Hourglass } from "lucide-react";

export default function ComingSoon({ title }) {
  return (
    <div data-testid="coming-soon-page" className="card-soft p-12 flex flex-col items-center text-center">
      <div className="w-14 h-14 rounded-2xl bg-purple-50 text-purple-600 flex items-center justify-center mb-4">
        <Hourglass className="w-6 h-6" />
      </div>
      <h1 className="text-xl font-bold text-slate-900 mb-2">{title}</h1>
      <p className="text-sm text-slate-500 max-w-sm">Este módulo faz parte das próximas fases do Robson Club e será desbloqueado em breve.</p>
    </div>
  );
}
