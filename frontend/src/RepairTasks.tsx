import {useCallback,useEffect,useState,type FormEvent} from "react";
import {api} from "./api";

type Task={id:string;order_id:string;mechanic_id:string;title:string;state:string;
 started_at:string|null;completed_at:string|null};
type Staff={id:string;email:string;role:string;active:boolean};
function errorText(e:unknown){return e instanceof Error?e.message:"Операция не выполнена";}
export default function RepairTasks({organization,orderId,role}:{
 organization:string;orderId:string;role:string;
}){
 const [tasks,setTasks]=useState<Task[]>([]);
 const [staff,setStaff]=useState<Staff[]>([]);
 const [mechanicId,setMechanicId]=useState("");
 const [title,setTitle]=useState("");
 const [busy,setBusy]=useState(false),[error,setError]=useState("");
 const [notice,setNotice]=useState("");
 const canAssign=["owner","manager"].includes(role);
 const canAction=["owner","manager","adviser","mechanic"].includes(role);
 const refresh=useCallback(async()=>{
   const jobs=await api<Task[]>("workorders/"+orderId+"/tasks",{organization});
   setTasks(jobs);
   if(canAssign){
     const rows=await api<Staff[]>("staff/members",{organization});
     const mechanics=rows.filter(x=>x.role==="mechanic"&&x.active);
     setStaff(mechanics);
     setMechanicId(old=>mechanics.some(m=>m.id===old)?old:mechanics[0]?.id??"");
   }
 },[organization,orderId,canAssign]);
 useEffect(()=>{
   let active=true;
   setTasks([]);setStaff([]);setMechanicId("");setError("");setNotice("");
   async function fetchJobs(){
     try{
       const jobs=await api<Task[]>("workorders/"+orderId+"/tasks",{organization});
       if(active)setTasks(jobs);
       if(canAssign){
         const rows=await api<Staff[]>("staff/members",{organization});
         if(active){
           const mechanics=rows.filter(x=>x.role==="mechanic"&&x.active);
           setStaff(mechanics);
           setMechanicId(mechanics[0]?.id??"");
         }
       }
     }catch(e){if(active)setError(errorText(e));}
   }
   void fetchJobs();
   return()=>{active=false;};
 },[organization,orderId,canAssign]);
 async function call(path:string,data:unknown={}){
   setBusy(true);setError("");setNotice("");
   try{await api(path,{method:"POST",organization,
     idempotencyKey:crypto.randomUUID(),data});
     await refresh();setNotice("Задание обновлено.");
   }catch(e){setError(errorText(e));}finally{setBusy(false);}
 }
 async function assign(e:FormEvent){
   e.preventDefault();await call("workorders/"+orderId+"/tasks",
     {membership_id:mechanicId,title});setTitle("");
 }
 return <section style={{marginTop:24}}>
  <h2>Задания механиков</h2>
  <p className="muted">Начало и завершение фиксируются сервером. Нельзя назначать механику два одновременно выполняемых задания.</p>
  {error&&<div className="notice error" role="alert">{error}</div>}
  {notice&&<div className="notice info" role="status">{notice}</div>}
  <div className="table-scroll"><table><thead><tr>
   <th>Задание</th><th>Механик</th><th>Состояние</th><th>Операция</th></tr></thead>
   <tbody>{tasks.map(t=><tr key={t.id}><td>{t.title}</td>
   <td>{staff.find(x=>x.id===t.mechanic_id)?.email??t.mechanic_id.slice(0,8)}</td>
   <td>{t.state==="assigned"?"Назначено":t.state==="running"?"В работе":t.state==="done"?"Выполнено":"Отменено"}</td>
   <td>{canAction&&t.state==="assigned"&&<button disabled={busy} className="secondary"
    onClick={()=>void call("workorders/"+orderId+"/tasks/"+t.id+"/start")}>Начать</button>}
    {canAction&&t.state==="running"&&<button disabled={busy} className="secondary"
    onClick={()=>void call("workorders/"+orderId+"/tasks/"+t.id+"/finish")}>Завершить</button>}
   </td></tr>)}</tbody></table></div>
  {canAssign&&<form onSubmit={assign}><h2>Назначить работу</h2>
    <label>Механик<select required value={mechanicId} onChange={e=>setMechanicId(e.target.value)}>
      <option value="">Выберите исполнителя</option>
      {staff.map(m=><option key={m.id} value={m.id}>{m.email}</option>)}
    </select></label>
    <label>Задание<input required maxLength={200} value={title}
      onChange={e=>setTitle(e.target.value)} placeholder="Например, проверить тормозную систему"/></label>
    <button className="secondary" disabled={busy||!mechanicId}>Назначить механику</button>
  </form>}
 </section>;
}
