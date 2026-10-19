import { useCallback,useEffect,useRef,useState,type FormEvent } from "react";
import { api,type Customer,type Vehicle } from "./api";
import RepairTasks from "./RepairTasks";
import OrderDocuments from "./OrderDocuments";
type Branch={id:string;name:string};
type Visit={id:string;branch_id:string;customer_id:string;vehicle_id:string;status:string};
type Order={id:string;visit_id:string;customer_id:string;vehicle_id:string;status:string;version:number;complaint:string};
type Line={id:string;kind:string;title:string;quantity:string;unit_price_minor:number;total_minor:number};
type Estimate={id:string;revision:number;state:string;total_minor:number;lines:Line[]};
type Detail={order:Order;estimates:Estimate[];history:{from:string;to:string;at:string}[]};
type Additional={id:string;title:string;description:string;amount_minor:number;status:string};
const STATES:Record<string,string>={draft:"Черновик",awaiting:"Ожидает согласования",approved:"Согласован",in_progress:"Ремонт",qa:"Проверка",ready:"Готов",delivered:"Выдан",cancelled:"Отменён"};
const money=(n:number)=>(n/100).toLocaleString("ru-RU",{style:"currency",currency:"RUB"});
const errmsg=(e:unknown)=>e instanceof Error?e.message:"Ошибка операции";
export default function WorkOrders({organization,role,customers,vehicles}:{
  organization:string;role:string;customers:Customer[];vehicles:Vehicle[];
}){
  const [branches,setBranches]=useState<Branch[]>([]),[branch,setBranch]=useState("");
  const [visits,setVisits]=useState<Visit[]>([]),[orders,setOrders]=useState<Order[]>([]);
  const [selected,setSelected]=useState<Detail|null>(null),[visit,setVisit]=useState("");
  const [complaint,setComplaint]=useState(""),[notice,setNotice]=useState("");
  const [lineTitle,setLineTitle]=useState(""),[lineKind,setLineKind]=useState("labor");
  const [quantity,setQuantity]=useState("1"),[price,setPrice]=useState("0");
  const [reference,setReference]=useState(""),[busy,setBusy]=useState(false);
  const [creating,setCreating]=useState(false);
  const [findings,setFindings]=useState<Additional[]>([]);
  const [extraTitle,setExtraTitle]=useState(""),[extraDescription,setExtraDescription]=useState(""),[extraPrice,setExtraPrice]=useState("0");
  const creation=useRef<{payload:string;key:string}|null>(null);
  const canEdit=["owner","manager","adviser"].includes(role);
  const headers={organization};
  const load=useCallback(async()=>{
    if(!branch)return;
    const [v,o]=await Promise.all([
      api<Visit[]>("visits?branch_id="+encodeURIComponent(branch),headers),
      api<Order[]>("workorders?branch_id="+encodeURIComponent(branch),headers)
    ]);setVisits(v);setOrders(o);
  },[branch,organization]);
  const loadDetail=useCallback(async(id:string)=>{
    const [detail,extra]=await Promise.all([api<Detail>("workorders/"+id,headers),api<Additional[]>("workorders/"+id+"/additional-works",headers)]);setSelected(detail);setFindings(extra);
  },[organization]);
  useEffect(()=>{let alive=true;api<Branch[]>("branches",headers).then(x=>{
    if(!alive)return;setBranches(x);setBranch(previous=>x.some(b=>b.id===previous)?previous:x[0]?.id??"");
  }).catch(e=>{if(alive)setNotice(errmsg(e));});return()=>{alive=false;};},[organization]);
  useEffect(()=>{setSelected(null);void load().catch(e=>setNotice(errmsg(e)));},[load]);
  async function create(e:FormEvent){
    e.preventDefault();if(!canEdit)return;
    const data={visit_id:visit,complaint};const serialized=JSON.stringify(data);
    if(creation.current?.payload!==serialized)creation.current={payload:serialized,key:crypto.randomUUID()};
    setBusy(true);setNotice("");
    try{const o=await api<Order>("workorders",{method:"POST",organization,
      idempotencyKey:creation.current.key,data});creation.current=null;setCreating(false);
      await load();await loadDetail(o.id);
    }catch(e){setNotice(errmsg(e));}finally{setBusy(false);}
  }
  async function addLine(e:FormEvent){
    e.preventDefault();if(!selected)return;
    const cents=Math.round(Number(price)*100);
    if(!Number.isSafeInteger(cents)||cents<0){setNotice("Некорректная стоимость.");return;}
    setBusy(true);setNotice("");
    try{await api("workorders/"+selected.order.id+"/lines",{method:"POST",organization,
      idempotencyKey:crypto.randomUUID(),data:{kind:lineKind,title:lineTitle,quantity,unit_price_minor:cents}});
      setLineTitle("");await loadDetail(selected.order.id);
    }catch(e){setNotice(errmsg(e));}finally{setBusy(false);}
  }
  async function action(actionName:string){
    if(!selected)return;setBusy(true);setNotice("");
    try{await api("workorders/"+selected.order.id+"/actions/"+actionName,{method:"POST",organization,
      idempotencyKey:crypto.randomUUID(),data:actionName==="approve"?{reference}:{}});
      await load();await loadDetail(selected.order.id);setReference("");
    }catch(e){setNotice(errmsg(e));}finally{setBusy(false);}
  }
  async function proposeAdditional(e:FormEvent){
    e.preventDefault();if(!selected)return;
    const value=Math.round(Number(extraPrice)*100);
    if(!Number.isSafeInteger(value)||value<0){setNotice("Неверная стоимость");return;}
    setBusy(true);setNotice("");
    try{
      await api("workorders/"+selected.order.id+"/additional-works",{method:"POST",organization,
        idempotencyKey:crypto.randomUUID(),data:{title:extraTitle,description:extraDescription,amount_minor:value}});
      setExtraTitle("");setExtraDescription("");setExtraPrice("0");await loadDetail(selected.order.id);
    }catch(e){setNotice(errmsg(e));}finally{setBusy(false);}
  }
  const current=selected?.estimates.at(-1);
  const active=visits.filter(v=>v.status==="open"&&!orders.some(o=>o.visit_id===v.id));
  return <><div className="page-lead"><div><div className="eyebrow">Производство</div>
    <h1>Заказ-наряды</h1><p className="muted">Приёмка, стоимость работ и последовательное согласование смет.</p></div>
    {canEdit&&<button className="primary" onClick={()=>setCreating(true)}>+ Новый заказ-наряд</button>}</div>
    {notice&&<div className="notice info" role="status">{notice}</div>}
    <section className="card action-card"><label>Филиал<select value={branch} onChange={e=>setBranch(e.target.value)}>
      {branches.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label>
      <div className="table-scroll"><table><thead><tr><th>Автомобиль</th><th>Клиент</th><th>Статус</th><th>Карточка</th></tr></thead>
      <tbody>{orders.map(o=><tr key={o.id}><td>{vehicles.find(v=>v.id===o.vehicle_id)?.model??"Автомобиль"}</td>
        <td>{customers.find(c=>c.id===o.customer_id)?.name??"Клиент"}</td><td>{STATES[o.status]??o.status}</td>
        <td><button className="secondary" onClick={()=>void loadDetail(o.id)}>Открыть</button></td></tr>)}</tbody></table>
      {!orders.length&&<p className="table-empty">Заказ-нарядов пока нет.</p>}</div></section>
    {selected&&<section className="card action-card" style={{marginTop:16}}>
      <div className="page-lead"><div><h2>Заказ-наряд {selected.order.id.slice(0,8).toUpperCase()}</h2>
        <p className="muted">Статус: {STATES[selected.order.status]}; версия: {selected.order.version}</p></div>
        <button className="secondary" onClick={()=>setSelected(null)}>Закрыть</button></div>
      <p>{selected.order.complaint||"Причина обращения не указана"}</p>
      <OrderDocuments organization={organization} orderId={selected.order.id} orderStatus={selected.order.status} canEdit={canEdit}/>
      <h2>Сметы и история согласования</h2>
      {selected.estimates.map(est=><div key={est.id} style={{padding:"14px 0",borderTop:"1px solid #e5e9ec"}}>
        <strong>Редакция №{est.revision} · {money(est.total_minor)} · {est.state}</strong>
        <div className="table-scroll"><table><thead><tr><th>Позиция</th><th>Количество</th><th>Стоимость</th></tr></thead>
        <tbody>{est.lines.map(line=><tr key={line.id}><td>{line.title}</td><td>{line.quantity}</td><td>{money(line.total_minor)}</td></tr>)}</tbody></table></div>
      </div>)}
      {canEdit&&selected.order.status==="draft"&&current?.state==="draft"&&
        <form onSubmit={addLine} style={{marginTop:16}}>
          <h2>Добавить позицию</h2><label>Наименование<input required value={lineTitle} onChange={e=>setLineTitle(e.target.value)}/></label>
          <div className="form-grid"><label>Тип<select value={lineKind} onChange={e=>setLineKind(e.target.value)}>
            <option value="labor">Работа</option><option value="material">Плановая деталь</option><option value="external">Подрядчик</option>
          </select></label><label>Количество<input required min="0.001" step="0.001" type="number" value={quantity} onChange={e=>setQuantity(e.target.value)}/></label></div>
          <label>Цена за единицу, ₽<input type="number" required min="0" step="0.01" value={price} onChange={e=>setPrice(e.target.value)}/></label>
          <button className="primary" disabled={busy}>Добавить в смету</button></form>}
      {findings.length>0&&<section><h2>Дополнительные неисправности</h2>
        <p className="muted">Новые работы не согласованы и не включены в счёт.</p>
        {findings.map(f=><p key={f.id}>{f.title} · {money(f.amount_minor)} · {f.status}</p>)}
      </section>}
      {canEdit&&["in_progress","qa"].includes(selected.order.status)&&<form onSubmit={proposeAdditional}><h2>Зафиксировать дополнительную неисправность</h2><label>Работа<input required value={extraTitle} onChange={e=>setExtraTitle(e.target.value)}/></label><label>Причина<input required value={extraDescription} onChange={e=>setExtraDescription(e.target.value)}/></label><label>Стоимость, ₽<input required type="number" step="0.01" min="0" value={extraPrice} onChange={e=>setExtraPrice(e.target.value)}/></label><button className="secondary" disabled={busy}>Предложить на согласование</button></form>}
      {canEdit&&<div className="quick-actions" style={{marginTop:18}}>
        {selected.order.status==="draft"&&<button disabled={busy} onClick={()=>void action("submit")}>Передать на согласование</button>}
        {selected.order.status==="awaiting"&&<><label>Основание согласования<input value={reference} onChange={e=>setReference(e.target.value)} placeholder="Подписанный документ / подтверждение"/></label>
        <button disabled={busy||!reference.trim()} onClick={()=>void action("approve")}>Зафиксировать согласование</button>
        <button disabled={busy} onClick={()=>void action("reject")}>Отказ клиента</button>
        <button disabled={busy} onClick={()=>void action("revise")}>Новая смета</button></>}
        {selected.order.status==="approved"&&<button disabled={busy} onClick={()=>void action("start")}>Начать ремонт</button>}
        {selected.order.status==="in_progress"&&<button disabled={busy} onClick={()=>void action("qa")}>На проверку</button>}
        {selected.order.status==="qa"&&<><button disabled={busy} onClick={()=>void action("ready")}>Готов</button>
          <button disabled={busy} onClick={()=>void action("rework")}>На доработку</button></>}
      </div>}
      {["approved","in_progress","qa","ready"].includes(selected.order.status)&&<RepairTasks organization={organization} orderId={selected.order.id} role={role}/>}
      {selected.order.status==="ready"&&<div className="notice info">Выдача автомобиля будет доступна после реализации документов и кассы в S08.</div>}
    </section>}
    {creating&&<div className="modal-backdrop"><div className="modal" role="dialog" aria-modal="true" aria-labelledby="wo-new">
      <div className="modal-heading"><h2 id="wo-new">Приёмка автомобиля</h2><button className="secondary" onClick={()=>setCreating(false)}>Закрыть</button></div>
      <form onSubmit={create}><label>Открытый визит<select required value={visit} onChange={e=>setVisit(e.target.value)}>
        <option value="">Выберите визит</option>{active.map(v=><option key={v.id} value={v.id}>{customers.find(c=>c.id===v.customer_id)?.name??"Клиент"} · {vehicles.find(car=>car.id===v.vehicle_id)?.model??"Автомобиль"}</option>)}</select></label>
        <label>Жалоба клиента<input maxLength={3000} value={complaint} onChange={e=>setComplaint(e.target.value)}/></label>
        <button className="primary" disabled={busy||!visit}>Создать заказ-наряд</button></form></div></div>}
  </>;
}
