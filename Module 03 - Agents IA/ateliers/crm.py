"""
crm.py : CRM simulé de Fictiva SA (clients, commandes, tickets) et calcul des remboursements.

Les données sont dans donnees/crm.json ; la date du scénario est fixée
(`date_reference`) pour que les calculs de délais restent reproductibles.
Ces fonctions sont exposées à l'agent comme outils : en lecture via le
serveur MCP (serveur_crm_mcp.py), en calcul et en écriture via LangChain.
"""

from __future__ import annotations

import json
from datetime import date
from itertools import count
from pathlib import Path

FICHIER = Path(__file__).resolve().parent / "donnees" / "crm.json"
DONNEES = json.loads(FICHIER.read_text(encoding="utf-8"))
DATE_REFERENCE = date.fromisoformat(DONNEES["date_reference"])

TICKETS: list[dict] = []
_numeros = count(1)


def rechercher_client(numero_client: str = "", nom: str = "") -> dict:
    """Fiche client par numéro (CL-xxxxx) ou par nom d'entreprise (recherche partielle)."""
    if numero_client:
        fiche = DONNEES["clients"].get(numero_client.strip().upper())
        if fiche is None:
            return {"erreur": f"Client {numero_client} introuvable. Format attendu : CL-xxxxx."}
        return {"numero_client": numero_client.strip().upper(), **fiche}
    if nom:
        trouves = [{"numero_client": num, **fiche} for num, fiche in DONNEES["clients"].items()
                   if nom.lower() in fiche["nom"].lower()]
        return {"clients": trouves} if trouves else {"erreur": f"Aucun client dont le nom contient « {nom} »."}
    return {"erreur": "Indiquez un numéro de client ou un nom d'entreprise."}


def commandes_du_client(numero_client: str) -> dict:
    """Liste résumée des commandes d'un client."""
    numero_client = numero_client.strip().upper()
    if numero_client not in DONNEES["clients"]:
        return {"erreur": f"Client {numero_client} introuvable. Format attendu : CL-xxxxx."}
    commandes = [
        {"numero_commande": num, "date_commande": c["date_commande"], "statut": c["statut"],
         "references": [ligne["reference"] for ligne in c["lignes"]]}
        for num, c in DONNEES["commandes"].items() if c["client"] == numero_client
    ]
    return {"numero_client": numero_client, "commandes": commandes}


def consulter_commande(numero_commande: str) -> dict:
    """Détail d'une commande : client, statut, livraison, lignes, montants."""
    numero_commande = numero_commande.strip().upper()
    commande = DONNEES["commandes"].get(numero_commande)
    if commande is None:
        return {"erreur": f"Commande {numero_commande} introuvable. Format attendu : CMD-AAAA-NNNN."}
    client = DONNEES["clients"][commande["client"]]
    lignes = [
        {**ligne, **{cle: DONNEES["produits"][ligne["reference"]][cle] for cle in ("designation", "categorie")}}
        for ligne in commande["lignes"]
    ]
    brut = sum(ligne["quantite"] * ligne["prix_unitaire"] for ligne in commande["lignes"])
    total_ht = round(brut * (1 - commande["remise_pct"] / 100), 2)
    detail = {
        "numero_commande": numero_commande,
        "client": {"numero_client": commande["client"], "nom": client["nom"], "statut": client["statut"]},
        "statut": commande["statut"],
        "date_commande": commande["date_commande"],
        "date_livraison": commande["date_livraison"],
        "lignes": lignes,
        "remise_pct": commande["remise_pct"],
        "frais_livraison": commande["frais_livraison"],
        "total_ht": total_ht,
        "facture": commande["facture"],
    }
    if commande["date_livraison"]:
        detail["jours_depuis_livraison"] = (DATE_REFERENCE - date.fromisoformat(commande["date_livraison"])).days
    if "acompte_verse" in commande:
        detail["acompte_verse"] = commande["acompte_verse"]
    return detail


