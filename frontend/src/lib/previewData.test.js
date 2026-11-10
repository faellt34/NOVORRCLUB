import { deriveDemoMetrics, getPendingDemoOperation, initialDemoEvents, makeDemoEvent, toMinorUnits, DEMO_STATUSES } from "./previewData";
const ev=(id,operationId,eventType,country="PT")=>makeDemoEvent({id,operationId,eventType,country,role:eventType==="qr_validated"?"partner":"follower",label:"Evento demo",status:"Demonstração"});
test("converte montantes decimais sem aceitar entradas ambíguas",()=>{
  expect(toMinorUnits("10,50")).toBe(1050);
  expect(toMinorUnits("0.01")).toBe(1);
  expect(toMinorUnits("0.001")).toBeNull();
  expect(toMinorUnits("10xyz")).toBeNull();
  expect(toMinorUnits("-1")).toBeNull();
});
test("não conta validações duplicadas e separa mercados",()=>{
  const events=[...initialDemoEvents(),ev("a","order1",DEMO_STATUSES.scan),ev("b","order1",DEMO_STATUSES.scan),ev("c","order2",DEMO_STATUSES.scan,"BR")];
  const pt=deriveDemoMetrics(events,"PT");
  expect(pt.scans).toBe(1);
  expect(pt.duplicates).toBe(1);
  expect(pt.pending).toBe(1);
  expect(deriveDemoMetrics(events,"BR").scans).toBe(1);
});
test("checkout nunca é dinheiro confirmado e depende de QR válido",()=>{
  const events=[...initialDemoEvents(),ev("a","sale1",DEMO_STATUSES.scan),ev("b","sale1",DEMO_STATUSES.checkout)];
  const info=deriveDemoMetrics(events,"PT");
  expect(info.checkouts).toBe(1);
  expect(info.pending).toBe(0);
  expect(info.actualPaid).toBeNull();
  expect(info.confirmedRevenueMinor).toBeNull();
  expect(getPendingDemoOperation(events,"PT")).toBeNull();
});
test("checkout órfão é sinalizado e não aumenta conversões",()=>{
  const metrics=deriveDemoMetrics([ev("orphan","missing",DEMO_STATUSES.checkout)],"PT");
  expect(metrics.orphan).toBe(1);
  expect(metrics.checkouts).toBe(0);
  expect(metrics.qualityOk).toBe(false);
});


test("não mistura eventos de produção com contadores demonstrativos",()=>{
  const realLike={...ev("prod1","real-order",DEMO_STATUSES.scan),source:"production"};
  const metrics=deriveDemoMetrics([realLike],"PT");
  expect(metrics.scans).toBe(0);
  expect(metrics.nonDemoExcluded).toBe(1);
  expect(metrics.actualPaid).toBeNull();
  expect(metrics.actualCommissionMinor).toBeNull();
});
test("Brasil e Portugal conservam operações independentes com o mesmo ID lógico",()=>{
  const events=[
    ev("ptscan","order-a",DEMO_STATUSES.scan,"PT"),
    ev("brscan","order-a",DEMO_STATUSES.scan,"BR"),
    ev("ptpay","order-a",DEMO_STATUSES.checkout,"PT"),
  ];
  expect(deriveDemoMetrics(events,"PT").checkouts).toBe(1);
  expect(deriveDemoMetrics(events,"BR").checkouts).toBe(0);
  expect(deriveDemoMetrics(events,"BR").pending).toBe(1);
  expect(getPendingDemoOperation(events,"BR").id).toBe("brscan");
});
test("um checkout duplicado não duplica transações e gera alerta",()=>{
  const events=[
    ev("scan","order-x",DEMO_STATUSES.scan),
    ev("checkout-1","order-x",DEMO_STATUSES.checkout),
    ev("checkout-2","order-x",DEMO_STATUSES.checkout),
  ];
  const metrics=deriveDemoMetrics(events,"PT");
  expect(metrics.checkouts).toBe(1);
  expect(metrics.duplicates).toBe(1);
  expect(metrics.qualityOk).toBe(false);
});
test("uma operação pendente não pode ser contada como pagamento recebido",()=>{
  const events=[ev("scan","order-y",DEMO_STATUSES.scan)];
  const metrics=deriveDemoMetrics(events,"PT");
  expect(metrics.scans).toBe(1);
  expect(metrics.pending).toBe(1);
  expect(metrics.checkouts).toBe(0);
  expect(metrics.confirmedRevenueMinor).toBeNull();
});
