/**
 * SIG & Carto - Application principale
 * Système d'Information Géographique interactif basé sur Leaflet.js
 */

'use strict';

/* ============================================================
   Configuration
   ============================================================ */
const CONFIG = {
    center: [46.5, 2.5],
    zoom: 6,
    minZoom: 4,
    maxZoom: 18,
    dataPath: 'data/'
};

/* ============================================================
   Fonds de carte (Tile Layers)
   ============================================================ */
const BASEMAPS = {
    osm: L.tileLayer(
        'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        {
            attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }
    ),
    satellite: L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        {
            attribution: '© <a href="https://www.esri.com/">Esri</a>',
            maxZoom: 18
        }
    ),
    topo: L.tileLayer(
        'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
        {
            attribution: '© <a href="https://opentopomap.org">OpenTopoMap</a> contributors',
            maxZoom: 17
        }
    )
};

/* ============================================================
   Styles des couches
   ============================================================ */
const STYLES = {
    regions: {
        default: {
            color: '#2980b9',
            weight: 2,
            fillColor: '#3498db',
            fillOpacity: 0.15,
            dashArray: '5,5'
        },
        hover: {
            fillOpacity: 0.35,
            weight: 3
        }
    },
    zonesProtegees: {
        default: {
            color: '#27ae60',
            weight: 2,
            fillColor: '#2ecc71',
            fillOpacity: 0.2
        },
        hover: {
            fillOpacity: 0.4,
            weight: 3
        }
    },
    routes: {
        default: {
            color: '#e67e22',
            weight: 3,
            opacity: 0.85
        },
        hover: {
            weight: 5,
            opacity: 1
        }
    }
};

/* ============================================================
   Application
   ============================================================ */
