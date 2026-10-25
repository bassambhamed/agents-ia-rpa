"""
api_rpa.py : service web du workflow RPA 2.0 de Fictiva (atelier 5.A).

Le workflow (n8n, Power Automate ou l'orchestrateur Python) appelle ces routes :

    POST /dossiers                     analyser un email : tri, identification, proposition, routage
    POST /dossiers/{id}/attente        enregistrer l'URL de reprise du workflow (validation humaine)
    POST /validations/{id}             décision humaine ; relance le workflow en attente
    POST /dossiers/{id}/cloturer       ticket CRM, réponse envoyée, statut final
    GET  /indicateurs                  KPI du workflow

Pages pour les humains : /console (validations en attente) et /tableau-de-bord (KPI).

Lancement, depuis le dossier ateliers :
    uvicorn api_rpa:app --port 8005
"""

from __future__ import annotations

import html
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

import rpa_fictiva as rf

etat: dict = {}


@asynccontextmanager
async def cycle_de_vie(app: FastAPI):
    # Index, reranker et agent construits une fois ; les dossiers sont enregistrés dans resultats/.
    etat["service"] = rf.ServiceRPA(fichier=Path(os.getenv("FICHIER_DOSSIERS", "resultats/dossiers.json")))
    yield


app = FastAPI(title="Workflow RPA 2.0 de Fictiva",
              description="Services du workflow de traitement des emails clients : analyse, validation humaine, "
                          "clôture et indicateurs. Données synthétiques.",
              version="1.0", lifespan=cycle_de_vie)


def service() -> rf.ServiceRPA:
    return etat["service"]


def dossier_ou_404(identifiant: str) -> rf.Dossier:
    dossier = service().dossiers.get(identifiant)
    if dossier is None:
        raise HTTPException(404, f"Dossier {identifiant} introuvable")
    return dossier


class Attente(BaseModel):
    resume_url: str | None = Field(default=None, description="URL de reprise du workflow (n8n : $execution.resumeUrl)")


class Validation(BaseModel):
    decision: Literal["approuver", "modifier", "rejeter"]
    validateur: str = Field(min_length=2, examples=["Claire Dubois, responsable du service client"])
    commentaire: str = ""
    montant_chf: float | None = Field(default=None, description="Montant corrigé, si la décision est « modifier »")


@app.get("/sante")
def sante() -> dict:
    s = service()
    return {"statut": "ok", "modeles": s.modeles, "seuil_validation_chf": s.seuil_validation,
            "disjoncteur": s.disjoncteur.etat, "dossiers": len(s.dossiers)}


@app.post("/dossiers")
def analyser(email: rf.Email) -> dict:
    dossier, doublon = service().analyser(email.model_dump())
    return {"doublon": doublon, **rf.asdict(dossier)}


@app.get("/dossiers")
def lister() -> list[dict]:
    return [d.resume() for d in service().dossiers.values()]


@app.get("/dossiers/{identifiant}")
def lire(identifiant: str) -> dict:
    return rf.asdict(dossier_ou_404(identifiant))


@app.post("/dossiers/{identifiant}/attente")
def mettre_en_attente(identifiant: str, attente: Attente) -> dict:
    return rf.asdict(service().mettre_en_attente(dossier_ou_404(identifiant), attente.resume_url))


@app.get("/validations")
def validations_en_attente() -> list[dict]:
    return [d.resume() | {"proposition": d.proposition, "email": d.email}
            for d in service().dossiers.values() if d.statut in ("a_valider", "en_attente")]


@app.post("/validations/{identifiant}")
def valider(identifiant: str, validation: Validation) -> dict:
    try:
        dossier = service().valider(dossier_ou_404(identifiant), **validation.model_dump())
    except ValueError as erreur:
        raise HTTPException(409, str(erreur)) from erreur
    reprise = None
    if dossier.resume_url:  # le workflow attend cette décision pour reprendre
        try:
            reprise = httpx.post(dossier.resume_url, json={"dossier": identifiant, **validation.model_dump()}, timeout=30).status_code
        except httpx.HTTPError as erreur:
            service().alerter(dossier, f"reprise du workflow impossible : {type(erreur).__name__}")
    return {"dossier": identifiant, "validation": dossier.validation, "reprise_workflow": reprise}


@app.post("/dossiers/{identifiant}/cloturer")
def cloturer(identifiant: str) -> dict:
    try:
        return rf.asdict(service().cloturer(dossier_ou_404(identifiant)))
    except ValueError as erreur:
        raise HTTPException(409, str(erreur)) from erreur


@app.get("/indicateurs")
def indicateurs() -> dict:
    return service().indicateurs()


@app.get("/envois")
def envois() -> list[dict]:
    return service().envois


@app.get("/alertes")
def alertes() -> list[dict]:
    return service().alertes


