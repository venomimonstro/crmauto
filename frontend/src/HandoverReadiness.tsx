import {useEffect,useState} from "react";
import {api} from "./api";
type Check={code:string;ok:boolean;label:string};
type Readiness={status:string;checks:Check[];handover_allowed:boolean;debt_minor:number|null;message:string};
export default function HandoverReadiness({organization,orderId}:{
 organization:string;orderId:string;
}){
 const [data,setData]=useState<Readiness|null>(null);
 const [error,setError]=useState("");
 const [serial,setSerial]=useState(0);
 useEffect(()=>{let active=true;setData(null);setError("");
  api<Readiness>("workorders/"+orderId+"/handover-readiness",{organization})
   .then(x=>{if(active)setData(x);})
   .catch(e=>{if(active)setError(e instanceof Error?e.message:"Ошибка проверки");});
  return()=>{active=false;};
 },[organization,orderId,serial]);
 return <section className="card action-card" style={{marginTop:18}}>
  <div className="page-lead"><div><h2>Подготовка к выдаче автомобиля</h2>
   <p className="muted">Проверка состояния ремонта. Не подтверждает фактическую выдачу.</p></div>
   <button className="secondary" onClick={()=>setSerial(n=>n+1)}>Проверить заново</button>
  </div>
  {error&&<p className="notice error" role="alert">{error}</p>}
  {!data&&!error&&<p role="status" className="muted">Проверка документов и расчётов…</p>}
  {data&&<><div className="handover-checklist">{data.checks.map(c=><div key={c.code} className="handover-check">
    <span aria-label={c.ok?"Выполнено":"Требует внимания"}>{c.ok?"✓":"○"}</span>
    <span>{c.label}</span></div>)}</div>
    <p className="notice info">{data.message}</p>
    {data.debt_minor!==null&&<p><strong>Остаток по внутреннему начислению:</strong> {(data.debt_minor/100).toLocaleString("ru-RU",{style:"currency",currency:"RUB"})}</p>}
  </>}
 </section>;
}