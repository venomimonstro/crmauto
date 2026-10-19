import {useCallback,useEffect,useRef,useState,type FormEvent} from "react";
import {api} from "./api";
type Branch={id:string;name:string};
type Cashbox={id:string;name:string};
type Invoice={id:string;order_id:string;amount_minor:number;paid_minor:number;refunded_minor:number;debt_minor:number};
type Movement={id:string;invoice_id:string;kind:"income"|"refund";amount_minor:number;method:string;reference:string};
type Order={id:string;status:string};
const rub=(v:number)=>new Intl.NumberFormat("ru-RU",{style:"currency",currency:"RUB"}).format(v/100);
function moneyToMinor(s:string){const n=Number(s);const value=Math.round(n*100);
  if(!Number.isFinite(n)||n<=0||!Number.isSafeInteger(value)||Math.abs(value/100-n)>0.00001)throw Error("Укажите корректную сумму в рублях.");
  return value;
}
export default function CashDesk({organization,role}:{organization:string;role:string}){
 const [branches,setBranches]=useState<Branch[]>([]),[branch,setBranch]=useState("");
 const [boxes,setBoxes]=useState<Cashbox[]>([]),[invoices,setInvoices]=useState<Invoice[]>([]);
 const [movements,setMovements]=useState<Movement[]>([]),[orders,setOrders]=useState<Order[]>([]);
 const [boxName,setBoxName]=useState(""),[selectedBox,setSelectedBox]=useState("");
 const [selectedInvoice,setSelectedInvoice]=useState(""),[selectedOrder,setSelectedOrder]=useState("");
 const [amount,setAmount]=useState(""),[reference,setReference]=useState("");
 const [refundSource,setRefundSource]=useState(""),[refundAmount,setRefundAmount]=useState("");
 const [busy,setBusy]=useState(false),[message,setMessage]=useState(""),[error,setError]=useState("");
 const pending=useRef<{signature:string;key:string}|null>(null);
 const canPay=["owner","manager","cashier"].includes(role);
 const canManage=["owner","manager"].includes(role);
 const headers={organization};
 const refresh=useCallback(async()=>{
   if(!branch)return;
   const [c,i,m]=await Promise.all([
     api<Cashbox[]>("cashboxes?branch_id="+branch,headers),
     api<Invoice[]>("invoices?branch_id="+branch,headers),
     api<Movement[]>("movements?branch_id="+branch,headers),
   ]);
   setBoxes(c);setInvoices(i);setMovements(m);
   setSelectedBox(old=>c.some(b=>b.id===old)?old:c[0]?.id??"");
   setSelectedInvoice(old=>i.some(b=>b.id===old)?old:i.find(x=>x.debt_minor>0)?.id??"");
   if(canManage){
     const w=await api<Order[]>("workorders?branch_id="+branch,headers);
     setOrders(w);
   }
 },[branch,organization,canManage]);
 useEffect(()=>{let live=true;api<Branch[]>("branches",headers).then(x=>{
   if(live){setBranches(x);setBranch(x[0]?.id??"");}}).catch(e=>{if(live)setError(String(e));});
   return()=>{live=false;};},[organization]);
 useEffect(()=>{setBoxes([]);setInvoices([]);setMovements([]);void refresh().catch(e=>setError(String(e)));},[refresh]);
 async function send(path:string,data:unknown){
   const signature=path+JSON.stringify(data);
   if(pending.current?.signature!==signature)pending.current={signature,key:crypto.randomUUID()};
   const response=await api<unknown>(path,{method:"POST",organization,
     idempotencyKey:pending.current.key,data});
   pending.current=null;return response;
 }
 async function perform(action:()=>Promise<void>){
   setBusy(true);setError("");setMessage("");
   try{await action();await refresh();setMessage("Операция сохранена.");}
   catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
 }
 async function addBox(e:FormEvent){e.preventDefault();await perform(async()=>{
   await send("cashboxes",{branch_id:branch,name:boxName});setBoxName("");});}
 async function createInvoice(e:FormEvent){e.preventDefault();await perform(async()=>{
   await send("invoices",{order_id:selectedOrder});setSelectedOrder("");});}
 async function pay(e:FormEvent){e.preventDefault();await perform(async()=>{
   await send("payments",{invoice_id:selectedInvoice,cashbox_id:selectedBox,
     amount_minor:moneyToMinor(amount),method:"cash",reference});setAmount("");setReference("");});}
 async function refund(e:FormEvent){e.preventDefault();await perform(async()=>{
   await send("refunds",{source_id:refundSource,amount_minor:moneyToMinor(refundAmount),
     reference:"Возврат по документу: "+reference});setRefundAmount("");setReference("");});}
 const candidates=orders.filter(o=>["approved","in_progress","qa","ready"].includes(o.status)&&!invoices.some(i=>i.order_id===o.id));
 return <><div className="page-lead"><div><div className="eyebrow">Внутренний учёт</div>
   <h1>Касса и задолженность</h1><p className="muted">Ручная регистрация полученных наличных. Без эквайринга и фискальных чеков.</p></div></div>
   <div className="notice info">Это внутренний журнал CRM, а не онлайн-касса. Платежи картой, банковская сверка и фискализация отключены.</div>
   {error&&<div className="notice error" role="alert">{error}</div>}
   {message&&<div className="notice info" role="status">{message}</div>}
   <section className="card action-card"><label>Филиал<select value={branch} onChange={e=>setBranch(e.target.value)}>
     {branches.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label></section>
   <section className="card action-card" style={{marginTop:16}}><h2>Начисления и задолженность</h2>
     <div className="table-scroll"><table><thead><tr><th>Заказ-наряд</th><th>Начислено</th><th>Оплачено</th><th>Возвраты</th><th>Долг</th></tr></thead>
     <tbody>{invoices.map(i=><tr key={i.id}><td>{i.order_id.slice(0,8)}</td><td>{rub(i.amount_minor)}</td>
       <td>{rub(i.paid_minor)}</td><td>{rub(i.refunded_minor)}</td><td>{rub(i.debt_minor)}</td></tr>)}</tbody></table>
       {!invoices.length&&<p className="table-empty">Начислений пока нет.</p>}</div></section>
   {canManage&&<section className="card action-card" style={{marginTop:16}}>
     <h2>Подготовка кассы</h2><div className="form-grid">
       <form onSubmit={addBox}><label>Название кассы<input required value={boxName} onChange={e=>setBoxName(e.target.value)}/></label>
         <button className="secondary" disabled={busy||!branch}>Создать кассу</button></form>
       <form onSubmit={createInvoice}><label>Заказ-наряд с согласованной сметой<select required value={selectedOrder}
         onChange={e=>setSelectedOrder(e.target.value)}><option value="">Выберите</option>
         {candidates.map(x=><option key={x.id} value={x.id}>{x.id.slice(0,8)} · {x.status}</option>)}</select></label>
         <button className="secondary" disabled={busy||!selectedOrder}>Создать начисление</button></form>
     </div></section>}
   {canPay&&<section className="card action-card" style={{marginTop:16}}><h2>Зарегистрировать наличные</h2>
     <form onSubmit={pay}><div className="form-grid"><label>Начисление<select value={selectedInvoice} required
       onChange={e=>setSelectedInvoice(e.target.value)}><option value="">Выберите</option>
       {invoices.filter(x=>x.debt_minor>0).map(i=><option key={i.id} value={i.id}>{i.order_id.slice(0,8)} · долг {rub(i.debt_minor)}</option>)}</select></label>
       <label>Касса<select required value={selectedBox} onChange={e=>setSelectedBox(e.target.value)}>
       <option value="">Выберите</option>{boxes.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label></div>
       <div className="form-grid"><label>Сумма, ₽<input required type="number" min="0.01" step="0.01"
       value={amount} onChange={e=>setAmount(e.target.value)}/></label>
       <label>Основание / внутренний номер<input required value={reference}
       onChange={e=>setReference(e.target.value)}/></label></div>
       <button className="primary" disabled={busy||!selectedBox||!selectedInvoice}>Зафиксировать получение наличных</button>
     </form></section>}
   <section className="card action-card" style={{marginTop:16}}><h2>Журнал операций</h2>
     <div className="table-scroll"><table><thead><tr><th>Тип</th><th>Сумма</th><th>Основание</th></tr></thead>
     <tbody>{movements.map(x=><tr key={x.id}><td>{x.kind==="income"?"Поступление":"Возврат"}</td>
       <td>{rub(x.amount_minor)}</td><td>{x.reference}</td></tr>)}</tbody></table>
     {!movements.length&&<p className="table-empty">Операций пока нет.</p>}</div></section>
   {canManage&&<section className="card action-card" style={{marginTop:16}}><h2>Возврат наличных</h2>
     <form onSubmit={refund}><label>Исходный платёж<select required value={refundSource}
       onChange={e=>setRefundSource(e.target.value)}><option value="">Выберите</option>
       {movements.filter(x=>x.kind==="income"&&x.method==="cash").map(x=>
       <option key={x.id} value={x.id}>{x.id.slice(0,8)} · {rub(x.amount_minor)}</option>)}</select></label>
       <div className="form-grid"><label>Сумма возврата, ₽<input required min="0.01" type="number" step="0.01"
         value={refundAmount} onChange={e=>setRefundAmount(e.target.value)}/></label>
         <label>Основание возврата<input required value={reference}
         onChange={e=>setReference(e.target.value)}/></label></div>
       <button className="secondary" disabled={busy||!refundSource}>Зафиксировать возврат</button></form></section>}
 </>;
}
