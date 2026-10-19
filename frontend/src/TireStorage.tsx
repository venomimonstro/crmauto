import {useCallback,useEffect,useRef,useState,type FormEvent} from "react";
import {api,type Customer,type Vehicle} from "./api";

type Branch={id:string;name:string};
type TireSet={id:string;code:string;customer_id:string;vehicle_id:string|null;
 pieces:number;description:string;storage_location:string;state:"stored"|"released"};
const errorText=(e:unknown)=>e instanceof Error?e.message:"Операция не выполнена.";

export default function TireStorage({organization,role,customers,vehicles}:{
 organization:string;role:string;customers:Customer[];vehicles:Vehicle[];
}){
 const [branches,setBranches]=useState<Branch[]>([]);
 const [branch,setBranch]=useState("");
 const [sets,setSets]=useState<TireSet[]>([]);
 const [code,setCode]=useState(""),[customer,setCustomer]=useState("");
 const [vehicle,setVehicle]=useState(""),[pieces,setPieces]=useState("4");
 const [description,setDescription]=useState(""),[location,setLocation]=useState("");
 const [busy,setBusy]=useState(false),[loading,setLoading]=useState(false);
 const [error,setError]=useState(""),[notice,setNotice]=useState("");
 const [search,setSearch]=useState("");
 const [onlyStored,setOnlyStored]=useState(true);
 const retry=useRef<{signature:string;key:string}|null>(null);
 const canEdit=["owner","manager","adviser"].includes(role);
 const refresh=useCallback(async()=>{
   if(!branch){setSets([]);return;}
   const rows=await api<TireSet[]>("tire-sets?branch_id="+encodeURIComponent(branch),{organization});
   setSets(rows);
 },[branch,organization]);
 useEffect(()=>{
   let mounted=true;
   setBranches([]);setBranch("");setSets([]);setError("");
   api<Branch[]>("branches",{organization}).then(rows=>{
     if(mounted){setBranches(rows);setBranch(rows[0]?.id??"");}
   }).catch(e=>{if(mounted)setError(errorText(e));});
   return()=>{mounted=false;};
 },[organization]);
 useEffect(()=>{
   if(!branch)return;
   let mounted=true;setLoading(true);setError("");
   api<TireSet[]>("tire-sets?branch_id="+encodeURIComponent(branch),{organization})
     .then(rows=>{if(mounted)setSets(rows);})
     .catch(e=>{if(mounted)setError(errorText(e));})
     .finally(()=>{if(mounted)setLoading(false);});
   return()=>{mounted=false;};
 },[branch,organization]);
 async function receive(e:FormEvent){
   e.preventDefault();
   const data={branch_id:branch,customer_id:customer,vehicle_id:vehicle||null,
     code:code.trim(),pieces:Number(pieces),description:description.trim(),
     storage_location:location.trim()};
   const signature=JSON.stringify(data);
   if(retry.current?.signature!==signature)retry.current={signature,key:crypto.randomUUID()};
   setBusy(true);setError("");setNotice("");
   try{
     await api("tire-sets",{method:"POST",organization,idempotencyKey:retry.current.key,data});
     retry.current=null;setCode("");setDescription("");setLocation("");setVehicle("");
     await refresh();setNotice("Комплект принят на ответственное хранение.");
   }catch(err){setError(errorText(err));}
   finally{setBusy(false);}
 }
 async function release(row:TireSet){
   if(!window.confirm("Подтвердить фактическую выдачу комплекта "+row.code+" клиенту?"))return;
   setBusy(true);setError("");setNotice("");
   try{
     await api("tire-sets/"+row.id+"/release",{method:"POST",organization,
       idempotencyKey:crypto.randomUUID(),data:{}});
     await refresh();setNotice("Комплект отмечен выданным.");
   }catch(err){setError(errorText(err));}
   finally{setBusy(false);}
 }
 const visible=sets.filter(x=>(!onlyStored||x.state==="stored")&&
   (x.code+" "+x.description+" "+x.storage_location+
    " "+(customers.find(c=>c.id===x.customer_id)?.name??""))
     .toLowerCase().includes(search.trim().toLowerCase()));
 return <><div className="page-lead"><div>
   <div className="eyebrow">Ответственное хранение</div><h1>Шиномонтаж и хранение шин</h1>
   <p className="muted">Клиентские колёса учитываются отдельно от товарного склада автосервиса.</p>
 </div></div>
 {error&&<div className="notice error" role="alert">{error}</div>}
 {notice&&<div className="notice info" role="status">{notice}</div>}
 <section className="card action-card">
   <label>Филиал<select value={branch} onChange={e=>{setBranch(e.target.value);setNotice("");setSets([]);}}>
     {branches.map(x=><option value={x.id} key={x.id}>{x.name}</option>)}
   </select></label>
 </section>
 {canEdit&&<section className="card action-card" style={{marginTop:16}}>
  <h2>Принять комплект на хранение</h2>
  <form onSubmit={receive}>
   <div className="form-grid">
     <label>Клиент<select value={customer} onChange={e=>{setCustomer(e.target.value);setVehicle("");}} required>
       <option value="">Выберите клиента</option>
       {customers.map(c=><option value={c.id} key={c.id}>{c.name}</option>)}
     </select></label>
     <label>Автомобиль<select value={vehicle} onChange={e=>setVehicle(e.target.value)}>
       <option value="">Не указывать</option>
       {vehicles.filter(v=>v.current_owner===customer).map(v=><option value={v.id} key={v.id}>{v.make} {v.model} · {v.plate}</option>)}
     </select></label>
     <label>Уникальный код комплекта<input required maxLength={80} value={code}
       onChange={e=>setCode(e.target.value)} placeholder="Ш-2026-001"/></label>
     <label>Количество колёс<input type="number" required min="1" max="16" step="1"
       value={pieces} onChange={e=>setPieces(e.target.value)}/></label>
     <label>Место хранения<input required maxLength={120} value={location}
       onChange={e=>setLocation(e.target.value)} placeholder="Стеллаж A / секция 3"/></label>
     <label>Описание, размер, сезон<input required maxLength={300} value={description}
       onChange={e=>setDescription(e.target.value)} placeholder="205/55 R16, зимние"/></label>
   </div>
   <button className="primary" disabled={busy||!branch||!customer}>Принять комплект</button>
  </form>
 </section>}
 <section className="card action-card" style={{marginTop:16}}>
  <div className="page-lead"><div><h2>Комплекты</h2>
    <p className="muted">{sets.filter(x=>x.state==="stored").length} сейчас хранятся</p></div>
    <button className="secondary" disabled={busy||loading||!branch} onClick={()=>void refresh().catch(e=>setError(errorText(e)))}>Обновить</button>
  </div>
  <div className="form-grid">
    <label>Поиск<input type="search" value={search} onChange={e=>setSearch(e.target.value)}
      placeholder="Код, клиент, место хранения"/></label>
    <label className="check-label"><input type="checkbox" checked={onlyStored}
      onChange={e=>setOnlyStored(e.target.checked)}/> Только хранящиеся</label>
  </div>
  {loading&&<div role="status" className="loading-inline">Загрузка комплектов…</div>}
  <div className="table-scroll"><table><thead><tr>
    <th>Код</th><th>Клиент</th><th>Колёс</th><th>Место</th><th>Статус</th><th>Действие</th>
  </tr></thead><tbody>{visible.map(x=><tr key={x.id}>
    <td><strong>{x.code}</strong><div className="muted">{x.description}</div></td>
    <td>{customers.find(c=>c.id===x.customer_id)?.name??"Клиент"}</td>
    <td>{x.pieces}</td><td>{x.storage_location}</td>
    <td>{x.state==="stored"?"Хранится":"Выдан"}</td>
    <td>{canEdit&&x.state==="stored"&&<button className="secondary" disabled={busy}
      onClick={()=>void release(x)}>Выдать клиенту</button>}</td>
  </tr>)}</tbody></table>
    {!visible.length&&!loading&&<p className="table-empty">Нет комплектов по выбранным условиям.</p>}
  </div>
 </section>
 <p className="muted" style={{marginTop:16}}>Документы ответственного хранения, фотографии и расчёт стоимости услуги требуют отдельной приёмки. Этот экран не создаёт продажу.</p>
 </>;
}
