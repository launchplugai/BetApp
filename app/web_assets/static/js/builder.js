async function addLeg(legData) {
    // Load user preferences
    let userPrefs;
    try {
        const prefsResponse = await fetch(`${API_BASE}/preferences`);
        if (!prefsResponse.ok) {
            throw new Error('Could not load user preferences');
        }
        userPrefs = await prefsResponse.json();
    } catch (err) {
        console.error('Failed to load user preferences:', err);
        return;  // Prevent adding leg if preferences can't be loaded
    }

    // Check constraints before adding the leg
    const constraintChecker = new ConstraintChecker(userPrefs);
    const violations = constraintChecker.check_picks([legData]);

    if (violations.length > 0) {
        // Handle violations - for instance, display warnings
        const messages = violations.map(v => v.message).join('\n');
        showError(`Cannot add this leg because: \n${messages}`);
        return;
    }

    // Check if already exists - if so, remove it
    const existingIndex = legs.findIndex(l => {
        if (l.market !== legData.market) return false;
        if (legData.team && l.team === legData.team) return true;
        if (legData.player && l.player === legData.player && l.line === legData.line) return true;
        if (legData.side && l.side === legData.side) return true;
        return false;
    });
    
    if (existingIndex >= 0) {
        removeLeg(existingIndex);
        return;
    }

    // Add new leg with unique ID
    const leg = {
        id: `leg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        ...legData
    };
    
    legs.push(leg);
    console.log('Leg added:', leg);
    renderLegs();
    recalculate();
    renderMarket(); // Re-render to update selected state
}