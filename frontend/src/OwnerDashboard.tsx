import {useCallback,useEffect,useState} from "react";
import {api} from "./api";

type Branch={id:string;name:string};
type Daily={
 date:string;appointments_today:number;arrived_today:number;open_visits:number;
 workorders_waiting_approval:number;workorders_in_repair:number;
 workorders_in_quality_check:number;workorders_ready:number;
 active_parts_reservations:number;purchases_waiting_receiving:number;
 cash_today_minor:number;outstanding_minor:number;warnings:string[];
};
const rub=(minor:number)=>new Intl.NumberFormat("ru-RU",{style:"currency",currency:"RUB",maximumFractionDigits:0}).format(minor/100);
const nameOf=(e:unknown)=>e instanceof Error?e.message:"Ошибка загрузки данных.";

export default function OwnerDashboard({organization,onNavigate}:{
 organization:string;onNavigate:(area:"orders"|"lifts"|"cash"|"reports"|"inventory")=>void;
}){
 const [branches,setBranches]=useState<Branch[]>([]);
 const [branch,setBranch]=useState("");
 const [daily,setDaily]=useState<Daily|null>(null);
 const [error,setError]=useState("");
 const [loading,setLoading]=useState(true);
 const [serial,setSerial]=useState(0);
 useEffect(()=>{
   let active=true;
   setBranches([]);setBranch("");setDaily(null);setError("");setLoading(true);
   api<Branch[]>("branches",{organization})
     .then(rows=>{if(active){setBranches(rows);setBranch(rows[0]?.id??"");if(!rows.length)setLoading(false);}})
     .catch(e=>{if(active){setError(nameOf(e));setLoading(false);}});
   return()=>{active=false;};
 },[organization,serial]);
 useEffect(()=>{
   if(!branch)return;
   let active=true;setLoading(true);setDaily(null);setError("");
   api<Daily>("reports/daily?branch_id="+encodeURIComponent(branch),{organization})
     .then(data=>{if(active)setDaily(data);})
     .catch(e=>{if(active)setError(nameOf(e));})
     .finally(()=>{if(active)setLoading(false);});
   return()=>{active=false;};
 },[organization,branch,serial]);
 const retry=useCallback(()=>setSerial(n=>n+1),[]);
 const number=(n:number)=>new Intl.NumberFormat("ru-RU").format(n);
 const stats: {title:string;value:number;area:"orders"|"lifts"|"inventory";note:string}[] =daily?[
  {title:"Записей на сегодня",value:daily.appointments_today,area:"lifts",note:"Все статусы"},
  {title:"Ждут согласования",value:daily.workorders_waiting_approval,area:"orders",note:"Требуют связи с клиентом"},
  {title:"В ремонте",value:daily.workorders_in_repair,area:"orders",note:"Текущие заказ-наряды"},
  {title:"Готовы к выдаче",value:daily.workorders_ready,area:"orders",note:"Выдача пока ограничена"},
  {title:"Ожидают поставки",value:daily.purchases_waiting_receiving,area:"inventory",note:"Открытые закупки"},
  {title:"Резервы запчастей",value:daily.active_parts_reservations,area:"inventory",note:"Активные резервы"},
 ]:[];
 return <div className="owner-dashboard">
   <div className="page-lead">
     <div><div className="eyebrow">Сегодня в автосервисе</div><h1>Рабочий день</h1>
     <p className="muted">Фактические очереди и показатели выбранного филиала. Без демонстрационных цифр.</p></div>
     <button className="secondary" onClick={retry} disabled={loading} aria-label="Обновить данные рабочего дня">Обновить</button>
   </div>
   <section className="card action-card owner-toolbar">
     <label>Филиал
       <select value={branch} disabled={loading&&!branches.length} onChange={e=>setBranch(e.target.value)}>
         {branches.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}
       </select>
     </label>
     {daily&&<div className="dashboard-updated">Актуально на {new Date().toLocaleTimeString("ru-RU",{hour:"2-digit",minute:"2-digit"})} · {new Date(daily.date+"T12:00:00").toLocaleDateString("ru-RU")}</div>}
   </section>
   {error&&<div className="notice error" role="alert">
     {error} <button className="secondary" onClick={retry}>Повторить загрузку</button>
   </div>}
   {loading&&<div className="loading-inline" role="status" aria-live="polite">Загрузка показателей филиала…</div>}
   {!loading&&!error&&!branches.length&&<div className="notice info">В организации нет доступных филиалов. Создайте или запросите доступ к филиалу.</div>}
   {daily&&!loading&&<><div className="stats owner-stats">
     {stats.map(x=><button className="stat stat-interactive" key={x.title} onClick={()=>onNavigate(x.area)}
       aria-label={x.title+", "+number(x.value)+". Открыть раздел"}>
       <span>{x.title}</span><strong>{number(x.value)}</strong><small>{x.note}</small>
     </button>)}
   </div>
   <section className="card action-card owner-finance">
     <div><h2>Денежный журнал за сегодня</h2>
       <p className="muted">Внутренний учёт наличных, не фискальный отчёт и не подтверждение банка.</p></div>
     <div className="owner-amounts">
       <div><span>Чистое движение</span><strong>{rub(daily.cash_today_minor)}</strong></div>
       <div><span>Текущая задолженность</span><strong>{rub(daily.outstanding_minor)}</strong></div>
     </div>
     <button className="secondary" onClick={()=>onNavigate("cash")}>Открыть кассу</button>
   </section>
   <section className="card action-card" style={{marginTop:16}}>
     <h2>Очередь руководителя</h2>
     <div className="owner-work-queue">
       <button onClick={()=>onNavigate("orders")}>Ожидают согласования <strong>{number(daily.workorders_waiting_approval)}</strong></button>
       <button onClick={()=>onNavigate("orders")}>На контроле качества <strong>{number(daily.workorders_in_quality_check)}</strong></button>
       <button onClick={()=>onNavigate("lifts")}>Открытых визитов <strong>{number(daily.open_visits)}</strong></button>
       <button onClick={()=>onNavigate("inventory")}>Ожидают поставки <strong>{number(daily.purchases_waiting_receiving)}</strong></button>
     </div>
     <button className="secondary" onClick={()=>onNavigate("reports")}>Все отчёты и центр потерь</button>
   </section>
   <p className="muted" style={{marginTop:18}}>Данные обновляются по запросу; для финансовой сверки необходимы подтверждённые кассовые документы.</p>
   </>}
 </div>;
}
