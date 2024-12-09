// Service worker registration
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/service-worker.js')
            .then(function(registration) {
                console.log('ServiceWorker registration successful');
            })
            .catch(function(err) {
                console.log('ServiceWorker registration failed: ', err);
            });
    });
}

// Map interaction handlers
function handleMapClick(e) {
    if (window.Shiny) {
        Shiny.setInputValue('map_click', {
            lat: e.latlng.lat,
            lng: e.latlng.lng
        });
    }
}

function handleZoomEnd(e) {
    if (window.Shiny) {
        Shiny.setInputValue('map_zoom', e.target.getZoom());
    }
}

// Table interaction handlers
function handleRowClick(propertyId) {
    if (window.Shiny) {
        Shiny.setInputValue('selected_property', propertyId);
    }
}

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatNumber(number, decimals = 0) {
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(number);
} 