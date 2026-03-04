async function checkFeatureFlags() {
    try {
        const response = await fetch('/api/features');
        const flags = await response.json();
        const navElement = document.getElementById('nav');

        // Remove existing protocols link if it exists
        const existingProtocolsLink = document.querySelector('[data-nav-protocols]');
        if (existingProtocolsLink) {
            existingProtocolsLink.remove();
        }

        // Add protocols link if the flag is enabled
        if (flags.protocol_feed_enabled) {
            const protocolsButton = document.createElement('a');
            protocolsButton.href = '/app?screen=protocol';
            protocolsButton.setAttribute('data-nav-protocols', 'true');
            protocolsButton.className = 'flex flex-col items-center gap-1 text-gray-500 hover:text-white transition-colors';
            protocolsButton.innerHTML = `
              <iconify-icon icon="lucide:layers" class="text-2xl"></iconify-icon>
              <span class="text-[10px] font-medium">Protocols</span>
            `; 
            navElement.appendChild(protocolsButton);
        }

        console.log('[nav-enhancer] Protocols link added to navigation if enabled.');
    } catch (error) {
        console.error('[nav-enhancer] Error in feature flag check:', error);
    }
}

// Call the function on page load
checkFeatureFlags();
