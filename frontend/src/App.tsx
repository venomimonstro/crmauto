import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import {
  Activity, BarChart3, CalendarDays, CarFront, CheckCircle2, ChevronDown,
  CircleHelp, ClipboardList, CreditCard, Gauge, LayoutDashboard, LogOut,
  Menu, Package, Plus, Search, Settings, ShieldCheck, ShoppingCart, Users, Wrench, X,
} from "lucide-react";
import { api, ApiError, type Customer, type Organization, type SessionUser, type Vehicle } from "./api";

type Area = "dashboard" | "customers" | "vehicles" | "orders" | "lifts" | "tyres" |
  "inventory" | "donors" | "suppliers" | "personnel" | "cash" | "reports" | "settings";
const navigation: { key: Area; title: string; icon: typeof Users; ready: boolean }[] = [
  { key: "dashboard", title: "Главная", icon: LayoutDashboard, ready: true },
  { key: "customers", title: "Клиенты", icon: Users, ready: true },
  { key: "vehicles", title: "Автомобили", icon: CarFront, ready: true },
  { key: "orders", title: "Заказ-наряды", icon: ClipboardList, ready: false },
  { key: "lifts", title: "Подъёмники", icon: Gauge, ready: false },
  { key: "tyres", title: "Шиномонтаж", icon: CalendarDays, ready: false },
  { key: "inventory", title: "Запчасти и склад", icon: Package, ready: false },
  { key: "donors", title: "Авторазбор", icon: Wrench, ready: false },
  { key: "suppliers", title: "Закупки и продажи", icon: ShoppingCart, ready: false },
  { key: "personnel", title: "Персонал", icon: Users, ready: false },
  { key: "cash", title: "Касса", icon: CreditCard, ready: false },
  { key: "reports", title: "Отчёты", icon: BarChart3, ready: false },
  { key: "settings", title: "Настройки", icon: Settings, ready: false },
];
function errorText(error: unknown): string {
  return error instanceof Error ? error.message : "Непредвиденная ошибка.";
}
function Notice({ children, type = "error" }: { children: ReactNode; type?: "error" | "info" }) {
  return <div className={"notice " + type} role={type === "error" ? "alert" : "status"}>{children}</div>;
}
function Auth({ afterLogin }: { afterLogin: () => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  async function submit(e: FormEvent) {
    e.preventDefault(); setSubmitting(true); setError("");
    try {
      await api("auth/login", { method: "POST", data: { email, password } });
      await afterLogin();
    } catch (err) { setError(errorText(err)); }
    finally { setSubmitting(false); }
  }
  return <div className="auth-layout">
    <aside className="auth-intro">
      <div className="brand light"><span className="brand-mark"><Wrench size={21}/></span> CRM <strong>Автосервис</strong></div>
      <h1>Управляйте сервисом. Контролируйте прибыль.</h1>
      <p>Клиенты, автомобили, ремонт, запчасти и авторазбор — в одной системе.</p>
      <div className="auth-features"><span><ShieldCheck size={17}/> Изоляция данных компаний</span>
        <span><Activity size={17}/> Сквозной учёт операций</span></div>
    </aside>
    <main className="auth-main"><div className="login-card">
      <div className="eyebrow">Личный кабинет</div><h2>Вход в систему</h2>
      <p className="muted">Используйте зарегистрированную учётную запись.</p>
      <form onSubmit={submit}><label>Электронная почта<input type="email" autoComplete="username" required value={email} onChange={e=>setEmail(e.target.value)} placeholder="name@company.ru"/></label>
      <label>Пароль<input type="password" minLength={12} autoComplete="current-password" required value={password} onChange={e=>setPassword(e.target.value)} placeholder="Не менее 12 символов"/></label>
      {error && <Notice>{error}</Notice>}
      <button className="primary wide" disabled={submitting}>{submitting ? "Входим…" : "Войти в кабинет"}</button></form>
      <Notice type="info">Открытая регистрация и восстановление доступа станут доступны после реализации проверки почты и защиты учётных записей.</Notice>
    </div></main>
  </div>;
}
function CreateOrganization({ onCreated }: { onCreated: () => Promise<void> }) {
  const [name, setName] = useState(""); const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try { await api("organizations", { method: "POST", data: { name } }); await onCreated(); }
    catch(err) { setError(errorText(err)); } finally { setBusy(false); }
  }
  return <main className="empty-workspace"><div className="card create-org">
    <span className="circle"><Wrench/></span><h1>Создайте рабочее пространство</h1>
    <p className="muted">Первый шаг: организация и основной филиал. Данные других компаний будут недоступны.</p>
    <form onSubmit={save}><label>Название автосервиса<input value={name} onChange={e=>setName(e.target.value)} minLength={2} maxLength={200} required placeholder="Например, Автоцентр Восток"/></label>
      {error && <Notice>{error}</Notice>}<button disabled={busy} className="primary wide">{busy?"Сохраняем…":"Создать организацию"}</button></form>
  </div></main>;
}
function Dashboard({ customers, vehicles, loading, navigate }: {
  customers: Customer[]; vehicles: Vehicle[]; loading: boolean; navigate:(s:Area)=>void
}) {
  return <><div className="page-lead"><div><div className="eyebrow">Рабочее пространство</div>
    <h1>Обзор бизнеса</h1><p className="muted">Сейчас доступны основные справочники. Финансовые показатели появятся после разработки учётных модулей.</p></div></div>
    <div className="stats"><div className="stat"><span>Клиенты <Users size={18}/></span><strong>{loading ? "—":customers.length}</strong><small>Первые 100 записей</small></div>
      <div className="stat"><span>Автомобили <CarFront size={18}/></span><strong>{loading?"—":vehicles.length}</strong><small>Первые 100 записей</small></div>
      <div className="stat"><span>Заказ-наряды <ClipboardList size={18}/></span><strong>—</strong><small>Модуль в разработке</small></div>
      <div className="stat"><span>Склад <Package size={18}/></span><strong>—</strong><small>Модуль в разработке</small></div>
    </div>
    <section className="card action-card"><h2>Быстрые действия</h2>
      <div className="quick-actions"><button onClick={()=>navigate("customers")}><Users size={20}/> Работа с клиентами</button>
        <button onClick={()=>navigate("vehicles")}><CarFront size={20}/> Работа с автомобилями</button></div>
    </section></>;
}
function Customers({ organization, items, refresh, canEdit }: { organization:string; items:Customer[]; refresh:()=>Promise<void>; canEdit:boolean }) {
  const [adding,setAdding]=useState(false); const [query,setQuery]=useState("");
  const [name,setName]=useState(""); const [kind,setKind]=useState<"person"|"company">("person");
  const [phone,setPhone]=useState(""); const [email,setEmail]=useState(""); const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const filtered=items.filter(x=>[x.name,x.phone,x.email].some(v=>v.toLowerCase().includes(query.toLowerCase())));
  async function create(e:FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try {
      await api("customers", { method:"POST", organization,
        idempotencyKey:crypto.randomUUID(), data:{name, kind, phone, email} });
      setAdding(false);setName("");setPhone("");setEmail("");await refresh();
    } catch(err){setError(errorText(err));}finally{setBusy(false);}
  }
  return <><div className="page-lead"><div><div className="eyebrow">CRM</div><h1>Клиенты</h1>
    <p className="muted">Единая база клиентов автосервиса и истории обслуживания.</p></div>
    {canEdit&&<button className="primary" onClick={()=>{setAdding(true);setError("");}}><Plus size={17}/> Добавить клиента</button>}</div>
    <section className="card table-card"><div className="table-head"><h2>Список клиентов</h2>
      <label className="search-input"><Search size={17}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Поиск по имени, телефону, почте" aria-label="Поиск клиентов"/></label></div>
      <div className="table-scroll"><table><thead><tr><th>Клиент</th><th>Контакты</th><th>Тип</th></tr></thead>
      <tbody>{filtered.map(c=><tr key={c.id}><td><strong>{c.name}</strong></td><td>{c.phone || c.email || "—"}</td><td>{c.kind==="company"?"Организация":"Физлицо"}</td></tr>)}</tbody></table>
      {filtered.length===0&&<p className="table-empty">Клиенты не найдены. Создайте первую карточку или измените поиск.</p>}</div></section>
    {adding&&<div className="modal-backdrop" role="presentation"><div className="modal" role="dialog" aria-modal="true" aria-labelledby="customer-title">
      <div className="modal-heading"><h2 id="customer-title">Новый клиент</h2><button className="icon-button" aria-label="Закрыть" onClick={()=>setAdding(false)}><X/></button></div>
      <form onSubmit={create}><label>Тип<select value={kind} onChange={e=>setKind(e.target.value as "person"|"company")}><option value="person">Физическое лицо</option><option value="company">Организация</option></select></label>
      <label>Имя / организация<input autoFocus value={name} onChange={e=>setName(e.target.value)} minLength={2} maxLength={200} required/></label>
      <label>Телефон<input type="tel" value={phone} onChange={e=>setPhone(e.target.value)} placeholder="+7 999 123-45-67"/></label>
      <label>Электронная почта<input type="email" value={email} onChange={e=>setEmail(e.target.value)}/></label>
      {error&&<Notice>{error}</Notice>}
      <div className="modal-footer"><button type="button" className="secondary" onClick={()=>setAdding(false)}>Отменить</button>
        <button disabled={busy} className="primary">{busy?"Сохранение…":"Создать клиента"}</button></div></form>
    </div></div>}
  </>;
}
function Vehicles({ organization, vehicles, customers, refresh, canEdit }: {
  organization:string; vehicles:Vehicle[]; customers:Customer[];refresh:()=>Promise<void>;canEdit:boolean
}) {
  const [adding,setAdding]=useState(false);const [query,setQuery]=useState("");
  const [make,setMake]=useState("");const [model,setModel]=useState("");
  const [vin,setVin]=useState("");const [plate,setPlate]=useState("");
  const [owner,setOwner]=useState("");const [error,setError]=useState("");const [busy,setBusy]=useState(false);
  const filtered=vehicles.filter(v=>[v.make,v.model,v.plate,v.vin].some(value=>value.toLowerCase().includes(query.toLowerCase())));
  async function create(e:FormEvent){
    e.preventDefault();setError("");setBusy(true);
    try {
      await api("vehicles",{method:"POST",organization,idempotencyKey:crypto.randomUUID(),
        data:{make,model,vin,plate,...(owner?{owner_id:owner}:{})}});
      setAdding(false);setMake("");setModel("");setVin("");setPlate("");setOwner("");await refresh();
    }catch(err){setError(errorText(err));}finally{setBusy(false);}
  }
  return <><div className="page-lead"><div><div className="eyebrow">Автопарк клиентов</div><h1>Автомобили</h1>
      <p className="muted">VIN, госномер и связь с клиентом. История владельцев сохраняется.</p></div>
      {canEdit&&<button className="primary" onClick={()=>{setAdding(true);setError("");}}><Plus size={17}/> Добавить автомобиль</button>}</div>
      <section className="card table-card"><div className="table-head"><h2>Автомобили</h2>
        <label className="search-input"><Search size={17}/><input aria-label="Поиск автомобилей" value={query}
        onChange={e=>setQuery(e.target.value)} placeholder="Марка, модель, VIN или номер"/></label></div>
        <div className="table-scroll"><table><thead><tr><th>Автомобиль</th><th>Госномер</th><th>VIN</th><th>Владелец</th></tr></thead>
        <tbody>{filtered.map(v=><tr key={v.id}><td><strong>{v.make} {v.model}</strong></td><td>{v.plate||"—"}</td>
          <td className="mono">{v.vin||"—"}</td><td>{customers.find(c=>c.id===v.current_owner)?.name||"Не указан"}</td></tr>)}</tbody></table>
        {filtered.length===0&&<p className="table-empty">Автомобили не найдены.</p>}</div></section>
      {adding&&<div className="modal-backdrop" role="presentation"><div className="modal" role="dialog" aria-modal="true" aria-labelledby="vehicle-title">
        <div className="modal-heading"><h2 id="vehicle-title">Новый автомобиль</h2><button className="icon-button" aria-label="Закрыть" onClick={()=>setAdding(false)}><X/></button></div>
        <form onSubmit={create}><div className="form-grid"><label>Марка<input autoFocus required maxLength={100} value={make} onChange={e=>setMake(e.target.value)} placeholder="Toyota"/></label>
        <label>Модель<input required maxLength={100} value={model} onChange={e=>setModel(e.target.value)} placeholder="Camry"/></label></div>
        <label>VIN (если известен)<input className="mono" maxLength={17} value={vin} onChange={e=>setVin(e.target.value.toUpperCase())} placeholder="17 символов"/></label>
        <label>Госномер<input maxLength={20} value={plate} onChange={e=>setPlate(e.target.value.toUpperCase())}/></label>
        <label>Владелец<select value={owner} onChange={e=>setOwner(e.target.value)}><option value="">Не указан</option>
          {customers.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
        {error&&<Notice>{error}</Notice>}<div className="modal-footer"><button type="button" className="secondary" onClick={()=>setAdding(false)}>Отменить</button>
        <button className="primary" disabled={busy}>{busy?"Сохраняем…":"Создать автомобиль"}</button></div></form>
      </div></div>}
    </>;
}
function ComingSoon({ name }: { name:string }) {
  return <div className="coming-soon"><span className="circle"><Wrench/></span>
    <h1>{name}</h1><p>Этот раздел находится в разработке. Учётные операции появятся после проверки серверной логики и тестов.</p>
    <Notice type="info">В настоящей системе не используются фиктивные записи, оплаты или остатки.</Notice></div>;
}
export default function App(){
  const [session,setSession]=useState<SessionUser|null>(null);
  const [loading,setLoading]=useState(true);
  const [organizationId,setOrganizationId]=useState("");
  const [area,setArea]=useState<Area>("dashboard");
  const [customers,setCustomers]=useState<Customer[]>([]);
  const [vehicles,setVehicles]=useState<Vehicle[]>([]);
  const [dataLoading,setDataLoading]=useState(false);
  const [error,setError]=useState("");const [menuOpen,setMenuOpen]=useState(false);
  const organizations=session?.organizations??[];
  const activeOrg:Organization|undefined=useMemo(()=>organizations.find(o=>o.id===organizationId)??organizations[0],[organizations,organizationId]);
  const loadSession=useCallback(async()=>{
    try{
      const user=await api<SessionUser>("auth/me");
      setSession(user);setOrganizationId(prev=>user.organizations.some(o=>o.id===prev)?prev:user.organizations[0]?.id??"");
    }catch(err){if(err instanceof ApiError&&(err.status===401||err.status===403)){setSession(null);}
      else setError(errorText(err));}
    finally{setLoading(false);}
  },[]);
  useEffect(()=>{void loadSession();},[loadSession]);
  const refreshData=useCallback(async()=>{
    if(!activeOrg)return;
    setDataLoading(true);setError("");
    try{
      const role=activeOrg.role;
      const canCustomers=["owner","manager","adviser","viewer"].includes(role);
      const canVehicles=canCustomers||["mechanic","stock"].includes(role);
      const [c,v]=await Promise.all([
        canCustomers ? api<Customer[]>("customers",{organization:activeOrg.id}) : Promise.resolve([] as Customer[]),
        canVehicles ? api<Vehicle[]>("vehicles",{organization:activeOrg.id}) : Promise.resolve([] as Vehicle[]),
      ]);
      setCustomers(c);setVehicles(v);
    }catch(err){setError(errorText(err));}
    finally{setDataLoading(false);}
  },[activeOrg?.id]);
  useEffect(()=>{void refreshData();},[refreshData]);
  async function logOut(){try{await api("auth/logout",{method:"POST"});}finally{
    setSession(null);setCustomers([]);setVehicles([]);setArea("dashboard");
  }}
  function navigate(next:Area){setArea(next);setMenuOpen(false);}
  if(loading)return <div className="loading"><Activity size={24}/> Загрузка CRM…</div>;
  if(!session)return <Auth afterLogin={loadSession}/>;
  if(!activeOrg)return <CreateOrganization onCreated={loadSession}/>;
  const selected=navigation.find(n=>n.key===area);
  return <div className="app-shell">
    {menuOpen&&<button className="mobile-scrim" onClick={()=>setMenuOpen(false)} aria-label="Закрыть меню"/>}
    <aside className={"sidebar "+(menuOpen?"open":"")}>
      <div className="brand"><span className="brand-mark"><Wrench size={20}/></span><span>CRM <strong>Автосервис</strong></span></div>
      <div className="workspace-switch"><span className="avatar-org">{activeOrg.name.slice(0,1).toUpperCase()}</span>
        <div className="workspace-name"><strong>{activeOrg.name}</strong><small>Роль: {activeOrg.role}</small></div><ChevronDown size={15}/></div>
      {organizations.length>1&&<label className="org-select-label">Организация<select value={activeOrg.id} onChange={e=>setOrganizationId(e.target.value)}>
        {organizations.map(o=><option key={o.id} value={o.id}>{o.name}</option>)}</select></label>}
      <div className="menu-heading">РАБОЧЕЕ ПРОСТРАНСТВО</div>
      <nav aria-label="Разделы CRM">{navigation.filter(item=>item.key!=="customers"||["owner","manager","adviser","viewer"].includes(activeOrg.role)).filter(item=>item.key!=="vehicles"||activeOrg.role!=="cashier").map(item=>{
        const Icon=item.icon;return <button key={item.key} aria-current={area===item.key?"page":undefined}
          className={"nav-link "+(area===item.key?"active":"")} onClick={()=>navigate(item.key)}>
          <Icon size={18}/><span>{item.title}</span>{!item.ready&&<span className="lock-mark" title="В разработке">·</span>}</button>;
      })}</nav>
      <div className="sidebar-bottom"><button className="nav-link" onClick={()=>navigate("settings")}><CircleHelp size={18}/> Справка</button>
        <button className="nav-link" onClick={()=>void logOut()}><LogOut size={18}/> Выйти</button></div>
    </aside>
    <div className="main-column">
      <header className="topbar"><div className="topbar-left"><button className="icon-button mobile-toggle" aria-label="Открыть меню" onClick={()=>setMenuOpen(true)}><Menu/></button>
        <span className="breadcrumbs">CRM <span>/</span> {selected?.title}</span></div>
        <div className="topbar-right"><span className="health-badge"><CheckCircle2 size={15}/> Тестовая сборка</span>
          <span className="user-pill">{session.email.slice(0,1).toUpperCase()}</span></div></header>
      <main className="content" id="main">
        {error&&<Notice>{error}</Notice>}
        {area==="dashboard"?<Dashboard customers={customers} vehicles={vehicles} loading={dataLoading} navigate={navigate}/>:
         area==="customers"?<Customers organization={activeOrg.id} items={customers} refresh={refreshData} canEdit={["owner","manager","adviser"].includes(activeOrg.role)}/>:
         area==="vehicles"?<Vehicles organization={activeOrg.id} vehicles={vehicles} customers={customers} refresh={refreshData} canEdit={["owner","manager","adviser"].includes(activeOrg.role)}/>:
         <ComingSoon name={selected?.title??"Раздел"}/>}
      </main>
    </div>
  </div>;
}
