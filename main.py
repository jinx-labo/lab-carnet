import os
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "/data/app.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ContactModel(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(200), nullable=False)
    telephone = Column(String(50), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="carnet", description="API Carnet de Contacts", version="1.0.0")

class ContactCreate(BaseModel):
    nom: str
    telephone: str
    note: Optional[str] = None

class ContactUpdate(BaseModel):
    nom: Optional[str] = None
    telephone: Optional[str] = None
    note: Optional[str] = None

class ContactOut(BaseModel):
    id: int
    nom: str
    telephone: str
    note: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/contacts", response_model=List[ContactOut])
def list_contacts(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(ContactModel)
    if q:
        like = f"%{q}%"
        query = query.filter(
            ContactModel.nom.ilike(like) | ContactModel.telephone.ilike(like)
        )
    return query.order_by(ContactModel.nom).all()

@app.post("/contacts", response_model=ContactOut, status_code=201)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    if not contact.nom.strip():
        raise HTTPException(status_code=400, detail="Le nom ne peut pas être vide.")
    if not contact.telephone.strip():
        raise HTTPException(status_code=400, detail="Le téléphone ne peut pas être vide.")
    db_contact = ContactModel(
        nom=contact.nom.strip(),
        telephone=contact.telephone.strip(),
        note=contact.note.strip() if contact.note else None,
    )
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

@app.get("/contacts/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(ContactModel).filter(ContactModel.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact introuvable.")
    return contact

@app.put("/contacts/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: int, data: ContactUpdate, db: Session = Depends(get_db)):
    contact = db.query(ContactModel).filter(ContactModel.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact introuvable.")
    if data.nom is not None:
        if not data.nom.strip():
            raise HTTPException(status_code=400, detail="Le nom ne peut pas être vide.")
        contact.nom = data.nom.strip()
    if data.telephone is not None:
        if not data.telephone.strip():
            raise HTTPException(status_code=400, detail="Le téléphone ne peut pas être vide.")
        contact.telephone = data.telephone.strip()
    if data.note is not None:
        contact.note = data.note.strip() if data.note.strip() else None
    db.commit()
    db.refresh(contact)
    return contact

@app.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(ContactModel).filter(ContactModel.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact introuvable.")
    db.delete(contact)
    db.commit()
    return

@app.get("/", response_class=HTMLResponse)
def index():
    html = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Carnet de contacts</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #f0f4f8; color: #2d3748; min-height: 100vh; }
  header { background: #4a90d9; color: #fff; padding: 1rem 1.5rem; display: flex; align-items: center; gap: .75rem; box-shadow: 0 2px 6px rgba(0,0,0,.15); }
  header svg { flex-shrink: 0; }
  header h1 { font-size: 1.4rem; font-weight: 700; letter-spacing: .5px; }
  .container { max-width: 680px; margin: 0 auto; padding: 1.25rem 1rem 3rem; }
  .card { background: #fff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.08); padding: 1.25rem; margin-bottom: 1.25rem; }
  .card h2 { font-size: 1rem; font-weight: 600; margin-bottom: .85rem; color: #4a90d9; }
  .form-group { margin-bottom: .75rem; }
  label { display: block; font-size: .82rem; font-weight: 600; margin-bottom: .3rem; color: #4a5568; }
  input, textarea { width: 100%; padding: .55rem .75rem; border: 1.5px solid #cbd5e0; border-radius: 8px; font-size: .95rem; transition: border-color .2s; background: #f7fafc; }
  input:focus, textarea:focus { outline: none; border-color: #4a90d9; background: #fff; }
  textarea { resize: vertical; min-height: 70px; }
  .btn { display: inline-flex; align-items: center; gap: .4rem; padding: .55rem 1.2rem; border: none; border-radius: 8px; font-size: .92rem; font-weight: 600; cursor: pointer; transition: background .2s, transform .1s; }
  .btn:active { transform: scale(.97); }
  .btn-primary { background: #4a90d9; color: #fff; }
  .btn-primary:hover { background: #357abd; }
  .btn-danger { background: #e53e3e; color: #fff; font-size: .8rem; padding: .35rem .75rem; }
  .btn-danger:hover { background: #c53030; }
  .btn-edit { background: #ed8936; color: #fff; font-size: .8rem; padding: .35rem .75rem; }
  .btn-edit:hover { background: #c05621; }
  .search-bar { display: flex; gap: .6rem; margin-bottom: 1rem; }
  .search-bar input { flex: 1; }
  #contact-list { display: flex; flex-direction: column; gap: .7rem; }
  .contact-item { background: #fff; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.07); padding: 1rem; display: flex; align-items: flex-start; gap: .75rem; }
  .avatar { width: 44px; height: 44px; border-radius: 50%; background: #4a90d9; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; font-weight: 700; flex-shrink: 0; }
  .contact-info { flex: 1; min-width: 0; }
  .contact-info strong { display: block; font-size: 1rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .contact-info .phone { color: #4a90d9; font-size: .88rem; margin: .15rem 0; }
  .contact-info .note { color: #718096; font-size: .82rem; margin-top: .25rem; white-space: pre-wrap; word-break: break-word; }
  .contact-actions { display: flex; gap: .4rem; flex-shrink: 0; flex-direction: column; align-items: flex-end; }
  .empty { text-align: center; color: #a0aec0; padding: 2rem 0; font-size: .95rem; }
  .toast { position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%); background: #2d3748; color: #fff; padding: .65rem 1.4rem; border-radius: 10px; font-size: .9rem; opacity: 0; transition: opacity .3s; pointer-events: none; z-index: 999; }
  .toast.show { opacity: 1; }
  .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 100; align-items: center; justify-content: center; }
  .modal-overlay.active { display: flex; }
  .modal { background: #fff; border-radius: 14px; padding: 1.5rem; width: 90%; max-width: 420px; box-shadow: 0 8px 30px rgba(0,0,0,.2); }
  .modal h2 { font-size: 1.1rem; font-weight: 700; color: #4a90d9; margin-bottom: 1rem; }
  .modal-actions { display: flex; gap: .6rem; justify-content: flex-end; margin-top: 1rem; }
  .btn-secondary { background: #e2e8f0; color: #4a5568; }
  .btn-secondary:hover { background: #cbd5e0; }
</style>
</head>
<body>
<header>
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
  <h1>Carnet de contacts</h1>
</header>

<div class="container">
  <div class="card">
    <h2>Ajouter un contact</h2>
    <div class="form-group">
      <label for="nom">Nom *</label>
      <input type="text" id="nom" placeholder="Jean Dupont" autocomplete="off"/>
    </div>
    <div class="form-group">
      <label for="telephone">Téléphone *</label>
      <input type="tel" id="telephone" placeholder="06 12 34 56 78" autocomplete="off"/>
    </div>
    <div class="form-group">
      <label for="note">Note</label>
      <textarea id="note" placeholder="Optionnel…"></textarea>
    </div>
    <button class="btn btn-primary" onclick="addContact()">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      Ajouter
    </button>
  </div>

  <div class="card">
    <h2>Mes contacts</h2>
    <div class="search-bar">
      <input type="text" id="search" placeholder="Rechercher…" oninput="searchContacts()" autocomplete="off"/>
    </div>
    <div id="contact-list"><div class="empty">Chargement…</div></div>
  </div>
</div>

<!-- Modal édition -->
<div class="modal-overlay" id="edit-modal">
  <div class="modal">
    <h2>Modifier le contact</h2>
    <input type="hidden" id="edit-id"/>
    <div class="form-group">
      <label for="edit-nom">Nom *</label>
      <input type="text" id="edit-nom" autocomplete="off"/>
    </div>
    <div class="form-group">
      <label for="edit-telephone">Téléphone *</label>
      <input type="tel" id="edit-telephone" autocomplete="off"/>
    </div>
    <div class="form-group">
      <label for="edit-note">Note</label>
      <textarea id="edit-note"></textarea>
    </div>
    <div class="modal-actions">
      <button class="btn btn-secondary" onclick="closeModal()">Annuler</button>
      <button class="btn btn-primary" onclick="saveEdit()">Enregistrer</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let currentSearch = '';

function showToast(msg, duration=2800) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), duration);
}

function avatarLetter(nom) {
  return nom ? nom.trim()[0].toUpperCase() : '?';
}

async function loadContacts(q='') {
  const url = q ? `/contacts?q=${encodeURIComponent(q)}` : '/contacts';
  const res = await fetch(url);
  const contacts = await res.json();
  const list = document.getElementById('contact-list');
  if (contacts.length === 0) {
    list.innerHTML = '<div class="empty">Aucun contact trouvé.</div>';
    return;
  }
  list.innerHTML = contacts.map(c => `
    <div class="contact-item" id="ci-${c.id}">
      <div class="avatar">${avatarLetter(c.nom)}</div>
      <div class="contact-info">
        <strong title="${esc(c.nom)}">${esc(c.nom)}</strong>
        <div class="phone">📞 ${esc(c.telephone)}</div>
        ${c.note ? `<div class="note">${esc(c.note)}</div>` : ''}
      </div>
      <div class="contact-actions">
        <button class="btn btn-edit" onclick="openEdit(${c.id},'${esc2(c.nom)}','${esc2(c.telephone)}',\`${esc2(c.note||'')}\`)">✏️ Éditer</button>
        <button class="btn btn-danger" onclick="deleteContact(${c.id})">🗑️ Suppr.</button>
      </div>
    </div>
  `).join('');
}

function esc(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function esc2(str) {
  return String(str).replace(/\\/g,'\\\\').replace(/'/g,"\\'").replace(/`/g,'\\`').replace(/\r?\n/g,'\\n');
}

async function addContact() {
  const nom = document.getElementById('nom').value.trim();
  const telephone = document.getElementById('telephone').value.trim();
  const note = document.getElementById('note').value.trim();
  if (!nom || !telephone) { showToast('⚠️ Nom et téléphone sont obligatoires.'); return; }
  const res = await fetch('/contacts', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({nom, telephone, note: note || null})
  });
  if (res.ok) {
    document.getElementById('nom').value = '';
    document.getElementById('telephone').value = '';
    document.getElementById('note').value = '';
    showToast('✅ Contact ajouté !');
    loadContacts(currentSearch);
  } else {
    const err = await res.json();
    showToast('❌ ' + (err.detail || 'Erreur'));
  }
}

async function deleteContact(id) {
  if (!confirm('Supprimer ce contact ?')) return;
  const res = await fetch(`/contacts/${id}`, {method:'DELETE'});
  if (res.status === 204) {
    showToast('🗑️ Contact supprimé.');
    loadContacts(currentSearch);
  } else {
    showToast('❌ Erreur lors de la suppression.');
  }
}

function openEdit(id, nom, telephone, note) {
  document.getElementById('edit-id').value = id;
  document.getElementById('edit-nom').value = nom;
  document.getElementById('edit-telephone').value = telephone;
  document.getElementById('edit-note').value = note;
  document.getElementById('edit-modal').classList.add('active');
}

function closeModal() {
  document.getElementById('edit-modal').classList.remove('active');
}

async function saveEdit() {
  const id = document.getElementById('edit-id').value;
  const nom = document.getElementById('edit-nom').value.trim();
  const telephone = document.getElementById('edit-telephone').value.trim();
  const note = document.getElementById('edit-note').value.trim();
  if (!nom || !telephone) { showToast('⚠️ Nom et téléphone sont obligatoires.'); return; }
  const res = await fetch(`/contacts/${id}`, {
    method: 'PUT',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({nom, telephone, note: note || null})
  });
  if (res.ok) {
    closeModal();
    showToast('✅ Contact mis à jour !');
    loadContacts(currentSearch);
  } else {
    const err = await res.json();
    showToast('❌ ' + (err.detail || 'Erreur'));
  }
}

let searchTimeout;
function searchContacts() {
  currentSearch = document.getElementById('search').value.trim();
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => loadContacts(currentSearch), 300);
}

document.getElementById('edit-modal').addEventListener('click', function(e) {
  if (e.target === this) closeModal();
});

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeModal();
});

loadContacts();
</script>
</body>
</html>"""
    return HTMLResponse(content=html)