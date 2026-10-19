import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { api, type Customer, type Vehicle } from "./api";
type Branch = { id:string; name:string };
type Bay = { id:string; name:string; active:boolean };
type Booking = { id:string; branch_id:string; customer_id:string; vehicle_id:string; bay_id:string|null;
  start_at:string; end_at:string; status:string; description:string; version:number };
const stateNames:Record<string,string>={booked:"Записан",confirmed:"Подтверждён",arrived:"Прибыл",cancelled:"Отменён",no_show:"Не прибыл"};
function error(e:unknown){return e instanceof Error?e.message:"Ошибка запроса";}
function isoLocal(date:string){return new Date(date).toLocaleString("ru-RU",{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"});}
export default function Schedule({ organization, role, customers, vehicles }:{
  organization:string;role:string;customers:Customer[];vehicles:Vehicle[];
}){
  const [branches,setBranches]=useState<Branch[]>([]),[branch,setBranch]=useState("");
  const [bays,setBays]=useState<Bay[]>([]),[bookings,setBookings]=useState<Booking[]>([]);
  const [name,setName]=useState(""),[bay,setBay]=useState(""),[customer,setCustomer]=useState(""),[vehicle,setVehicle]=useState("");
  const [start,setStart]=useState(""),[end,setEnd]=useState(""),[description,setDescription]=useState("");
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState(""),[adding,setAdding]=useState(false);
  const canEdit=["owner","manager","adviser"].includes(role);
  const idempotency=useRef<{signature:string;key:string}|null>(null);
  const headers={organization};
  const refresh=useCallback(async()=>{
    if(!branch)return;
    const [b,a]=await Promise.all([
      api<Bay[]>("bays?branch_id="+encodeURIComponent(branch),headers),
      api<Booking[]>("appointments?branch_id="+encodeURIComponent(branch),headers),
    ]);
    setBays(b);setBookings(a);
  },[branch,organization]);
  useEffect(()=>{let active=true;api<Branch[]>("branches",headers).then(data=>{
    if(!active)return;setBranches(data);setBranch(old=>data.some(b=>b.id===old)?old:data[0]?.id??"");
  }).catch(e=>{if(active)setNotice(error(e));});return()=>{active=false;};},[organization]);
  useEffect(()=>{setBays([]);setBookings([]);void refresh().catch(e=>setNotice(error(e)));},[refresh]);
  async function addBooking(e:FormEvent){
    e.preventDefault();setNotice("");setBusy(true);
    const data={branch_id:branch,customer_id:customer,vehicle_id:vehicle,bay_id:bay||null,
      start_at:new Date(start).toISOString(),end_at:new Date(end).toISOString(),description};
    const signature=JSON.stringify(data);
    if(idempotency.current?.signature!==signature)idempotency.current={signature,key:crypto.randomUUID()};
    try{
      await api("appointments",{method:"POST",organization,idempotencyKey:idempotency.current.key,data});
      idempotency.current=null;setAdding(false);await refresh();setNotice("Запись создана.");
    }catch(err){setNotice(error(err));}finally{setBusy(false);}
  }
  async function action(id:string,move:string){
    setBusy(true);setNotice("");
    try{await api("appointments/"+id+"/"+move,{method:"POST",organization,idempotencyKey:crypto.randomUUID(),data:{}});
      await refresh();setNotice("Статус записи обновлён.");
    }catch(e){setNotice(error(e));}finally{setBusy(false);}
  }
  return <><div className="page-lead"><div><div className="eyebrow">Планирование</div><h1>Запись на обслуживание</h1>
    <p className="muted">Запись, рабочий пост и фактическое прибытие — отдельные операции.</p></div>
    {canEdit&&<button className="primary" onClick={()=>setAdding(true)}>+ Создать запись</button>}</div>
    {notice&&<div className="notice info" role="status">{notice}</div>}
    <section className="card action-card">
      <label>Филиал<select value={branch} onChange={e=>setBranch(e.target.value)}>
      {branches.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label>
      <div className="table-scroll"><table><thead><tr><th>Время</th><th>Автомобиль</th><th>Клиент</th><th>Пост</th><th>Статус и действия</th></tr></thead>
      <tbody>{bookings.map(b=><tr key={b.id}><td>{isoLocal(b.start_at)} – {isoLocal(b.end_at)}</td>
        <td>{vehicles.find(v=>v.id===b.vehicle_id)?.model??b.vehicle_id}</td>
        <td>{customers.find(c=>c.id===b.customer_id)?.name??"Скрыто по роли"}</td>
        <td>{bays.find(p=>p.id===b.bay_id)?.name??"Без поста"}</td><td>{stateNames[b.status]??b.status}
        {canEdit&&["booked","confirmed"].includes(b.status)&&<div className="quick-actions">
          <button disabled={busy} onClick={()=>void action(b.id,"arrive")}>Прибыл</button>
          <button disabled={busy} onClick={()=>void action(b.id,"cancel")}>Отменить</button>
        </div>}</td></tr>)}</tbody></table>
      {!bookings.length&&<p className="table-empty">Нет записей для выбранного филиала.</p>}</div>
    </section>
    {adding&&<div className="modal-backdrop"><div className="modal" role="dialog" aria-modal="true" aria-labelledby="schedule-heading">
      <div className="modal-heading"><h2 id="schedule-heading">Новая запись</h2><button className="secondary" onClick={()=>setAdding(false)}>Закрыть</button></div>
      <form onSubmit={addBooking}>
      <label>Клиент<select required value={customer} onChange={e=>setCustomer(e.target.value)}><option value="">Выберите клиента</option>{customers.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
      <label>Автомобиль<select required value={vehicle} onChange={e=>setVehicle(e.target.value)}><option value="">Выберите автомобиль</option>{vehicles.map(v=><option key={v.id} value={v.id}>{v.make} {v.model} — {v.plate}</option>)}</select></label>
      <label>Пост<select value={bay} onChange={e=>setBay(e.target.value)}><option value="">Назначить позже</option>{bays.filter(x=>x.active).map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
      <div className="form-grid"><label>Начало<input required type="datetime-local" value={start} onChange={e=>setStart(e.target.value)}/></label>
      <label>Конец<input required type="datetime-local" value={end} onChange={e=>setEnd(e.target.value)}/></label></div>
      <label>Причина обращения<input maxLength={500} value={description} onChange={e=>setDescription(e.target.value)}/></label>
      <button className="primary" disabled={busy||!branch}>Создать запись</button></form>
    </div></div>}
  </>;
}
