// static/js/main.js

// Initialize Socket.IO connection
const socket = io();

// Global variables
let map = null;
let busMarkers = {};

// Format time function
function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Format date function
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Show loading spinner
function showLoading(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="spinner-container">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
    }
}

// Show error message
function showError(containerId, message) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <i class="fas fa-exclamation-triangle"></i>
                ${message}
            </div>
        `;
    }
}

// Initialize map
function initMap(centerLat = 40.712776, centerLng = -74.005974, zoom = 13) {
    map = L.map('map').setView([centerLat, centerLng], zoom);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);
    
    return map;
}

// Bus icon
const busIcon = L.icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
});

// Update bus markers on map
function updateBusMarkers(buses) {
    // Remove old markers
    Object.values(busMarkers).forEach(marker => {
        map.removeLayer(marker);
    });
    busMarkers = {};
    
    // Add new markers
    buses.forEach(bus => {
        if (bus.latitude && bus.longitude) {
            const marker = L.marker([bus.latitude, bus.longitude], { icon: busIcon })
                .bindPopup(`
                    <b>Bus ${bus.bus_number}</b><br>
                    Route: ${bus.route_name || 'Unknown'}<br>
                    Next Stop: ${bus.next_stop || 'Unknown'}<br>
                    Speed: ${bus.speed || 0} km/h<br>
                    Status: ${bus.trip_status || 'Unknown'}<br>
                    Last Updated: ${formatTime(bus.timestamp)}
                `);
            
            marker.addTo(map);
            busMarkers[bus.bus_id] = marker;
        }
    });
}

// Update bus list UI
function updateBusList(buses) {
    const busList = document.getElementById('bus-list');
    if (!busList) return;
    
    if (buses.length === 0) {
        busList.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle"></i>
                No active buses at the moment.
            </div>
        `;
        return;
    }
    
    let html = '';
    buses.forEach(bus => {
        const statusClass = getStatusClass(bus.trip_status);
        html += `
            <div class="bus-item ${statusClass}">
                <div class="d-flex justify-content-between align-items-center">
                    <h6 class="mb-1">
                        <i class="fas fa-bus"></i> Bus ${bus.bus_number}
                    </h6>
                    <span class="badge badge-${statusClass}">${bus.trip_status || 'Unknown'}</span>
                </div>
                <p class="mb-1 small">Route: ${bus.route_name || 'Unknown'}</p>
                <p class="mb-1 small">Next Stop: ${bus.next_stop || 'Unknown'}</p>
                <p class="mb-0 small text-muted">
                    <i class="fas fa-tachometer-alt"></i> ${bus.speed || 0} km/h
                    <span class="ms-2"><i class="fas fa-clock"></i> ${formatTime(bus.timestamp)}</span>
                </p>
            </div>
        `;
    });
    
    busList.innerHTML = html;
}

// Get status class for styling
function getStatusClass(status) {
    switch(status) {
        case 'on_time':
            return 'on-time';
        case 'delayed':
            return 'delayed';
        case 'approaching':
            return 'approaching';
        default:
            return '';
    }
}

// Socket.IO event listeners
socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('bus_location_updated', (data) => {
    console.log('Bus location updated:', data);
    
    // Update marker if it exists
    if (busMarkers[data.bus_id]) {
        busMarkers[data.bus_id].setLatLng([data.latitude, data.longitude]);
        busMarkers[data.bus_id].getPopup().setContent(`
            <b>Bus ${data.bus_number}</b><br>
            Route: ${data.route_name}<br>
            Speed: ${data.speed} km/h<br>
            Last Updated: Just now
        `);
    }
});

// Form submission handler
function handleFormSubmit(formId, url, successCallback) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(form);
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        
        // Show loading state
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        
        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                if (successCallback) {
                    successCallback(data);
                }
            } else {
                alert('Error: ' + data.message);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred. Please try again.');
        } finally {
            // Restore button
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('Campus Bus System initialized');
});