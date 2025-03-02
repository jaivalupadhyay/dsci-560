// Convert DMS (Degrees, Minutes, Seconds) to Decimal
function dmsToDecimal(dms) {
    const regex = /(\d+)°\s*(\d+)'?\s*([\d.]+)"?\s*([NSEW])/;
    const match = dms.match(regex);

    if (!match) {
        console.warn(`Invalid DMS format: ${dms}`);
        return NaN; // Return NaN if format is incorrect
    }

    let degrees = parseFloat(match[1]);
    let minutes = parseFloat(match[2]);
    let seconds = parseFloat(match[3]);
    let direction = match[4];

    let decimal = degrees + (minutes / 60) + (seconds / 3600);

    // South and West should be negative
    if (direction === "S" || direction === "W") {
        decimal *= -1;
    }

    return decimal;
}

// Initialize OpenLayers Map
const map = new ol.Map({
    target: 'map',
    layers: [
        new ol.layer.Tile({
            source: new ol.source.XYZ({
                url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                tileLoadFunction: function(imageTile, src) {
                    setTimeout(() => {
                        imageTile.getImage().src = src; // Retry tile loading
                    }, 1000); // Delay retry by 1 second
                }
            })
        })
    ],
    view: new ol.View({
        center: ol.proj.fromLonLat([-103.731363, 48.109352]), // Default center (adjust as needed)
        zoom: 5
    })
});

// Create Layer for Markers
const vectorSource = new ol.source.Vector();
const vectorLayer = new ol.layer.Vector({
    source: vectorSource
});
map.addLayer(vectorLayer);

// Function to Fetch Well Data and Add Markers
async function addMarkers() {
    try {
        const response = await fetch("http://localhost:3000/wells");
        const wells = await response.json();
        console.log("Fetched wells data:", wells); // Debugging line

        wells.forEach(well => {
            let lat = dmsToDecimal(well.latitude);
            let lon = dmsToDecimal(well.longitude);

            if (!isNaN(lat) && !isNaN(lon)) {
                console.log(`Adding marker at: ${lat}, ${lon}`);

                const feature = new ol.Feature({
                    geometry: new ol.geom.Point(ol.proj.fromLonLat([lon, lat])),
                    wellData: well
                });

                feature.setStyle(new ol.style.Style({
                    image: new ol.style.Icon({
                        anchor: [0.5, 1],
                        src: 'https://upload.wikimedia.org/wikipedia/commons/e/ec/RedDot.svg',
                        scale: 1
                    })
                }));

                vectorSource.addFeature(feature);
            } else {
                console.warn(`Skipping invalid well: ${JSON.stringify(well)}`);
            }
        });

    } catch (error) {
        console.error("Error fetching well data:", error);
    }
}

// Popup for Well Data
const overlay = new ol.Overlay({
    element: document.createElement('div'),
    positioning: 'bottom-center',
    stopEvent: false
});
map.addOverlay(overlay);

map.on('click', function (event) {
    map.forEachFeatureAtPixel(event.pixel, function (feature) {
        const well = feature.get('wellData');
        const coords = feature.getGeometry().getCoordinates();

        const popupContent = `
            <strong>Well Name:</strong> ${well.well_name || "N/A"}<br>
            <strong>Operator:</strong> ${well.operator || "N/A"}<br>
            <strong>County:</strong> ${well.county || "N/A"}<br>
            <strong>API Number:</strong> ${well.API || "N/A"}<br>
            <strong>Latitude:</strong> ${well.latitude}<br>
            <strong>Longitude:</strong> ${well.longitude}
        `;

        overlay.getElement().innerHTML = popupContent;
        overlay.setPosition(coords);
    });
});

// Create Layer for Markers (Initialize before adding markers)
addMarkers();

