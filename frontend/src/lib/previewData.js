// Contrato de dados EXCLUSIVO da demonstração. Nunca interpreta eventos demo como pagamentos.
export const DEMO_SOURCE = "local_demo";
export const DEMO_CAMPAIGN = "DEMO-INVERNO";
export const DEMO_STATUSES = Object.freeze({
  campaign: "campaign_created",
  share: "campaign_shared",
  scan: "qr_validated",
  checkout: "checkout_simulated",
});
export const initialDemoEvents = () => [
  ...["PT","BR"].map(country=>({id:"seed-campaign-"+country,operationId:"campaign-demo-inverno-"+country,eventType:DEMO_STATUSES.campaign,role:"influencer",label:"Campanha DEMO-INVERNO criada",status:"Demonstração",country,source:DEMO_SOURCE,occurredAt:null})),
];
export function makeDemoEvent({ id, operationId, eventType, role, label, status, country, amountMinor = null, discountMinor = null, currency = null }) {
  if (!Object.values(DEMO_STATUSES).includes(eventType)) throw new Error("Tipo de evento inválido");
  if (!["PT","BR"].includes(country)) throw new Error("Mercado inválido");
  return {id:String(id),operationId:String(operationId),eventType,role,label,status,country,source:DEMO_SOURCE,
    amountMinor:Number.isSafeInteger(amountMinor)&&amountMinor>=0?amountMinor:null,
    discountMinor:Number.isSafeInteger(discountMinor)&&discountMinor>=0?discountMinor:null,
    currency,occurredAt:new Date().toISOString()};
}
export function toMinorUnits(raw) {
  const text=String(raw).trim().replace(",",".");
  if (!/^(?:[0-9]{1,6})(?:\.[0-9]{1,2})?$/.test(text)) return null;
  const units=Math.round(Number(text)*100);
  return Number.isSafeInteger(units)&&units>0&&units<=10000000?units:null;
}
export function deriveDemoMetrics(events,country) {
  const subset=events.filter(e=>e.source===DEMO_SOURCE&&e.country===country);
  const byType=t=>subset.filter(e=>e.eventType===t);
  const unique=t=>new Set(byType(t).map(e=>e.operationId));
  const scans=unique(DEMO_STATUSES.scan);
  const checkouts=unique(DEMO_STATUSES.checkout);
  const orphan=Array.from(checkouts).filter(id=>!scans.has(id)).length;
  const pending=Array.from(scans).filter(id=>!checkouts.has(id)).length;
  const duplicates=Object.values(DEMO_STATUSES).reduce((total,t)=>total+byType(t).length-unique(t).size,0);
  const invalid=subset.filter(e=>!e.id||!e.operationId||!e.eventType||!e.role).length;
  const collision=events.filter(e=>e.source!==DEMO_SOURCE).length;
  return {
    campaignCount: unique(DEMO_STATUSES.campaign).size,
    shares: unique(DEMO_STATUSES.share).size,
    scans: scans.size,
    checkouts: Array.from(checkouts).filter(id=>scans.has(id)).length,
    pending, orphan, duplicates, invalid, nonDemoExcluded:collision,
    actualPaid:null, confirmedRevenueMinor:null, actualCommissionMinor:null,
    qualityOk:duplicates===0&&orphan===0&&invalid===0
  };
}
export function getPendingDemoOperation(events,country) {
  const scans=events.filter(e=>e.country===country&&e.source===DEMO_SOURCE&&e.eventType===DEMO_STATUSES.scan);
  const used=new Set(events.filter(e=>e.country===country&&e.source===DEMO_SOURCE&&e.eventType===DEMO_STATUSES.checkout).map(e=>e.operationId));
  return scans.find(e=>!used.has(e.operationId))||null;
}
