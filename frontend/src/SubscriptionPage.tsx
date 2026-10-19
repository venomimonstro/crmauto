import {useEffect,useState} from "react";
import {api} from "./api";
type Plan={code:string;name:string;price_minor:number;max_branches:number;max_staff:number};
type Status={state:string;access:string;plan_code?:string;paid_through?:string|null;
 trial_ends_at?:string|null;limits?:{branches:number;staff:number};message?:string};
const formatRub=(v:number)=>new Intl.NumberFormat("ru-RU",{style:"currency",currency:"RUB",maximumFractionDigits:0}).format(v/100);
const date=(value?:string|null)=>value?new Date(value).toLocaleDateString("ru-RU"):"Не установлена";
export default function SubscriptionPage({organization,role}:{organization:string;role:string}){
 const [plans,setPlans]=useState<Plan[]>([]),[state,setState]=useState<Status|null>(null);
 const [loading,setLoading]=useState(true),[error,setError]=useState("");
 useEffect(()=>{let alive=true;setLoading(true);setError("");setState(null);setPlans([]);
   Promise.all([
     api<Plan[]>("billing/plans",{organization}),
     api<Status>("billing/subscription",{organization})
   ]).then(([p,s])=>{if(alive){setPlans(p);setState(s);}})
     .catch(e=>{if(alive)setError(e instanceof Error?e.message:String(e));})
     .finally(()=>{if(alive)setLoading(false);});
   return()=>{alive=false;};
 },[organization]);
 if(!["owner","manager"].includes(role))
   return <div className="notice error">Настройки подписки доступны владельцу и управляющему.</div>;
 return <><div className="page-lead"><div><div className="eyebrow">Подписка CRM</div>
   <h1>Тариф и доступ</h1><p className="muted">Управление доступом вашей организации к CRM.</p></div></div>
   {loading&&<p className="muted">Загрузка сведений о подписке…</p>}
   {error&&<div role="alert" className="notice error">{error}</div>}
   {state&&<section className="card action-card">
     <h2>Текущий доступ</h2>
     <p><strong>{state.access==="write"?"Работа разрешена":"Только просмотр / доступ не настроен"}</strong></p>
     <p className="muted">Состояние: {state.state}; тариф: {state.plan_code??"не установлен"}</p>
     <p className="muted">Пробный период до: {date(state.trial_ends_at)}. Оплачено до: {date(state.paid_through)}.</p>
     {state.limits&&<p className="muted">Ограничения: филиалы — {state.limits.branches}, сотрудники — {state.limits.staff}.</p>}
     {state.access!=="write"&&<div className="notice error">Новые операции заблокированы после включения серверной политики подписок. Существующие данные сохраняются доступными для просмотра.</div>}
   </section>}
   <section className="card action-card" style={{marginTop:16}}>
     <h2>Доступные тарифы</h2><div className="table-scroll"><table><thead><tr><th>Тариф</th><th>Стоимость</th><th>Филиалов</th><th>Сотрудников</th></tr></thead>
     <tbody>{plans.map(x=><tr key={x.code}><td>{x.name}</td><td>{formatRub(x.price_minor)}</td>
       <td>{x.max_branches}</td><td>{x.max_staff}</td></tr>)}</tbody></table>
     {!plans.length&&<p className="table-empty">Тарифы пока не опубликованы.</p>}</div>
   </section>
   <div className="notice info" style={{marginTop:20}}>
     Онлайн-оплата и автоматическое продление ещё не подключены. Не отправляйте деньги по реквизитам, полученным вне проверенного платёжного сервиса.
   </div>
 </>;
}