def calculer_remboursement(numero_commande: str, references: list[str], defectueux: bool,
                           consommables_ouverts: bool = False) -> dict:
    """Applique la politique de retours de Fictiva aux articles retournés d'une commande.

    Art. 1 : 30 jours (60 pour un client Premium). Art. 2 : défaut sous garantie de
    24 mois, remboursement intégral avec les frais de livraison. Art. 3 : sans défaut,
    frais de traitement de 10 % plafonnés à 50 CHF ; articles personnalisés exclus.
    Art. 4 : consommables ouverts exclus. Art. 5 : validation au-delà de 5 000 CHF.
    """
    commande = consulter_commande(numero_commande)
    if "erreur" in commande:
        return commande
    if commande["statut"] != "livree":
        return {"remboursable": False, "montant_chf": 0.0, "validation_requise": False,
                "motif": f"Commande non livrée (statut : {commande['statut']}) : ce n'est pas un retour. "
                         "Traiter comme une réclamation ou une annulation."}

    references = [r.strip().upper() for r in references]
    lignes = [ligne for ligne in commande["lignes"] if ligne["reference"] in references]
    inconnues = sorted(set(references) - {ligne["reference"] for ligne in lignes})
    if inconnues:
        return {"erreur": f"Références absentes de la commande {numero_commande} : {', '.join(inconnues)}."}

    coefficient = 1 - commande["remise_pct"] / 100
    jours = commande["jours_depuis_livraison"]
    premium = commande["client"]["statut"] == "premium"
    montant_articles = sum(ligne["quantite"] * ligne["prix_unitaire"] * coefficient for ligne in lignes)

    if defectueux:
        if jours > 730:
            return {"remboursable": False, "montant_chf": 0.0, "validation_requise": False,
                    "motif": f"Garantie de 24 mois expirée ({jours} jours depuis la livraison).", "articles_politique": ["2.3"]}
        montant, motif, regles = montant_articles + commande["frais_livraison"], "Défaut sous garantie : prix et frais de livraison initiaux remboursés.", ["2.2"]
    else:
        delai = 60 if premium else 30
        if jours > delai:
            return {"remboursable": False, "montant_chf": 0.0, "validation_requise": False,
                    "motif": f"Délai de retour de {delai} jours dépassé ({jours} jours) et article sans défaut.",
                    "articles_politique": ["1"]}
        exclues = [ligne["reference"] for ligne in lignes
                   if ligne["categorie"] == "personnalise" or (ligne["categorie"] == "consommable" and consommables_ouverts)]
        if exclues:
            return {"remboursable": False, "montant_chf": 0.0, "validation_requise": False,
                    "motif": f"Articles non repris sans défaut (personnalisés ou consommables ouverts) : {', '.join(exclues)}.",
                    "articles_politique": ["3.4", "4"]}
        frais = min(0.10 * montant_articles, 50.0)
        montant = montant_articles - frais
        motif = f"Retour sans défaut dans le délai de {delai} jours : frais de traitement de {frais:.2f} CHF déduits."
        regles = ["1.2" if premium else "1.1", "3"]

    montant = round(montant, 2)
    return {"remboursable": montant > 0, "montant_chf": montant, "validation_requise": montant > 5000,
            "motif": motif, "articles_politique": regles + (["5"] if montant > 5000 else [])}


def creer_ticket(numero_client: str, categorie: str, resume: str, montant_chf: float | None = None) -> dict:
    """Enregistre un ticket de traitement dans le CRM (action en écriture)."""
    numero_client = numero_client.strip().upper()
    if numero_client not in DONNEES["clients"]:
        return {"erreur": f"Client {numero_client} introuvable : ticket non créé."}
    ticket = {"numero_ticket": f"TCK-{next(_numeros):04d}", "numero_client": numero_client,
              "categorie": categorie, "resume": resume, "montant_chf": montant_chf, "statut": "ouvert"}
    TICKETS.append(ticket)
    return ticket
