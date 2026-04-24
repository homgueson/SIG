# SIG & Carto — Système d'Information Géographique

Application web de cartographie interactive basée sur **Leaflet.js**, permettant la visualisation et l'analyse de données géospatiales françaises.

## Fonctionnalités

- 🗺️ **Fonds de carte** interchangeables : OpenStreetMap, Satellite (Esri), Topographique
- 📍 **Couches de données GeoJSON** :
  - Villes principales françaises (population, région, superficie)
  - Axes routiers (autoroutes) avec informations de trafic
  - Régions administratives (population, chef-lieu)
  - Zones protégées (parcs nationaux, réserves naturelles)
- 📏 **Outils de mesure** : distance et surface
- 🔍 **Recherche** par nom de ville, région ou zone protégée
- 🖱️ **Coordonnées** affichées en temps réel au survol
- 💾 **Export GeoJSON** des éléments dessinés
- 🖨️ **Impression** de la carte

## Structure du projet

```
SIG/
├── index.html              # Page principale de l'application
├── css/
│   └── style.css           # Styles de l'interface
├── js/
│   └── app.js              # Logique applicative (Leaflet)
├── data/
│   ├── villes.geojson      # Points : villes principales de France
│   ├── routes.geojson      # Lignes : axes routiers (autoroutes)
│   ├── regions.geojson     # Polygones : régions administratives
│   └── zones_protegees.geojson  # Polygones : zones protégées
└── README.md
```

## Technologies

| Technologie | Version | Usage |
|-------------|---------|-------|
| [Leaflet.js](https://leafletjs.com/) | 1.9.4 | Moteur de carte interactif |
| GeoJSON | RFC 7946 | Format de données géospatiales |
| HTML5 / CSS3 / JS (ES6+) | — | Interface utilisateur |

## Utilisation

### Démarrage

Ouvrir `index.html` dans un navigateur web moderne. Pour éviter les restrictions CORS lors du chargement des fichiers GeoJSON locaux, utiliser un serveur local :

```bash
# Avec Python 3
python -m http.server 8080

# Avec Node.js (npx)
npx serve .

# Avec PHP
php -S localhost:8080
```

Puis ouvrir [http://localhost:8080](http://localhost:8080).

### Navigation

| Action | Description |
|--------|-------------|
| Molette / + − | Zoomer/dézoomer |
| Clic + glisser | Déplacer la carte |
| Clic sur un élément | Afficher la fiche d'information |
| Survol | Voir les infos dans la barre du bas |

### Couches

Activer ou désactiver les couches depuis le panneau latéral gauche. Changer le fond de carte avec les boutons radio.

### Mesures

1. Cliquer sur **📏 Distance** ou **📐 Surface**
2. Cliquer sur la carte pour définir les points
3. Double-clic pour terminer le tracé
4. Le résultat s'affiche dans le panneau

### Recherche

Saisir un nom de ville, région ou zone protégée dans le champ de recherche et appuyer sur **Entrée** ou le bouton loupe. Cliquer sur un résultat pour y naviguer.

## Données

Les données GeoJSON incluses sont des données de démonstration représentant :

- **12 villes** françaises avec leur population, région et code postal
- **6 axes autoroutiers** avec longueur et gestionnaire
- **8 régions** administratives avec chef-lieu et population
- **5 zones protégées** (parcs nationaux, réserves naturelles, zones humides)

## Projection

L'application utilise la projection **WGS 84 (EPSG:4326)** pour les données GeoJSON, affichées sur une carte Web Mercator (EPSG:3857) via Leaflet.

## Licence

Projet SIG et carto — Usage pédagogique et professionnel.
