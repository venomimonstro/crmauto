import {useEffect,useState} from "react";
import {api} from "./api";
type Branch={id:string;name:string};
type Totals={invoiced_minor:number;cash_received_minor:number;cash_refunded_minor:number;outstanding_minor:number;profit_unavailable_reason:string};
type Flag={code:string;object_id:string;amount_minor:number|null;description:string};
const rub=(v:number)=>new Intl.NumberFormat("ru-RU",{style:"currency",currency:"RUB"}).format(v/100);
export default function Reports({organization}:{organization:string}){
 const [branches,setBranches]=useState<Branch[]>([]);
 const [branch,setBranch]=useState("");
 const [totals,setTotals]=useState<Totals|null>(null);
 const [flags,setFlags]=useState<Flag[]>([]);
 const [error,setError]=useState("");
 useEffect(()=>{setBranches([]);setBranch("");api<Branch[]>("branches",{organization})
   .then(rows=>{setBranches(rows);setBranch(rows[0]?.id??"");})
   .catch(e=>setError(String(e)));},[organization]);
 useEffect(()=>{if(!branch)return;setTotals(null);setFlags([]);
   Promise.all([api<Totals>("reports/finance?branch_id="+branch,{organization}),
     api<{items:Flag[]}>("reports/losses?branch_id="+branch,{organization})])
     .then(([a,b])=>{setTotals(a);setFlags(b.items);}).catch(e=>setError(String(e)));
 },[organization,branch]);
 return <><div className="page-lead"><div><div className="eyebrow">Управление</div>
   <h1>Отчёты и центр потерь</h1><p className="muted">Только проверяемые внутренние показатели CRM.</p></div></div>
   {error&&<div className="notice error" role="alert">{error}</div>}
   <section className="card action-card"><label>Филиал<select value={branch}
    onChange={e=>setBranch(e.target.value)}>{branches.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label></section>
   {totals&&<><div className="stats" style={{marginTop:16}}>
      {[["Начислено",totals.invoiced_minor],["Поступило",totals.cash_received_minor],
      ["Возвращено",totals.cash_refunded_minor],["Долг",totals.outstanding_minor]].map(([name,sum])=>
      <div className="stat" key={String(name)}><span>{name}</span><strong>{rub(Number(sum))}</strong></div>)}</div>
      <div className="notice info">Прибыль не рассчитана: {totals.profit_unavailable_reason}</div></>}
   <section className="card action-card"><h2>Требуют внимания</h2>
    <div className="table-scroll"><table><thead><tr><th>Причина</th><th>Объект</th><th>Сумма</th></tr></thead>
    <tbody>{flags.map(x=><tr key={x.code+x.object_id}><td>{x.description}</td>
    <td>{x.object_id.slice(0,8)}</td><td>{x.amount_minor===null?"—":rub(x.amount_minor)}</td></tr>)}</tbody></table>
    {!flags.length&&<p className="table-empty">Проблемы не обнаружены или данные загружаются.</p>}</div></section>
   <p className="muted">CRM не заменяет банковскую сверку, фискализацию и бухгалтерскую отчётность.</p></>;
}