# --- Pages pour les humains ----------------------------------------------------

STYLE = """<style>
body{font-family:system-ui,sans-serif;margin:0;background:#f2f5f9;color:#1c2733}
header{background:#123a63;color:#fff;padding:14px 24px;border-bottom:4px solid #e2542c}
main{max-width:1100px;margin:0 auto;padding:20px}
.carte{background:#fff;border:1px solid #d7dee6;border-left:4px solid #123a63;border-radius:8px;padding:14px 16px;margin-bottom:14px}
.regle{color:#c0392b;font-size:.9em} pre{white-space:pre-wrap;background:#f7f8fa;padding:8px;border-radius:6px;font-size:.88em}
button{border:0;border-radius:6px;padding:6px 12px;margin-right:6px;color:#fff;cursor:pointer}
.ok{background:#1b998b}.non{background:#c0392b} table{border-collapse:collapse;width:100%}
td,th{border-bottom:1px solid #d7dee6;padding:6px 8px;text-align:left}.kpi{font-size:1.6em;color:#123a63;font-weight:600}
.grille{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px}
</style>"""


@app.get("/console", response_class=HTMLResponse)
def console() -> str:
    cartes = []
    for d in service().dossiers.values():
        if d.statut not in ("a_valider", "en_attente"):
            continue
        p = d.proposition or {}
        regles = "".join(f"<li class='regle'>{html.escape(r)}</li>" for r in d.routage["regles"])
        montant = f"{p['montant_chf']:.2f} CHF" if p.get("montant_chf") is not None else "-"
        cartes.append(f"""<div class='carte'><b>{d.id}</b> · {html.escape(d.email['objet'])} · {html.escape(d.email['expediteur'])}
        <ul>{regles}</ul><p>Proposition : <b>{html.escape(str(p.get('action')))}</b> · montant : {montant}
        · {html.escape(str(p.get('motif', '')))}</p><pre>{html.escape(p.get('brouillon', '') or '')}</pre>
        <button class='ok' onclick="decider('{d.id}','approuver')">Approuver</button>
        <button class='non' onclick="decider('{d.id}','rejeter')">Rejeter (traitement manuel)</button></div>""")
    contenu = "".join(cartes) or "<p>Aucun dossier en attente de validation.</p>"
    return f"""<!doctype html><html lang='fr'><head><meta charset='utf-8'><title>Console de validation</title>{STYLE}</head>
    <body><header><h2>Console de validation · Fictiva SA</h2></header><main>{contenu}</main>
    <script>async function decider(id, decision) {{
      const validateur = prompt('Votre nom :'); if (!validateur) return;
      const r = await fetch('/validations/' + id, {{method: 'POST', headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{decision, validateur}})}});
      alert(r.ok ? 'Décision enregistrée' : 'Erreur ' + r.status); location.reload(); }}</script></body></html>"""


@app.get("/tableau-de-bord", response_class=HTMLResponse)
def tableau_de_bord() -> str:
    k = service().indicateurs()

    def pct(x):
        return "-" if x is None else f"{x:.0%}"

    tuiles = [("Dossiers", k["dossiers"]), ("Clôturés", k["clotures"]), ("En attente de validation", k["en_attente_de_validation"]),
              ("Automatisation de bout en bout", pct(k["taux_automatisation_bout_en_bout"])),
              ("Escalade humaine", pct(k["taux_escalade_humaine"])),
              ("Approbation sans modification", pct(k["taux_approbation_sans_modification"])),
              ("Analyse moyenne", f"{k['duree_moyenne_analyse_s']} s"), ("Appels au LLM par dossier", k["appels_llm_par_dossier"]),
              ("Montant remboursé", f"{k['montant_rembourse_chf']:.0f} CHF"), ("Alertes", k["alertes"])]
    grille = "".join(f"<div class='carte'><div>{t}</div><div class='kpi'>{v}</div></div>" for t, v in tuiles)
    lignes = "".join(f"<tr><td>{d.id}</td><td>{html.escape(d.email['objet'])}</td><td>{(d.tri or {}).get('categorie', '-')}</td>"
                     f"<td>{(d.proposition or {}).get('action', '-')}</td><td>{d.statut}</td></tr>"
                     for d in service().dossiers.values())
    return f"""<!doctype html><html lang='fr'><head><meta charset='utf-8'><title>Tableau de bord</title>{STYLE}
    <meta http-equiv='refresh' content='10'></head><body><header><h2>Tableau de bord du workflow · Fictiva SA</h2></header>
    <main><div class='grille'>{grille}</div><div class='carte'><table><tr><th>Dossier</th><th>Objet</th><th>Catégorie</th>
    <th>Action</th><th>Statut</th></tr>{lignes}</table></div></main></body></html>"""
