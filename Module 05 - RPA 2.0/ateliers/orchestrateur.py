"""
orchestrateur.py : le workflow de l'atelier 5.A écrit en Python, équivalent du workflow n8n.

Mêmes étapes et mêmes appels HTTP que workflow_n8n.json :

    email reçu → POST /dossiers → doublon ? fin
                                → automatique ? POST /dossiers/{id}/cloturer
                                → à valider ?   POST /dossiers/{id}/attente, puis, après la
                                                décision humaine, POST /dossiers/{id}/cloturer

Chaque appel est réessayé en cas d'erreur réseau ou de réponse 5xx (comme l'option
« Retry On Fail » des nœuds HTTP de n8n).
"""

from __future__ import annotations

import time

import httpx


class Orchestrateur:
    def __init__(self, url_api: str = "http://127.0.0.1:8005", essais: int = 3, pause_s: float = 2.0):
        self.url, self.essais, self.pause_s = url_api.rstrip("/"), essais, pause_s
        self.journal: list[dict] = []

    def appeler(self, methode: str, chemin: str, **options) -> dict:
        """Appel HTTP avec nouvelles tentatives (attente croissante) sur les erreurs transitoires."""
        for essai in range(1, self.essais + 1):
            try:
                reponse = httpx.request(methode, f"{self.url}{chemin}", timeout=600, **options)
                if reponse.status_code < 500:
                    reponse.raise_for_status()
                    return reponse.json()
                erreur = f"HTTP {reponse.status_code}"
            except httpx.TransportError as e:
                erreur = type(e).__name__
            self.journal.append({"etape": chemin, "essai": essai, "erreur": erreur})
            time.sleep(self.pause_s * essai)
        raise RuntimeError(f"{methode} {chemin} : échec après {self.essais} essais ({erreur})")

    def traiter(self, email: dict) -> dict:
        """Traite un email jusqu'à la clôture, ou jusqu'à la mise en attente de validation."""
        dossier = self.appeler("POST", "/dossiers", json=email)
        if dossier["doublon"]:
            resultat = {"dossier": dossier["id"], "issue": "doublon ignoré"}
        elif dossier["routage"]["statut"] == "automatique":
            clos = self.appeler("POST", f"/dossiers/{dossier['id']}/cloturer")
            resultat = {"dossier": dossier["id"], "issue": f"clôturé automatiquement ({clos['statut']})"}
        else:
            # n8n transmet ici l'URL de reprise de son nœud Wait ; l'orchestrateur reprendra lui-même.
            self.appeler("POST", f"/dossiers/{dossier['id']}/attente", json={"resume_url": None})
            resultat = {"dossier": dossier["id"], "issue": "en attente de validation humaine"}
        self.journal.append({"etape": "email", "message_id": email["message_id"], **resultat})
        return resultat

    def reprendre(self) -> list[dict]:
        """Clôture les dossiers validés par un humain (équivalent de la reprise du nœud Wait)."""
        resultats = []
        for resume in self.appeler("GET", "/dossiers"):
            dossier = self.appeler("GET", f"/dossiers/{resume['id']}")
            if dossier["statut"] == "en_attente" and dossier["validation"]:
                clos = self.appeler("POST", f"/dossiers/{dossier['id']}/cloturer")
                resultats.append({"dossier": dossier["id"], "issue": f"clôturé après validation ({clos['statut']})"})
        return resultats
