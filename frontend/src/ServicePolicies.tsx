import {useEffect,useState,type FormEvent} from "react";
import {api} from "./api";
type Policy={id:string;version:number;service_terms:string;warranty_terms:string;created_at:string;is_current:boolean};
export default function ServicePolicies({organization}:{organization:string}){
 const [history,setHistory]=useState<Policy[]>([]);
 const [service,setService]=useState(""),[warranty,setWarranty]=useState("");
 const [error,setError]=useState(""),[notice,setNotice]=useState(""),[busy,setBusy]=useState(false);
 useEffect(()=>{let live=true;setHistory([]);setError("");setService("");setWarranty("");
   api<Policy[]>("organization/service-policies",{organization}).then(items=>{
     if(live){setHistory(items);if(items.length){setService(items[0].service_terms);setWarranty(items[0].warranty_terms);}}
   }).catch(e=>{if(live)setError(String(e));});return()=>{live=false;};
 },[organization]);
 async function publish(e:FormEvent){
   e.preventDefault();setBusy(true);setError("");setNotice("");
   try{await api("organization/service-policies",{method:"POST",organization,
      idempotencyKey:crypto.randomUUID(),data:{service_terms:service,warranty_terms:warranty}});
      const items=await api<Policy[]>("organization/service-policies",{organization});
      setHistory(items);setNotice("Новая редакция опубликована. Ранее сформированные документы не изменены.");
   }catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
 }
 return <section className="card action-card" style={{marginTop:16}}>
  <h2>Условия обслуживания и гарантии</h2>
  <p className="muted">Редактируйте утверждённые правила СТО. Каждая публикация создаёт новую редакцию; прежние печатные документы сохраняют старый текст. Условия должны быть юридически проверены.</p>
  {error&&<div className="notice error" role="alert">{error}</div>}
  {notice&&<div className="notice info" role="status">{notice}</div>}
  <form onSubmit={publish}>
   <label>Правила обслуживания<textarea required minLength={30} rows={5}
     value={service} onChange={e=>setService(e.target.value)}/></label>
   <label>Гарантийные условия<textarea required minLength={30} rows={5}
     value={warranty} onChange={e=>setWarranty(e.target.value)}/></label>
   <button className="primary" disabled={busy||service.trim().length<30||warranty.trim().length<30}>Опубликовать новую редакцию</button>
  </form>
  <h2 style={{marginTop:24}}>История редакций</h2>
  {history.map(item=><p key={item.id}>Редакция №{item.version} · {new Date(item.created_at).toLocaleString("ru-RU")} {item.is_current?"· Действует":""}</p>)}
  {!history.length&&<p className="muted">Условия пока не опубликованы.</p>}
 </section>;
}