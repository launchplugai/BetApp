/**
 * Nav Protocols Enhancement (Slice 2B)
 * 
 * Dynamically adds "Protocols" link to navigation when feature flag is enabled.
 * Include this script in screens: browse, builder, history
 */

(async function() {
  try {
    const response = await fetch('/api/features');
    const flags = await response.json();
    
    if (!flags.dashboard_enabled) {
      // Feature disabled, do nothing
      return;
    }
    
    // Feature enabled — add "Protocols" link to nav
    const nav = document.querySelector('nav, footer nav, footer > div');
    if (!nav) {
      console.warn('[nav-protocols] Navigation element not found');
      return;
    }
    
    // Check if protocols link already exists
    if (document.querySelector('[data-nav-protocols]')) {
      return; // Already added
    }
    
    // Create protocols button
    const protocolsButton = document.createElement('a');
    protocolsButton.href = '/app?screen=protocols';
    protocolsButton.setAttribute('data-nav-protocols', 'true');
    protocolsButton.className = 'flex flex-col items-center gap-1 text-gray-500 hover:text-white transition-colors';
    protocolsButton.style.minWidth = '60px';
    protocolsButton.innerHTML = `
      <iconify-icon icon="lucide:layers" class="text-2xl"></iconify-icon>
      <span class="text-[10px] font-medium">Protocols</span>
    `;
    
    // Insert before last nav item (usually Profile)
    const navItems = nav.querySelectorAll('a, button');
    if (navItems.length > 0) {
      const lastItem = navItems[navItems.length - 1];
      lastItem.parentNode.insertBefore(protocolsButton, lastItem);
    } else {
      nav.appendChild(protocolsButton);
    }
    
    console.log('[nav-protocols] Protocols link added to navigation');
  } catch (error) {
    console.error('[nav-protocols] Failed to load feature flags:', error);
  }
})();
