"""
serveur_crm_mcp.py : serveur MCP qui expose le CRM de Fictiva en lecture seule.

Le serveur communique par l'entrée et la sortie standard (transport stdio) :
c'est le client MCP (l'agent, un IDE, un assistant de bureau) qui le lance.
Test manuel : `mcp dev serveur_crm_mcp.py` ouvre l'inspecteur MCP.
"""

from mcp.server.fastmcp import FastMCP

import crm

serveur = FastMCP("crm-fictiva")


@serveur.tool()
def rechercher_client(numero_client: str = "", nom: str = "") -> dict:
    """Retrouve la fiche d'un client de Fictiva : nom de l'entreprise, contact, statut
    (standard ou premium), ville. Chercher par numéro de client (format CL-xxxxx) ou,
    à défaut, par une partie du nom de l'entreprise."""
    return crm.rechercher_client(numero_client, nom)


@serveur.tool()
def commandes_du_client(numero_client: str) -> dict:
    """Liste les commandes d'un client (numéro, date, statut, références commandées).
    Utile quand le client ne cite pas son numéro de commande."""
    return crm.commandes_du_client(numero_client)


@serveur.tool()
def consulter_commande(numero_commande: str) -> dict:
    """Détail d'une commande (format CMD-AAAA-NNNN) : client et statut du client,
    statut de la commande, dates, nombre de jours depuis la livraison, lignes avec
    prix et catégorie des produits, remise, frais de livraison, numéro de facture."""
    return crm.consulter_commande(numero_commande)


if __name__ == "__main__":
    serveur.run()  # transport stdio par défaut
