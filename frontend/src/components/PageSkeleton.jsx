export const PageSkeleton = () => (
  <div className="space-y-6 animate-pulse" data-testid="page-skeleton">
    <div className="h-8 w-64 bg-slate-200 rounded-lg" />
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      {[0, 1, 2, 3].map((i) => <div key={i} className="h-32 bg-white rounded-2xl border border-slate-100" />)}
    </div>
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
      <div className="h-72 bg-white rounded-2xl border border-slate-100 xl:col-span-2" />
      <div className="h-72 bg-white rounded-2xl border border-slate-100" />
    </div>
  </div>
);
