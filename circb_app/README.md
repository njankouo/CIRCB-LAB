# CIRCB-LAB 🏥🔬

Plateforme intégrée de gestion hospitalière et de laboratoire pour le **Centre International de Référence Chantal Biya (CIRCB)**. Ce système permet d'administrer efficacement les dossiers médicaux, les flux de laboratoire, ainsi que les accès et les rôles des utilisateurs selon les normes institutionnelles.

---

## 🚀 Fonctionnalités principales

* **Gestion Avancée des Rôles & Permissions :** Interface dédiée pour configurer les groupes d'utilisateurs (Administrateurs, Médecins, Biologistes, etc.) et leur assigner des permissions granulaires.
* **Sécurité Intégrée :** 
  * Protection contre la suppression accidentelle des rôles encore liés à des utilisateurs actifs.
  * Décorateurs de sécurité et contrôle d'accès basé sur les rôles (RBAC).
* **Interface Utilisateur Moderne (Style DHIS2) :** Design épuré, professionnel et orienté santé publique propulsé par **Tailwind CSS** et **Alpine.js**.
* **Gestion du Laboratoire :** Suivi des analyses, des permissions spécifiques aux modules cliniques (`circb_app`) et traçabilité des actions.

---

## 🛠️ Stack Technique

* **Backend :** Python, Django
* **Frontend :** HTML5, Tailwind CSS, Alpine.js
* **Base de données :** SQLite (par défaut en développement) / PostgreSQL (recommandé en production)
* **Contrôle de version :** Git / GitHub

---

## ⚙️ Installation et Configuration

Suivez ces étapes pour installer et exécuter le projet en local :

### 1. Cloner le dépôt
```bash
git clone [https://github.com/njankouo/CIRCB-LAB.git](https://github.com/njankouo/CIRCB-LAB.git)
cd CIRCB-LAB