const App = {
    map: null,
    layers: {},
    drawControl: null,
    drawLayer: null,
    measuring: false,
    measureType: null,

    /* ------ Initialisation --------------------------------- */
    init() {
        this.initMap();
        this.loadAllLayers();
        this.bindUIEvents();
        this.updateZoomDisplay();
    },

    /* ------ Carte ------------------------------------------ */
    initMap() {
        this.map = L.map('map', {
            center: CONFIG.center,
            zoom: CONFIG.zoom,
            minZoom: CONFIG.minZoom,
            maxZoom: CONFIG.maxZoom,
            zoomControl: true
        });

        // Fond de carte par défaut
        BASEMAPS.osm.addTo(this.map);

        // Mise à jour des coordonnées au survol
        this.map.on('mousemove', (e) => {
            document.getElementById('cursor-lat').textContent = e.latlng.lat.toFixed(5);
            document.getElementById('cursor-lng').textContent = e.latlng.lng.toFixed(5);
        });

        // Mise à jour du zoom
        this.map.on('zoomend', () => this.updateZoomDisplay());

        // Couche pour le dessin / mesures
        this.drawLayer = new L.FeatureGroup();
        this.map.addLayer(this.drawLayer);
    },

    updateZoomDisplay() {
        document.getElementById('current-zoom').textContent = this.map.getZoom();
    },

    /* ------ Chargement des données GeoJSON ----------------- */
    async loadAllLayers() {
        const tasks = [
            { key: 'villes',          file: 'villes.geojson',         handler: this.createVillesLayer.bind(this) },
            { key: 'routes',          file: 'routes.geojson',         handler: this.createRoutesLayer.bind(this) },
            { key: 'regions',         file: 'regions.geojson',        handler: this.createRegionsLayer.bind(this) },
            { key: 'zonesProtegees',  file: 'zones_protegees.geojson', handler: this.createZonesProtegeesLayer.bind(this) }
        ];

        await Promise.all(tasks.map(async (task) => {
            try {
                const response = await fetch(CONFIG.dataPath + task.file);
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const data = await response.json();
                this.layers[task.key] = task.handler(data);
                this.setStatus(`Couche "${task.file}" chargée`);
            } catch (err) {
                console.warn(`Impossible de charger ${task.file}:`, err);
            }
        }));

        // Afficher les couches cochées par défaut
        this.syncLayerVisibility();
        this.setStatus('Toutes les couches ont été chargées');
    },

    /* ------ Créateurs de couches --------------------------- */
    createVillesLayer(data) {
        return L.geoJSON(data, {
            pointToLayer: (feature, latlng) => {
                const pop = feature.properties.population || 0;
                const radius = pop > 500000 ? 10 : pop > 200000 ? 8 : 6;
                return L.circleMarker(latlng, {
                    radius,
                    fillColor: '#e74c3c',
                    color: 'white',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.9
                });
            },
            onEachFeature: (feature, layer) => {
                const p = feature.properties;
                layer.bindPopup(this.buildPopup(p.nom, [
                    ['Région', p.region],
                    ['Population', (p.population || 0).toLocaleString('fr-FR') + ' hab.'],
                    ['Code postal', p.code_postal],
                    ['Superficie', (p.superficie_km2 || '—') + ' km²']
                ]));
                layer.on('mouseover', () => {
                    layer.setStyle({ fillColor: '#c0392b', radius: 12 });
                    document.getElementById('feature-info').textContent =
                        `${p.nom} — ${(p.population || 0).toLocaleString('fr-FR')} habitants`;
                });
                layer.on('mouseout', () => {
                    const pop = p.population || 0;
                    layer.setStyle({
                        fillColor: '#e74c3c',
                        radius: pop > 500000 ? 10 : pop > 200000 ? 8 : 6
                    });
                    document.getElementById('feature-info').textContent =
                        'Survolez un élément pour afficher ses informations';
                });
            }
        });
    },

    createRoutesLayer(data) {
        return L.geoJSON(data, {
            style: STYLES.routes.default,
            onEachFeature: (feature, layer) => {
                const p = feature.properties;
                layer.bindPopup(this.buildPopup(p.nom, [
                    ['Type', p.type],
                    ['Longueur', (p.longueur_km || '—') + ' km'],
                    ['Vitesse max', (p.vitesse_max || '—') + ' km/h'],
                    ['Gestionnaire', p.gestionnaire || '—']
                ]));
                layer.on('mouseover', () => {
                    layer.setStyle(STYLES.routes.hover);
                    document.getElementById('feature-info').textContent =
                        `${p.nom} — ${p.type} (${p.longueur_km || '?'} km)`;
                });
                layer.on('mouseout', () => {
                    layer.setStyle(STYLES.routes.default);
                    document.getElementById('feature-info').textContent =
                        'Survolez un élément pour afficher ses informations';
                });
            }
        });
    },

    createRegionsLayer(data) {
        return L.geoJSON(data, {
            style: STYLES.regions.default,
            onEachFeature: (feature, layer) => {
                const p = feature.properties;
                layer.bindPopup(this.buildPopup(p.nom, [
                    ['Chef-lieu', p.chef_lieu],
                    ['Population', (p.population || 0).toLocaleString('fr-FR') + ' hab.'],
                    ['Superficie', (p.superficie_km2 || '—').toLocaleString('fr-FR') + ' km²'],
                    ['Départements', p.nb_departements]
                ]));
                layer.on('mouseover', () => {
                    layer.setStyle(STYLES.regions.hover);
                    document.getElementById('feature-info').textContent =
                        `Région ${p.nom} — Chef-lieu : ${p.chef_lieu}`;
                });
                layer.on('mouseout', () => {
                    layer.setStyle(STYLES.regions.default);
                    document.getElementById('feature-info').textContent =
                        'Survolez un élément pour afficher ses informations';
                });
            }
        });
    },

    createZonesProtegeesLayer(data) {
        return L.geoJSON(data, {
            style: STYLES.zonesProtegees.default,
            onEachFeature: (feature, layer) => {
                const p = feature.properties;
                layer.bindPopup(this.buildPopup(p.nom, [
                    ['Type', p.type],
                    ['Superficie', (p.superficie_ha || '—').toLocaleString('fr-FR') + ' ha'],
                    ['Création', p.creation],
                    ['Faune', p.faune],
                    ['Statut', p.statut]
                ]));
                layer.on('mouseover', () => {
                    layer.setStyle(STYLES.zonesProtegees.hover);
                    document.getElementById('feature-info').textContent =
                        `${p.nom} — ${p.type}`;
                });
                layer.on('mouseout', () => {
                    layer.setStyle(STYLES.zonesProtegees.default);
                    document.getElementById('feature-info').textContent =
                        'Survolez un élément pour afficher ses informations';
                });
            }
        });
    },

    /* ------ Synchronisation de la visibilité des couches --- */
    syncLayerVisibility() {
        const toggles = {
            'layer-villes':          { key: 'villes',         defaultOn: true },
            'layer-routes':          { key: 'routes',          defaultOn: false },
            'layer-regions':         { key: 'regions',         defaultOn: false },
            'layer-zones-protegees': { key: 'zonesProtegees',  defaultOn: false }
        };

        Object.entries(toggles).forEach(([id, cfg]) => {
            const checkbox = document.getElementById(id);
            const layer = this.layers[cfg.key];
            if (!layer) return;

            if (checkbox.checked) {
                layer.addTo(this.map);
            } else {
                this.map.removeLayer(layer);
            }
        });
    },

    /* ------ Construction des popups ----------------------- */
    buildPopup(title, rows) {
        const rowsHtml = rows.map(([k, v]) =>
            `<div class="popup-row">
                <span class="popup-key">${k}</span>
                <span class="popup-val">${v !== undefined && v !== null ? v : '—'}</span>
            </div>`
        ).join('');

        return `<div>
            <div class="popup-title">${title}</div>
            ${rowsHtml}
        </div>`;
    },

    /* ------ Gestion des événements UI --------------------- */
    bindUIEvents() {
        // Basemaps
        document.querySelectorAll('input[name="basemap"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                Object.values(BASEMAPS).forEach(bm => this.map.removeLayer(bm));
                BASEMAPS[e.target.value].addTo(this.map);
                this.setStatus(`Fond de carte : ${e.target.labels[0].textContent.trim()}`);
            });
        });

        // Toggle de couches
        const layerMap = {
            'layer-villes':          'villes',
            'layer-routes':          'routes',
            'layer-regions':         'regions',
            'layer-zones-protegees': 'zonesProtegees'
        };
        Object.entries(layerMap).forEach(([id, key]) => {
            document.getElementById(id).addEventListener('change', (e) => {
                const layer = this.layers[key];
                if (!layer) return;
                if (e.target.checked) {
                    layer.addTo(this.map);
                } else {
                    this.map.removeLayer(layer);
                }
            });
        });

        // Toggle panneau
        document.getElementById('btn-toggle-panel').addEventListener('click', () => {
            document.getElementById('side-panel').classList.toggle('collapsed');
        });

        // Vue initiale
        document.getElementById('btn-reset-view').addEventListener('click', () => {
            this.map.setView(CONFIG.center, CONFIG.zoom);
            this.setStatus('Vue réinitialisée');
        });

        // Mesure distance
        document.getElementById('btn-measure-distance').addEventListener('click', () => {
            this.startMeasure('polyline');
        });

        // Mesure surface
        document.getElementById('btn-measure-area').addEventListener('click', () => {
            this.startMeasure('polygon');
        });

        // Recherche
        document.getElementById('btn-search').addEventListener('click', () => {
            this.performSearch();
        });
        document.getElementById('search-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });

        // Export GeoJSON
        document.getElementById('btn-export-geojson').addEventListener('click', () => {
            this.exportGeoJSON();
        });

        // Impression
        document.getElementById('btn-print-map').addEventListener('click', () => {
            window.print();
        });
    },

    /* ------ Mesures --------------------------------------- */
    startMeasure(type) {
        if (this.measuring) {
            this.stopMeasure();
            return;
        }

        this.measuring = true;
        this.measureType = type;

        const btnId = type === 'polyline' ? 'btn-measure-distance' : 'btn-measure-area';
        document.getElementById(btnId).classList.add('active');
        document.getElementById('measure-result').classList.add('hidden');
        this.setStatus('Cliquez sur la carte pour dessiner. Double-clic pour terminer.');

        const options = {
            edit: { featureGroup: this.drawLayer }
        };

        const DrawClass = type === 'polyline'
            ? L.Draw.Polyline
            : L.Draw.Polygon;

        this.currentDraw = new DrawClass(this.map, {
            shapeOptions: {
                color: '#e74c3c',
                weight: 3
            },
            showLength: true,
            metric: true,
            tooltip: {
                start: 'Cliquez pour commencer',
                cont: 'Cliquez pour continuer',
                end: 'Double-clic pour terminer'
            }
        });
        this.currentDraw.enable();

        this.map.once(L.Draw.Event.CREATED, (e) => {
            this.drawLayer.clearLayers();
            this.drawLayer.addLayer(e.layer);
            const result = this.computeMeasure(e.layer, type);
            document.getElementById('measure-value').textContent = result;
            document.getElementById('measure-result').classList.remove('hidden');
            this.stopMeasure();
        });
    },

    stopMeasure() {
        this.measuring = false;
        if (this.currentDraw) {
            this.currentDraw.disable();
            this.currentDraw = null;
        }
        document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
        this.setStatus('Mesure terminée');
    },

    computeMeasure(layer, type) {
        if (type === 'polyline') {
            const latlngs = layer.getLatLngs();
            let total = 0;
            for (let i = 0; i < latlngs.length - 1; i++) {
                total += latlngs[i].distanceTo(latlngs[i + 1]);
            }
            return total >= 1000
                ? (total / 1000).toFixed(2) + ' km'
                : total.toFixed(0) + ' m';
        } else {
            const area = L.GeometryUtil
                ? L.GeometryUtil.geodesicArea(layer.getLatLngs()[0])
                : this.computePolygonArea(layer.getLatLngs()[0]);
            return area >= 1000000
                ? (area / 1000000).toFixed(2) + ' km²'
                : area.toFixed(0) + ' m²';
        }
    },

    computePolygonArea(latlngs) {
        // Shoelace formula approximation (planar)
        let area = 0;
        const n = latlngs.length;
        for (let i = 0; i < n; i++) {
            const j = (i + 1) % n;
            const lat1 = latlngs[i].lat * Math.PI / 180;
            const lat2 = latlngs[j].lat * Math.PI / 180;
            const dlng = (latlngs[j].lng - latlngs[i].lng) * Math.PI / 180;
            area += dlng * (2 + Math.sin(lat1) + Math.sin(lat2));
        }
        return Math.abs(area * 6371000 * 6371000 / 2);
    },

    /* ------ Recherche ------------------------------------- */
    performSearch() {
        const query = document.getElementById('search-input').value.trim().toLowerCase();
        if (!query) return;

        const results = [];

        // Recherche dans les villes
        if (this.layers.villes) {
            this.layers.villes.eachLayer(layer => {
                const p = layer.feature.properties;
                if (p.nom.toLowerCase().includes(query) || (p.region || '').toLowerCase().includes(query)) {
                    results.push({
                        name: p.nom,
                        type: `Ville — ${p.region}`,
                        layer
                    });
                }
            });
        }

        // Recherche dans les régions
        if (this.layers.regions) {
            this.layers.regions.eachLayer(layer => {
                const p = layer.feature.properties;
                if (p.nom.toLowerCase().includes(query) || (p.chef_lieu || '').toLowerCase().includes(query)) {
                    results.push({
                        name: p.nom,
                        type: `Région — Chef-lieu : ${p.chef_lieu}`,
                        layer
                    });
                }
            });
        }

        // Recherche dans les zones protégées
        if (this.layers.zonesProtegees) {
            this.layers.zonesProtegees.eachLayer(layer => {
                const p = layer.feature.properties;
                if (p.nom.toLowerCase().includes(query)) {
                    results.push({
                        name: p.nom,
                        type: p.type,
                        layer
                    });
                }
            });
        }

        this.displaySearchResults(results);
    },

    displaySearchResults(results) {
        const container = document.getElementById('search-results');
        container.innerHTML = '';

        if (results.length === 0) {
            container.innerHTML = '<div class="search-result-item"><span class="result-name">Aucun résultat</span></div>';
            container.classList.remove('hidden');
            return;
        }

        results.slice(0, 8).forEach(result => {
            const item = document.createElement('div');
            item.className = 'search-result-item';
            item.innerHTML = `
                <div class="result-name">${result.name}</div>
                <div class="result-type">${result.type}</div>
            `;
            item.addEventListener('click', () => {
                if (result.layer.getBounds) {
                    this.map.fitBounds(result.layer.getBounds(), { padding: [40, 40] });
                } else if (result.layer.getLatLng) {
                    this.map.setView(result.layer.getLatLng(), 12);
                }
                result.layer.openPopup();
                container.classList.add('hidden');
                document.getElementById('search-input').value = result.name;
                this.setStatus(`Navigation vers : ${result.name}`);
            });
            container.appendChild(item);
        });

        container.classList.remove('hidden');
    },

    /* ------ Export GeoJSON -------------------------------- */
    exportGeoJSON() {
        const features = [];

        // Collecter les entités dessinées
        this.drawLayer.eachLayer(layer => {
            if (layer.toGeoJSON) {
                features.push(layer.toGeoJSON());
            }
        });

        if (features.length === 0) {
            this.setStatus('Aucun élément dessiné à exporter. Utilisez les outils de mesure pour dessiner.');
            return;
        }

        const geojson = {
            type: 'FeatureCollection',
            features
        };

        const blob = new Blob([JSON.stringify(geojson, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'sig_export.geojson';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        this.setStatus('Export GeoJSON téléchargé');
    },

    /* ------ Utilitaires ----------------------------------- */
    setStatus(msg) {
        document.getElementById('status-message').textContent = msg;
    }
};

/* ============================================================
   Démarrage de l'application
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => App.init());
