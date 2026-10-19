import {useCallback,useEffect,useRef,useState,type FormEvent} from "react";
import {api} from "./api";
type Branch={id:string;name:string};type Warehouse={id:string;branch_id:string;name:string;active:boolean};
type Part={id:string;sku:string;name:string;condition:string};
type Stock={id:string;warehouse_id:string;part_id:string;quantity:number;reserved:number;available:number};
type Supplier={id:string;name:string;inn:string};
type PurchaseLine={id:string;part_id:string;ordered:number;received:number;unit_cost_minor:number};
type Purchase={id:string;warehouse_id:string;supplier_id:string;status:string;lines:PurchaseLine[]};
function msg(e:unknown){return e instanceof Error?e.message:"Произошла ошибка";}
export default function Inventory({organization,role}: {organization:string;role:string}){
  const [branches,setBranches]=useState<Branch[]>([]),[branch,setBranch]=useState("");
  const [warehouses,setWarehouses]=useState<Warehouse[]>([]),[warehouse,setWarehouse]=useState("");
  const [parts,setParts]=useState<Part[]>([]),[stock,setStock]=useState<Stock[]>([]);
  const [suppliers,setSuppliers]=useState<Supplier[]>([]),[purchases,setPurchases]=useState<Purchase[]>([]);
  const [tab,setTab]=useState<"stock"|"purchases">("stock");
  const [sku,setSku]=useState(""),[partName,setPartName]=useState("");
  const [supplierName,setSupplierName]=useState(""),[selectedSupplier,setSelectedSupplier]=useState("");
  const [warehouseName,setWarehouseName]=useState("");
  const [selectedPurchase,setSelectedPurchase]=useState("");
  const [selectedPart,setSelectedPart]=useState("");
  const [ordered,setOrdered]=useState("1"),[unitCost,setUnitCost]=useState("0");
  const [busy,setBusy]=useState(false),[error,setError]=useState(""),[info,setInfo]=useState("");
  const pending=useRef<{signature:string;key:string}|null>(null);
  const canEdit=["owner","manager","stock"].includes(role);
  const headers={organization};
  const send=async(path:string,data:unknown)=>{
    const signature=path+JSON.stringify(data);
    if(pending.current?.signature!==signature)pending.current={signature,key:crypto.randomUUID()};
    const result=await api<unknown>(path,{method:"POST",organization,idempotencyKey:pending.current.key,data});
    pending.current=null;return result;
  };
  const refresh=useCallback(async()=>{
    if(!branch)return;
    const [w,p,s]=await Promise.all([
      api<Warehouse[]>("warehouses?branch_id="+branch,headers),
      api<Part[]>("parts",headers),
      api<Supplier[]>("suppliers",headers),
    ]);setWarehouses(w);setParts(p);setSuppliers(s);
  },[branch,organization]);
  useEffect(()=>{let alive=true;api<Branch[]>("branches",headers).then(rows=>{
    if(!alive)return;setBranches(rows);setBranch(x=>rows.some(r=>r.id===x)?x:rows[0]?.id??"");
  }).catch(e=>setError(msg(e)));return()=>{alive=false;};},[organization]);
  useEffect(()=>{setWarehouses([]);setWarehouse("");setStock([]);setPurchases([]);
    void refresh().catch(e=>setError(msg(e)));},[refresh]);
  useEffect(()=>{setWarehouse(x=>warehouses.some(w=>w.id===x)?x:warehouses[0]?.id??"");},[warehouses]);
  const refreshDetails=useCallback(async()=>{
    if(!branch||!warehouse)return;
    const [stocks,purchasesList]=await Promise.all([
      api<Stock[]>("stocks?warehouse_id="+warehouse,headers),
      api<Purchase[]>("purchases?branch_id="+branch,headers),
    ]);setStock(stocks);setPurchases(purchasesList);
  },[branch,warehouse,organization]);
  useEffect(()=>{void refreshDetails().catch(e=>setError(msg(e)));},[refreshDetails]);
  async function run(job:()=>Promise<unknown>){
    setBusy(true);setError("");setInfo("");
    try{await job();await refresh();await refreshDetails();setInfo("Операция выполнена.");}
    catch(e){setError(msg(e));}finally{setBusy(false);}
  }
  async function createPart(e:FormEvent){e.preventDefault();await run(async()=>{
    await send("parts",{sku,name:partName,condition:"new"});setSku("");setPartName("");
  });}
  async function createWarehouse(e:FormEvent){e.preventDefault();await run(async()=>{
    await send("warehouses",{branch_id:branch,name:warehouseName});setWarehouseName("");
  });}
  async function createSupplier(e:FormEvent){e.preventDefault();await run(async()=>{
    await send("suppliers",{name:supplierName});setSupplierName("");
  });}
  async function createPurchase(){
    await run(async()=>{const result=await send("purchases",{branch_id:branch,warehouse_id:warehouse,
      supplier_id:selectedSupplier}) as Purchase;setSelectedPurchase(result.id);});
  }
  async function addLine(e:FormEvent){e.preventDefault();const cents=Math.round(Number(unitCost)*100);
    if(!Number.isSafeInteger(cents)||cents<0){setError("Неверная закупочная цена.");return;}
    await run(()=>send("purchases/"+selectedPurchase+"/lines",{
      part_id:selectedPart,ordered:Number(ordered),unit_cost_minor:cents,
    }));
  }
  async function receive(purchase:Purchase,line:PurchaseLine){
    const value=prompt("Сколько единиц получено?",String(line.ordered-line.received));
    if(value===null)return;const quantity=Number(value);
    if(!Number.isInteger(quantity)||quantity<=0){setError("Укажите целое положительное количество.");return;}
    await run(()=>send("purchases/"+purchase.id+"/receive",{line_id:line.id,quantity}));
  }
  const purchase=purchases.find(p=>p.id===selectedPurchase);
  return <><div className="page-lead"><div><div className="eyebrow">Учёт товаров</div><h1>Запчасти и закупки</h1>
    <p className="muted">Остатки, резервирование и документированная приёмка от поставщика.</p></div></div>
    {error&&<div className="notice error" role="alert">{error}</div>}
    {info&&<div className="notice info" role="status">{info}</div>}
    <section className="card action-card">
      <div className="form-grid"><label>Филиал<select value={branch} onChange={e=>setBranch(e.target.value)}>
        {branches.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
        <label>Склад<select value={warehouse} onChange={e=>setWarehouse(e.target.value)}>
        {warehouses.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label></div>
      <div className="quick-actions" style={{margin:"15px 0"}}>
        <button onClick={()=>setTab("stock")} aria-pressed={tab==="stock"}>Остатки</button>
        <button onClick={()=>setTab("purchases")} aria-pressed={tab==="purchases"}>Закупки</button></div>
    </section>
    {tab==="stock"&&<section className="card action-card" style={{marginTop:16}}>
      <h2>Остатки склада</h2><div className="table-scroll"><table><thead>
      <tr><th>Артикул</th><th>Название</th><th>Физически</th><th>Резерв</th><th>Доступно</th></tr></thead>
      <tbody>{stock.map(s=>{const p=parts.find(p=>p.id===s.part_id);return <tr key={s.id}>
        <td>{p?.sku??"—"}</td><td>{p?.name??"—"}</td><td>{s.quantity}</td><td>{s.reserved}</td><td>{s.available}</td></tr>;})}</tbody>
      </table>{!stock.length&&<p className="table-empty">Пока нет товаров на складе.</p>}</div>
      {canEdit&&<div className="form-grid" style={{marginTop:24}}>
        <form onSubmit={createWarehouse}><h2>Добавить склад</h2><label>Название<input required value={warehouseName} onChange={e=>setWarehouseName(e.target.value)}/></label>
          <button className="secondary" disabled={busy||!branch}>Создать склад</button></form>
        <form onSubmit={createPart}><h2>Добавить товар</h2>
          <label>Артикул<input required value={sku} onChange={e=>setSku(e.target.value)}/></label>
          <label>Название<input required value={partName} onChange={e=>setPartName(e.target.value)}/></label>
          <button className="secondary" disabled={busy}>Создать карточку</button></form></div>}
    </section>}
    {tab==="purchases"&&<section className="card action-card" style={{marginTop:16}}>
      <h2>Заказы поставщикам</h2>
      {canEdit&&<div className="form-grid">
        <form onSubmit={createSupplier}><h2>Новый поставщик</h2>
          <label>Название<input value={supplierName} onChange={e=>setSupplierName(e.target.value)} required/></label>
          <button className="secondary" disabled={busy}>Сохранить поставщика</button></form>
        <div><h2>Новый заказ поставщику</h2>
          <label>Поставщик<select value={selectedSupplier} onChange={e=>setSelectedSupplier(e.target.value)}>
          <option value="">Выберите</option>{suppliers.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
          <button className="primary" style={{marginTop:12}} disabled={busy||!warehouse||!selectedSupplier} onClick={()=>void createPurchase()}>Создать заказ</button></div>
      </div>}
      <div className="table-scroll" style={{marginTop:20}}><table><thead><tr><th>Заказ</th><th>Поставщик</th><th>Статус</th><th>Действие</th></tr></thead>
        <tbody>{purchases.map(p=><tr key={p.id}><td>{p.id.slice(0,8)}</td><td>{suppliers.find(s=>s.id===p.supplier_id)?.name??"—"}</td>
          <td>{p.status}</td><td><button className="secondary" onClick={()=>setSelectedPurchase(p.id)}>Открыть</button></td></tr>)}</tbody></table></div>
      {purchase&&<div style={{marginTop:24}}><h2>Заказ {purchase.id.slice(0,8)}</h2>
        <p className="muted">Статус: {purchase.status}</p>
        <div className="table-scroll"><table><thead><tr><th>Деталь</th><th>Заказано</th><th>Принято</th><th>Приёмка</th></tr></thead>
          <tbody>{purchase.lines.map(line=><tr key={line.id}><td>{parts.find(p=>p.id===line.part_id)?.name??line.part_id}</td><td>{line.ordered}</td>
            <td>{line.received}</td><td>{canEdit&&["ordered","partial"].includes(purchase.status)&&line.ordered>line.received&&
            <button className="secondary" disabled={busy} onClick={()=>void receive(purchase,line)}>Принять часть</button>}</td></tr>)}</tbody></table></div>
        {canEdit&&purchase.status==="draft"&&<>
          <form onSubmit={addLine}><div className="form-grid"><label>Деталь<select required value={selectedPart} onChange={e=>setSelectedPart(e.target.value)}>
            <option value="">Выберите</option>{parts.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
            <label>Количество<input min={1} type="number" required value={ordered} onChange={e=>setOrdered(e.target.value)}/></label></div>
            <label>Закупочная цена, ₽<input type="number" required step="0.01" min="0" value={unitCost} onChange={e=>setUnitCost(e.target.value)}/></label>
            <button className="secondary" disabled={busy||!selectedPart}>Добавить строку</button></form>
          <button className="primary" style={{marginTop:12}} disabled={busy||!purchase.lines.length}
            onClick={()=>void run(()=>send("purchases/"+purchase.id+"/actions/submit",{}))}>Отправить заказ</button>
        </>}
      </div>}
    </section>}
  </>;
}
