"""
Module centralisé pour le menu des capacités de l'agent Yaburu.
Utilisé dans agent_dispatcher.py.
"""

CAPABILITIES_MENU = """
---
*Voici tout ce que je peux faire pour toi :*

*1. Statistiques de ta boutique*
   Demande-moi tes stats et je te donne un apercu complet : nombre de produits, total des ventes, nombre de clients, chiffre d'affaires.
   Exemples : "Montre-moi mes stats", "Comment va ma boutique ?", "Mon chiffre d'affaires ?"

*2. Voir tes produits*
   Je peux te lister tous les produits de ta boutique ou te donner les infos detaillees d'un produit en particulier (prix, stock, description, type).
   Exemples : "Liste mes produits", "Montre-moi mes articles", "C'est quoi le prix du T-shirt bleu ?", "Combien il me reste de savon en stock ?"

*3. Ajouter un nouveau produit*
   Envoie-moi la photo du produit avec les infos (nom, prix, stock, type, description) et je le mets en ligne direct. La photo est obligatoire.
   Exemples : "Je veux ajouter un produit", "Nouveau produit" puis envoie la photo

*4. Consulter les commandes*
   Je te montre les commandes passees sur un produit precis : clients, quantites, statuts, montants.
   Exemples : "Les commandes du T-shirt", "Qui a commande le savon ?", "Mes commandes sur le sac"

*5. Tes informations personnelles*
   Je peux te rappeler ton nom et la liste de toutes tes boutiques actives.
   Exemples : "Mes infos", "C'est quoi mon profil ?", "Quelles sont mes boutiques ?"

*6. Support et Aide sur Yaburu*
   Tu peux me poser toutes tes questions sur le fonctionnement de Yaburu, nos services, la livraison, ou comment utiliser la plateforme.
   Exemples : "Comment fonctionne la livraison ?", "Quels sont vos tarifs ?", "Comment récupérer mon mot de passe ?"

---
Pour revoir ce menu a tout moment, dis-moi simplement "menu" ou "aide".
"""

# Mots-clés détectant un flux intermédiaire → le menu ne doit PAS être ajouté
_INTERMEDIATE_KEYWORDS = [
    # Attente d'une photo produit
    "envoyer la photo",
    "envoyez la photo",
    "photo du produit",
    "m'envoyer la photo",
    "veuillez m'envoyer",
    "envoyer une photo",
    "j'ai bien reçu la photo",
    "reçu la photo",
    # Attente des détails produit (après réception de la photo)
    "j'ai besoin de quelques détails",
    "quelques détails supplémentaires",
    "j'ai besoin de",
    "le nom du produit",
    "le prix",
    "la quantité",
    "le stock",
    "type de produit",
]

# Mots-clés indiquant que le marchand demande explicitement le menu
_MENU_REQUEST_KEYWORDS = [
    "menu",
    "aide",
    "help",
    "qu'est-ce que tu peux faire",
    "que peux-tu faire",
    "qu'est ce que tu sais faire",
    "que sais-tu faire",
    "tes capacités",
    "tes fonctionnalités",
    "ce que tu peux faire",
    "ce que tu sais faire",
    "tu peux faire quoi",
    "tu sais faire quoi",
    "montre-moi le menu",
    "les options",
    "tes options",
]


def is_menu_requested(user_text: str) -> bool:
    """
    Retourne True si le message du marchand demande explicitement le menu.
    """
    lower = user_text.strip().lower()
    for kw in _MENU_REQUEST_KEYWORDS:
        if kw in lower:
            return True
    return False


def is_intermediate_response(response_text: str) -> bool:
    """
    Retourne True si la réponse de l'agent est une étape intermédiaire
    (attente photo, choix boutique) où le menu ne doit pas être affiché.
    """
    lower = response_text.lower()
    for kw in _INTERMEDIATE_KEYWORDS:
        if kw in lower:
            return True
    return False
