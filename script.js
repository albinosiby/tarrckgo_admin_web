// Navigation & Modal Logic
// Note: Navigation is now handled by standard href links in the HTML files.

window.openModal = (id) => document.getElementById(id).style.display = 'flex';
window.closeModal = (id) => document.getElementById(id).style.display = 'none';
window.onclick = (e) => { if (e.target.classList.contains('modal-overlay')) e.target.style.display = 'none'; };

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Map centered on Chemperi (Vimal Jyothi College area)
    // Only initialize if the map container exists (it's only on the dashboard page)
    if (document.getElementById('map')) {
        window.mapInstance = L.map('map').setView([12.096, 75.558], 13);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(window.mapInstance);

        // Dummy Bus Markers
        const buses = [
            { id: 'Bus 1', lat: 12.096, lng: 75.558, title: 'Bus 1 - College' },
            { id: 'Bus 3', lat: 12.080, lng: 75.550, title: 'Bus 3 - Town' },
            { id: 'Bus 5', lat: 12.110, lng: 75.570, title: 'Bus 5 - Village' }
        ];

        buses.forEach(bus => {
            L.marker([bus.lat, bus.lng]).addTo(window.mapInstance)
                .bindPopup(`<b>${bus.title}</b><br>Status: Moving`);
        });
    }
});
