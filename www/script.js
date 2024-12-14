// Debug function
function debug(message, data = null) {
    console.log(`[Debug] ${message}`, data || '');
    const debugOutput = document.getElementById('debug-output');
    if (debugOutput) {
        debugOutput.innerHTML += `<div>${message}</div>`;
    }
}

// Wait for Shiny to be ready
$(document).on('shiny:connected', function() {
    console.log('Shiny connected, initializing sort functionality');
});

// Initialize sorting functionality
$(document).ready(function() {
    console.log('Document ready');
    initializeSorting();
});

function initializeSorting() {
    console.log('Initializing sorting');
    
    // Add click handlers to sortable headers
    $(document).on('click', 'th.sortable', function(e) {
        e.preventDefault();
        const column = $(this).data('column');
        handleSort(column);
    });
    
    // Update initial sort indicators
    updateSortIndicators();
}

function handleSort(column) {
    console.log('Handling sort for column:', column);
    
    // Get current values
    const currentColumn = $('#sort_column').val();
    const currentDirection = $('#sort_direction').val();
    
    console.log('Current state:', { currentColumn, currentDirection });
    
    // Simple toggle between asc and desc
    let newDirection = 'asc';
    if (column === currentColumn && currentDirection === 'asc') {
        newDirection = 'desc';
    }
    
    // Update the inputs
    $('#sort_column').val(column).trigger('change');
    $('#sort_direction').val(newDirection).trigger('change');
    
    // Update visual indicators
    updateSortIndicators();
}

function updateSortIndicators() {
    const currentColumn = $('#sort_column').val();
    const currentDirection = $('#sort_direction').val();
    
    try {
        // Only remove indicators from columns that aren't current
        $('th.sortable').not(`[data-column="${currentColumn}"]`)
            .removeClass('asc desc')
            .find('.sort-indicator')
            .remove();
        
        // Update current column indicator
        const currentHeader = $(`th.sortable[data-column="${currentColumn}"]`);
        
        // Only update classes if they've changed
        if (!currentHeader.hasClass(currentDirection)) {
            currentHeader.removeClass('asc desc').addClass(currentDirection);
            
            // Update arrow indicator
            currentHeader.find('.sort-indicator').remove();
            if (currentDirection !== 'none') {
                const arrow = currentDirection === 'asc' ? '↑' : '↓';
                currentHeader.append(`<span class="sort-indicator">${arrow}</span>`);
            }
        }
    } catch (error) {
        console.error('Error updating sort indicators:', error);
    }
}

// Make sure sorting is initialized when table updates
const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.addedNodes.length) {
            updateSortIndicators();
        }
    });
});

// Start observing the document for changes
observer.observe(document.body, {
    childList: true,
    subtree: true
});

// Add styles for sort indicators
const style = document.createElement('style');
style.textContent = `
    .sortable {
        cursor: pointer;
        position: relative;
        padding-right: 20px !important;
    }
    
    .sort-indicator {
        position: absolute;
        right: 5px;
        top: 50%;
        transform: translateY(-50%);
    }
    
    .sortable:hover {
        background-color: rgba(0, 0, 0, 0.05);
    }
`;
document.head.appendChild(style);

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    debug('DOM Content Loaded');
});

// Also try to initialize after a short delay (backup)
setTimeout(function() {
    debug('Initializing after delay');
}, 1000);

// Log when script is loaded
debug('Sorting script loaded successfully');

// Initialize loading state
Shiny.addCustomMessageHandler('toggleLoading', function(show) {
    const loadingEl = document.getElementById('table-loading');
    if (loadingEl) {
        loadingEl.style.display = show ? 'flex' : 'none';
    }
});

// Handle keyboard navigation for table rows
document.addEventListener('keydown', function(event) {
    if (event.target.closest('.product-row')) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            event.target.closest('.product-row').click();
        }
    }
});

// Add ripple effect to clickable elements
document.querySelectorAll('.product-row').forEach(row => {
    row.addEventListener('click', function(e) {
        const ripple = document.createElement('div');
        ripple.classList.add('ripple');
        
        const rect = this.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = e.clientX - rect.left - size/2 + 'px';
        ripple.style.top = e.clientY - rect.top - size/2 + 'px';
        
        this.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    });
});

// Add input debouncing for search
let searchTimeout;
const searchInput = document.querySelector('input#product_search');
if (searchInput) {
    searchInput.addEventListener('input', function(e) {
        clearTimeout(searchTimeout);
        Shiny.setInputValue('loading', true);
        
        searchTimeout = setTimeout(() => {
            Shiny.setInputValue('product_search', e.target.value);
            setTimeout(() => {
                Shiny.setInputValue('loading', false);
            }, 300);
        }, 300);
    });
}
