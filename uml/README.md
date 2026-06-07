# 📐 Modélisations et Diagrammes UML — Agent IA Yaburu

Ce dossier contient l'ensemble des diagrammes UML décrivant le fonctionnement technique de l'Agent IA Yaburu (WhatsApp). 

Chaque cas d'utilisation est modélisé sous plusieurs formes :
1. **Diagramme d'Activité Standard (Avec Acteurs)** : Partitionné en lignes d'eau (swimlanes) décrivant les actions de chaque acteur.
2. **Diagramme d'Activité Simplifié (Sans Acteur / NoActor)** : Concentré uniquement sur le flux de traitement logique de l'application.
3. **Diagramme de Séquence (Sequence)** : Représentation chronologique fine des appels de fonctions, requêtes HTTP et opérations en base de données.

---

## 🎭 Entités de Lignes de Vie (Diagrammes de Séquence)

Pour correspondre exactement à l'architecture de votre projet, les diagrammes de séquences s'articulent autour de ces 4 lifelines clés :
- 🟢 **Marchand** : L'utilisateur final sur WhatsApp.
- 🔵 **API WhatsApp Cloud** : La passerelle de communication (WASenderAPI) gérant les webhooks.
- 🟡 **Système** : Notre application FastAPI (regroupant le code et son stockage base de données local).
- 🟠 **API Yaburu** : Le backend Laravel externe.

---

## 🗂️ Table des Fichiers UML par Cas d'Utilisation

| Cas d'Utilisation | Diagramme d'Activité Standard | Diagramme d'Activité (Sans Acteur) | Diagramme de Séquence |
|---|---|---|---|
| **UC0 — Authentification / Onboarding** | `UC0_Authentification.png` | `UC0_Authentification_NoActor.puml`<br>`UC0_Authentification_NoActor.png` | `UC0_Authentification_Sequence.puml`<br>`UC0_Authentification_Sequence.png` |
| **UC1 — Statistiques** | `UC1_Statistiques.puml`<br>`UC1_Statistiques.png` | `UC1_Statistiques_NoActor.puml`<br>`UC1_Statistiques_NoActor.png` | `UC1_Statistiques_Sequence.puml`<br>`UC1_Statistiques_Sequence.png` |
| **UC2 — Liste Produits** | `UC2_Liste_Produits.puml`<br>`UC2_Liste_Produits.png` | `UC2_Liste_Produits_NoActor.puml`<br>`UC2_Liste_Produits_NoActor.png` | `UC2_Liste_Produits_Sequence.puml`<br>`UC2_Liste_Produits_Sequence.png` |
| **UC3 — Ajouter Produit** | `UC3_Ajouter_Produit.puml`<br>`UC3_Ajouter_Produit.png` | `UC3_Ajouter_Produit_NoActor.puml`<br>`UC3_Ajouter_Produit_NoActor.png` | `UC3_Ajouter_Produit_Sequence.puml`<br>`UC3_Ajouter_Produit_Sequence.png` |
| **UC4 — Commandes** | `UC4_Commandes_Produit.puml`<br>`UC4_Commandes_Produit.png` | `UC4_Commandes_Produit_NoActor.puml`<br>`UC4_Commandes_Produit_NoActor.png` | `UC4_Commandes_Produit_Sequence.puml`<br>`UC4_Commandes_Produit_Sequence.png` |
| **UC5 — Changer Boutique** | `UC5_Changer_Boutique.puml`<br>`UC5_Changer_Boutique.png` | `UC5_Changer_Boutique_NoActor.puml`<br>`UC5_Changer_Boutique_NoActor.png` | `UC5_Changer_Boutique_Sequence.puml`<br>`UC5_Changer_Boutique_Sequence.png` |
| **UC6 — Mon Profil** | `UC6_Mon_Profil.puml`<br>`UC6_Mon_Profil.png` | `UC6_Mon_Profil_NoActor.puml`<br>`UC6_Mon_Profil_NoActor.png` | *(Non requis)* |

---

## ⚙️ Règles de gestion clés modélisées

- **Fast-Path Session active (UC0) :** Si l'utilisateur possède déjà une session valide en DB locale, le système bypass entièrement les requêtes HTTP externes de contrôle d'utilisateur et de synchronisation des boutiques, éliminant tout délai inutile.
- **Debounce de 1.5s (UC0 - UC5) :** Mécanisme d'anti-rebond systématique pour fusionner les messages rapides d'un même utilisateur en une seule session de traitement.
- **PendingMedia (UC3) :** Flux d'ajout en deux temps. L'envoi d'une photo l'enregistre en base locale, puis l'envoi de la description extrait les attributs, crée le produit sur Yaburu avec la photo et purge la DB locale.
- **Pagination interactive (UC2 & UC4) :** Affichage direct si $\le 5$ éléments, ou affichage des 5 premiers avec bouton/option interactive "Voir plus" si la liste dépasse 5.
