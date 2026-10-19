import {useEffect,useState} from "react";
import {api} from "./api";
type Branch={id:string;name:string};
type Donor={id:string;description:string;vin:string;acquisition_cost_minor:number;allocated_cost_minor:number};
type Part={id:string;inventory_code:string;name:string;state:string;allocated_cost_minor:number;target_price_minor:number};
const rub=(n:number)=>new Intl.NumberFormat("ru-RU",{style:"currency",currency:"RUB"}).format(n/100);
export default function Dismantling({organization,role}:{organization:string;role:string}){
 const [branches,setBranches]=useState<Branch[]>([]),[branch,setBranch]=useState("");
 const [donors,setDonors]=useState<Donor[]>([]),[selected,setSelected]=useState("");
 const [parts,setParts]=useState<Part[]>([]),[description,setDescription]=useState("");
 const [cost,setCost]=useState("0"),[notice,setNotice]=useState(""),[busy,setBusy]=useState(false);
 const editable=["owner","manager","stock"].includes(role);
 useEffect(()=>{api<Branch[]>("branches",{organization}).then(x=>{
   setBranches(x);setBranch(x[0]?.id??"");}).catch(e=>setNotice(String(e)));},[organization]);
 useEffect(()=>{if(!branch)return;api<Donor[]>("donors?branch_id="+branch,{organization})
  .then(setDonors).catch(e=>setNotice(String(e)));},[organization,branch]);
 useEffect(()=>{if(!selected){setParts([]);return;}api<Part[]>("salvaged-parts?donor_id="+selected,{organization})
  .then(setParts).catch(e=>setNotice(String(e)));},[organization,selected]);
 async function create(e:React.FormEvent){
  e.preventDefault();const minor=Math.round(Number(cost)*100);
  if(!Number.isSafeInteger(minor)||minor<0){setNotice("Некорректная сумма затрат.");return;}
  setBusy(true);setNotice("");
  try{await api("donors",{method:"POST",organization,idempotencyKey:crypto.randomUUID(),
    data:{branch_id:branch,description,acquisition_cost_minor:minor}});
   setDescription("");const rows=await api<Donor[]>("donors?branch_id="+branch,{organization});
   setDonors(rows);setNotice("Автомобиль-донор зарегистрирован.");}
  catch(err){setNotice(String(err));}finally{setBusy(false);}
 }
 return <><div className="page-lead"><div><div className="eyebrow">Уникальные детали</div>
 <h1>Авторазбор</h1><p className="muted">Учёт автомобилей-доноров и штучных запасных частей без двойного резервирования.</p></div></div>
 {notice&&<div className="notice info" role="status">{notice}</div>}
 <section className="card action-card"><label>Филиал<select value={branch} onChange={e=>{setBranch(e.target.value);setSelected("");}}>
 {branches.map(x=><option value={x.id} key={x.id}>{x.name}</option>)}</select></label>
 {editable&&<form onSubmit={create} style={{marginTop:20}}>
 <div className="form-grid"><label>Описание донора<input value={description} onChange={e=>setDescription(e.target.value)}
 required maxLength={250} placeholder="BMW X5, кузов, состояние"/></label>
 <label>Закупочные затраты, ₽<input value={cost} onChange={e=>setCost(e.target.value)} type="number"
 min="0" step=".01" required/></label></div>
 <button className="primary" disabled={!branch||busy}>Добавить донора</button></form>}</section>
 <section className="card action-card" style={{marginTop:16}}><h2>Автомобили-доноры</h2>
 <div className="table-scroll"><table><thead><tr><th>Автомобиль</th><th>Закупка</th><th>Распределено</th><th>Детали</th></tr></thead><tbody>
 {donors.map(x=><tr key={x.id}><td>{x.description}</td><td>{rub(x.acquisition_cost_minor)}</td>
 <td>{rub(x.allocated_cost_minor)}</td><td><button className="secondary" onClick={()=>setSelected(x.id)}>Открыть</button></td></tr>)}
 </tbody></table></div>
 {selected&&<><h2 style={{marginTop:25}}>Демонтированные детали</h2>
 <div className="table-scroll"><table><thead><tr><th>Учётный код</th><th>Название</th><th>Состояние</th><th>Плановая цена</th></tr></thead><tbody>
 {parts.map(x=><tr key={x.id}><td>{x.inventory_code}</td><td>{x.name}</td>
 <td>{x.state}</td><td>{rub(x.target_price_minor)}</td></tr>)}</tbody></table>
 {!parts.length&&<p className="table-empty">Детали пока не внесены. API регистрации деталей доступен после создания ячейки хранения.</p>}
 </div></>}</section>
 <p className="muted">Продажа и показатель окупаемости ещё не реализованы. Указанные закупочные затраты — данные внутреннего учёта, а не подтверждённая оплата.</p></>;
}
